"""Finite offline paired comparison; same cases, activations and folds in both arms."""
import datetime,hashlib,json
from pathlib import Path
import modal
app=modal.App('ambient-field-lens-paired-comparison')
weights=modal.Volume.from_name('glimmer-weights',create_if_missing=False)
artifacts=modal.Volume.from_name('afl-recal-artifacts',create_if_missing=True)
cpu_image=modal.Image.debian_slim(python_version='3.12')
gpu_image=(modal.Image.debian_slim(python_version='3.12')
 .pip_install('torch==2.14.1','transformers==5.21.0','accelerate==1.15.0','safetensors',
              'numpy==2.5.4','scikit-learn==1.9.1','scipy==1.18.1','pillow')
 .env({'HF_HUB_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1'}))

@app.function(image=cpu_image,gpu=None,volumes={'/weights':weights},timeout=30,retries=0,
 min_containers=0,max_containers=1,scaledown_window=2)
def checked_download():
    root=Path('/weights/Muse-Glimmer-30B')
    report=json.loads((root/'verified-download.json').read_text())
    if not report.get('verified') or report.get('gpu_used') or report.get('weight_bytes')!=59_553_435_272:
        raise ValueError('Verified BF16 CPU snapshot required')
    for item in report['files']:
        if (root/item['path']).stat().st_size!=item['bytes']:raise ValueError('Verified snapshot changed')
    return report


HERE=Path(__file__).parent
image=(gpu_image.add_local_file(HERE/'paired_analysis.py','/opt/afl/paired_analysis.py')
 .add_local_file(HERE/'jacobian_lens.py','/opt/afl/jacobian_lens.py'))


def encode_record(tok,record,frames=None):
    if frames:
        import base64,io
        from PIL import Image
        frame=frames[record['frame_sha256']]
        raw=base64.b64decode(frame['jpeg_base64'],validate=True)
        if hashlib.sha256(raw).hexdigest()!=record['frame_sha256']:raise ValueError('Frame hash mismatch')
        image=Image.open(io.BytesIO(raw)).convert('RGB')
        messages=[{'role':'user','content':[{'type':'image','image':image},{'type':'text','text':record['text']}]},
                  {'role':'assistant','content':record['candidate']}]
        return tok.apply_chat_template(messages,add_generation_prompt=False,continue_final_message=True,
                 tokenize=True,return_tensors='pt',return_dict=True,reasoning_strength='low',max_image_tokens=256)
    return tok.apply_chat_template([{'role':'user','content':record['text']},
      {'role':'assistant','content':record['candidate']}],add_generation_prompt=False,
      continue_final_message=True,return_tensors='pt',return_dict=True,reasoning_strength='low')


@app.function(image=image,gpu=None,cpu=(1,2),memory=(4096,8192),volumes={'/weights':weights},
 timeout=240,retries=0,min_containers=0,max_containers=1,scaledown_window=2)
def paired_preflight(records,frames=None):
    import torch
    from accelerate import init_empty_weights
    from transformers import AutoConfig,AutoTokenizer,AutoProcessor,AutoModelForCausalLM,AutoModelForImageTextToText
    root='/weights/Muse-Glimmer-30B'
    config=AutoConfig.from_pretrained(root,local_files_only=True,trust_remote_code=False)
    tok=(AutoProcessor if frames else AutoTokenizer).from_pretrained(root,local_files_only=True,trust_remote_code=False)
    kind,loader=next((kind,loader) for kind,loader in [('causal',AutoModelForCausalLM),('multimodal',AutoModelForImageTextToText)] if type(config) in loader._model_mapping)
    with init_empty_weights(include_buffers=True):model=loader.from_config(config,trust_remote_code=False)
    paths=[name for name,m in model.named_modules() if isinstance(m,torch.nn.ModuleList) and name.endswith('layers') and len(m)==52]
    if len(paths)!=1:raise ValueError('Text decoder ambiguous')
    norm_path=paths[0].rsplit('.',1)[0]+'.norm'
    norm=model.get_submodule(norm_path).to_empty(device='cpu').float()
    with torch.no_grad():
        for name,p in norm.named_parameters():p.fill_(0 if 'bias' in name else 1)
    x=torch.arange(6656,dtype=torch.float32)/6656
    _,tangent=torch.func.jvp(norm,(x,),(torch.ones_like(x),))
    if not torch.isfinite(tangent).all():raise ValueError('Actual norm JVP unavailable on CPU')
    enc=[encode_record(tok,r,frames) for r in records]
    if frames and any('pixel_values' not in e or not e['pixel_values'].numel() for e in enc):raise ValueError('Camera input missing from processor output')
    lengths=[int(e['input_ids'].shape[-1]) for e in enc]
    if max(lengths)>1024:raise ValueError('Prompt budget exceeded; no truncation allowed')
    for r,e in zip(records,enc):
        decoded=(tok.tokenizer if frames else tok).decode(e['input_ids'][0],skip_special_tokens=True)
        if not decoded.rstrip().endswith(r['candidate']):raise ValueError('Readout is not at final candidate token')
    return {'loader_kind':kind,'decoder_path':paths[0],'norm_path':norm_path,'norm_class':type(norm).__name__,
      'cases_checked':len(records),'maximum_prompt_tokens':max(lengths),'prompt_tokens':lengths,
      'image_input':bool(frames),'frame_count':len(frames or {}),'max_image_tokens':256 if frames else None,
      'image_grids':[e['image_grid_thw'].tolist() for e in enc] if frames else [],
      'actual_norm_jvp_cpu_verified':True,'candidate_token_readout_verified':True,'gpu_used':False}


@app.function(image=image,gpu='A100-80GB',cpu=(2,4),memory=(32768,65536),
 volumes={'/weights':weights,'/artifacts':artifacts},timeout=2700,startup_timeout=300,retries=0,
 min_containers=0,max_containers=1,buffer_containers=0,scaledown_window=2,single_use_containers=True)
def paired_research(payload,reservation,preflight,input_sha):
    import copy,sys,time
    import numpy as np
    import torch,transformers
    from transformers import AutoTokenizer,AutoProcessor,AutoModelForCausalLM,AutoModelForImageTextToText
    sys.path.insert(0,'/opt/afl')
    from paired_analysis import validate_records,fit_score,summarize
    from jacobian_lens import project_jacobian
    records=payload['records'];validate_records(records);frames=payload.get('frames')
    started=time.monotonic();out=Path('/artifacts')/reservation['id'];out.mkdir(parents=True,exist_ok=True)
    def save(name,obj):
        (out/name).write_text(json.dumps(obj,indent=2));artifacts.commit()
    provenance={'input_sha256':input_sha,'sources':payload['sources'],'input_cache_sha256':payload['cache_sha256'],
      'case_origin':payload['case_origin'],'author_review':payload['author_review'],'image_input':bool(frames),
      'frames':[{k:v for k,v in f.items() if k!='jpeg_base64'} for f in (frames or {}).values()],
      'camera_scope':payload.get('camera_scope','Text-only smoke; no camera evidence'),
      'folds':{f:[r['id'] for r in records if r['fold']==f] for f in ('fit','validation','test')},
      'reservation':reservation,'preflight':preflight,'phase3_enabled':False,
      'source_revision':'cec94fcfd6512f2cfe708138c32533b346ea4f69'}
    save('paired-provenance.json',provenance)
    try:
        root='/weights/Muse-Glimmer-30B';tok=(AutoProcessor if frames else AutoTokenizer).from_pretrained(root,local_files_only=True,trust_remote_code=False)
        loader=AutoModelForCausalLM if preflight['loader_kind']=='causal' else AutoModelForImageTextToText
        print('Loading verified BF16 checkpoint; finite paired research only.',flush=True)
        model=loader.from_pretrained(root,dtype=torch.bfloat16,device_map='cuda:0',local_files_only=True,trust_remote_code=False,attn_implementation='sdpa')
        model.eval();model.requires_grad_(False)
        layers=model.get_submodule(preflight['decoder_path']);captures={}
        def capture(i):
            def hook(module,args,output):
                h=output[0] if isinstance(output,tuple) else output
                captures[i]=h[0,-1].detach().float().cpu().numpy()
            return hook
        handles=[layer.register_forward_hook(capture(i)) for i,layer in enumerate(layers)]
        states=[]
        try:
            for i,r in enumerate(records):
                encoded=encode_record(tok,r,frames)
                if encoded['input_ids'].shape[-1]!=preflight['prompt_tokens'][i]:raise ValueError('Tokenizer preflight drift')
                captures.clear()
                with torch.inference_mode():model(**{k:v.to('cuda:0') for k,v in encoded.items()},use_cache=False)
                if len(captures)!=52:raise ValueError('Missing decoder layer')
                states.append(np.stack([captures[l] for l in range(52)]))
                print('Paired prefill',i+1,'/',len(records),flush=True)
        finally:
            for h in handles:h.remove()
        states=np.stack(states)
        if states.shape!=(36,52,6656):raise ValueError('Unexpected hidden shape')
        np.savez_compressed(out/'paired-hidden-states.npz',states=states)
        artifacts.commit()
        baseline=np.stack([fit_score(states[:,l],records)[0] for l in range(52)],axis=1)
        baseline_report=summarize(baseline,records);save('hidden-contrastive.json',baseline_report)
        # FP32 norm/head arithmetic; no full-network backpropagation or model-weight gradient.
        norm=copy.deepcopy(model.get_submodule(preflight['norm_path'])).float()
        head=model.get_output_embeddings().weight.detach().float()
        fit=np.array([r['fold']=='fit' for r in records]);lens_scores=[]
        for l in range(52):
            a=torch.tensor(states[fit,l].mean(0),device='cuda:0',dtype=torch.float32)
            x=torch.tensor(states[:,l],device='cuda:0',dtype=torch.float32)
            with torch.no_grad():z=project_jacobian(norm,head,a,x).cpu().numpy()
            score,_=fit_score(z,records);lens_scores.append(score)
            print('Full-vocabulary norm/head Jacobian layer',l+1,'/52',flush=True)
            del z
        lens_scores=np.stack(lens_scores,axis=1);lens_report=summarize(lens_scores,records)
        save('jacobian-lens.json',lens_report)
        np.savez_compressed(out/'paired-all-layer-scores.npz',hidden=baseline,jacobian_lens=lens_scores)
        rows=[{'id':r['id'],'pair_id':r['pair_id'],'group':r['group'],'fold':r['fold'],'supported':r['supported'],
          'hidden_score':float(baseline[i,baseline_report['selected_layer']]),
          'jacobian_lens_score':float(lens_scores[i,lens_report['selected_layer']])} for i,r in enumerate(records)]
        save('paired-scores.json',rows)
        report={**provenance,'hidden_contrastive':baseline_report,'full_vocabulary_norm_head_jacobian':lens_report,
          'jacobian_scope':'Exact Jacobian of final norm + entire unembedding at fit-only mean residual; local readout lens, not full transformer network Jacobian',
          'same_cases_folds_activations':True,'elapsed_seconds':round(time.monotonic()-started,2),
          'runtime':{'torch':str(torch.__version__),'transformers':str(transformers.__version__),'gpu':torch.cuda.get_device_name(),'peak_gpu_memory_bytes':torch.cuda.max_memory_allocated(),'vocab_coordinates':head.shape[0]},
          'artifact_directory':str(out),'phase3_enabled':False,'status':'complete'}
        save('paired-report.json',report);return report
    except Exception as exc:
        save('paired-failure.json',{'error_type':type(exc).__name__,'error':str(exc)[:1200],'elapsed_seconds':round(time.monotonic()-started,2),'reservation':reservation,'phase3_enabled':False})
        raise


@app.local_entrypoint()
def compare(inputs:str,output:str,gpu_window:bool=False):
    import sys
    sys.path.insert(0,str(HERE))
    from paired_analysis import validate_records
    from budget import reserve_window,record_result
    if not gpu_window:raise ValueError('Explicit finite window required')
    raw=Path(inputs).read_bytes();payload=json.loads(raw);validate_records(payload['records'])
    source=checked_download.remote()
    if source['revision']!='cec94fcfd6512f2cfe708138c32533b346ea4f69':raise ValueError('Checkpoint revision drift')
    preflight=paired_preflight.remote(payload['records'],payload.get('frames'))
    preflight_path=Path(output).with_name('paired-camera-cpu-preflight.json' if payload.get('frames') else 'paired-cpu-preflight.json');preflight_path.parent.mkdir(parents=True,exist_ok=True)
    preflight_path.write_text(json.dumps(preflight,indent=2))
    path=Path.home()/'.local/state/ambient-field-lens/budget.json';reservation=reserve_window(path)
    print('RESERVATION',json.dumps(reservation),flush=True)
    try:
        report=paired_research.remote(payload,reservation,preflight,hashlib.sha256(raw).hexdigest())
        Path(output).write_text(json.dumps(report,indent=2)+'\n')
        record_result(path,reservation['id'],status='complete',elapsed_seconds=report['elapsed_seconds'],artifact_directory=report['artifact_directory'])
        print('PAIRED COMPARISON COMPLETE',output,flush=True)
    except BaseException as exc:
        record_result(path,reservation['id'],status='failed',error_type=type(exc).__name__,error=str(exc)[:500])
        raise
