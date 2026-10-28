"""Finite offline paired comparison; same cases, activations and folds in both arms."""
import datetime,hashlib,json
from pathlib import Path
import modal
app=modal.App('ambient-field-lens-teacher-forced-trajectory')
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
image=(gpu_image.pip_install('torchvision==0.29.1').add_local_file(HERE/'paired_analysis.py','/opt/afl/paired_analysis.py')
 .add_local_file(HERE/'jacobian_lens.py','/opt/afl/jacobian_lens.py')
 .add_local_file(HERE/'trajectory_analysis.py','/opt/afl/trajectory_analysis.py'))


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
def trajectory_preflight(records,frames=None):
    import sys
    sys.path.insert(0,'/opt/afl')
    from trajectory_analysis import candidate_start,trajectory_indices
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
    if frames and any(int(e['image_grid_thw'].prod())//4>256 for e in enc):raise ValueError('Vision-token budget exceeded')
    lengths=[int(e['input_ids'].shape[-1]) for e in enc]
    if max(lengths)>1024:raise ValueError('Prompt budget exceeded; no truncation allowed')
    for r,e in zip(records,enc):
        decoded=(tok.tokenizer if frames else tok).decode(e['input_ids'][0],skip_special_tokens=True)
        if not decoded.rstrip().endswith(r['candidate']):raise ValueError('Readout is not at final candidate token')
    starts=[candidate_start((tok.tokenizer if frames else tok),e['input_ids'][0].tolist(),r['candidate']) for r,e in zip(records,enc)]
    counts=[length-start for length,start in zip(lengths,starts)]
    positions=[trajectory_indices(n) for n in counts]
    return {'candidate_starts':starts,'candidate_counts':counts,'trajectory_indices':positions,'loader_kind':kind,'decoder_path':paths[0],'norm_path':norm_path,'norm_class':type(norm).__name__,
      'cases_checked':len(records),'maximum_prompt_tokens':max(lengths),'prompt_tokens':lengths,
      'image_input':bool(frames),'frame_count':len(frames or {}),'max_image_tokens':256 if frames else None,
      'image_grids':[e['image_grid_thw'].tolist() for e in enc] if frames else [],
      'actual_norm_jvp_cpu_verified':True,'candidate_token_readout_verified':True,'gpu_used':False}


@app.function(image=image,gpu='A100-80GB',cpu=(2,4),memory=(32768,65536),
 volumes={'/weights':weights,'/artifacts':artifacts},timeout=2700,startup_timeout=300,retries=0,
 min_containers=0,max_containers=1,buffer_containers=0,scaledown_window=2,single_use_containers=True)
def trajectory_research(payload,reservation,preflight,input_sha):
    import copy,sys,time
    import numpy as np
    import torch,transformers
    from transformers import AutoProcessor,AutoModelForImageTextToText
    sys.path.insert(0,'/opt/afl')
    from paired_analysis import validate_records,fit_score
    from jacobian_lens import project_jacobian
    from trajectory_analysis import ALL_POINTS,summarize_trajectory
    records=payload['records'];validate_records(records);frames=payload['frames']
    started=time.monotonic();out=Path('/artifacts')/reservation['id'];out.mkdir(parents=True,exist_ok=True)
    def save(name,obj):
        (out/name).write_text(json.dumps(obj,indent=2));artifacts.commit()
    provenance={'input_sha256':input_sha,'sources':payload['sources'],'input_cache_sha256':payload['cache_sha256'],
      'case_origin':payload['case_origin'],'author_review':payload['author_review'],'image_input':True,
      'frames':[{k:v for k,v in f.items() if k!='jpeg_base64'} for f in frames.values()],
      'folds':{f:[r['id'] for r in records if r['fold']==f] for f in ('fit','validation','test')},
      'reservation':reservation,'preflight':preflight,'phase3_enabled':False,
      'source_revision':'cec94fcfd6512f2cfe708138c32533b346ea4f69',
      'protocol':'trajectory-protocol-2026-10-28.md','sampling':False,'forward_passes_per_record':1}
    save('trajectory-provenance.json',provenance)
    try:
        root='/weights/Muse-Glimmer-30B'
        tok=AutoProcessor.from_pretrained(root,local_files_only=True,trust_remote_code=False)
        print('Loading verified BF16 checkpoint for one teacher-forced pass per record.',flush=True)
        model=AutoModelForImageTextToText.from_pretrained(root,dtype=torch.bfloat16,device_map='cuda:0',
          local_files_only=True,trust_remote_code=False,attn_implementation='sdpa')
        model.eval();model.requires_grad_(False)
        layers=model.get_submodule(preflight['decoder_path']);captures={};slice_start=0
        def capture(i):
            def hook(module,args,output):
                h=output[0] if isinstance(output,tuple) else output
                captures[i]=h[0,slice_start:].detach().float().cpu().numpy()
            return hook
        handles=[layer.register_forward_hook(capture(i)) for i,layer in enumerate(layers)]
        states={p:[] for p in ALL_POINTS};token_provenance=[];passes=0
        try:
            for i,r in enumerate(records):
                encoded=encode_record(tok,r,frames)
                ids=encoded['input_ids'][0].tolist()
                if len(ids)!=preflight['prompt_tokens'][i]:raise ValueError('Tokenizer preflight drift')
                start=preflight['candidate_starts'][i];slice_start=start-1
                positions=preflight['trajectory_indices'][i]
                if len(ids)-start!=preflight['candidate_counts'][i]:raise ValueError('Candidate boundary drift')
                captures.clear()
                with torch.inference_mode():
                    # One full causal pass. No generation, incremental retries or sampling.
                    model(**{k:v.to('cuda:0') for k,v in encoded.items()},use_cache=False)
                passes+=1
                if len(captures)!=52:raise ValueError('Missing decoder layer')
                trajectory=np.stack([captures[l] for l in range(52)])
                if trajectory.shape!=(52,len(ids)-slice_start,6656):raise ValueError('Unexpected trajectory shape')
                if not np.isfinite(trajectory).all():raise ValueError('Nonfinite residual')
                np.savez_compressed(out/f'trajectory-{i:02}.npz',residuals=trajectory,token_ids=np.array(ids[slice_start:],dtype=np.int64))
                artifacts.commit()
                for p in ALL_POINTS:states[p].append(trajectory[:,positions[p]])
                token_provenance.append({'id':r['id'],'pair_id':r['pair_id'],'fold':r['fold'],'group':r['group'],
                  'supported':r['supported'],'frame_sha256':r['frame_sha256'],
                  'candidate_sha256':hashlib.sha256(r['candidate'].encode()).hexdigest(),
                  'candidate_start':start,'candidate_tokens':len(ids)-start,'prompt_tokens':len(ids),
                  'point_indices_in_saved_slice':positions,'candidate_token_ids':ids[start:],
                  'artifact':f'trajectory-{i:02}.npz'})
                save('trajectory-token-provenance.json',token_provenance)
                print('Teacher-forced trajectory',i+1,'/36; candidate tokens',len(ids)-start,flush=True)
        finally:
            for h in handles:h.remove()
        if passes!=36:raise ValueError('One forward per record invariant failed')
        states={p:np.stack(x) for p,x in states.items()}
        np.savez_compressed(out/'trajectory-point-residuals.npz',**states);artifacts.commit()
        baseline={p:np.stack([fit_score(states[p][:,l],records)[0] for l in range(52)],axis=1) for p in ALL_POINTS}
        hidden_report=summarize_trajectory(baseline,records);save('trajectory-hidden-report.json',hidden_report)
        norm=copy.deepcopy(model.get_submodule(preflight['norm_path'])).float()
        head=model.get_output_embeddings().weight.detach().float()
        fit=np.array([r['fold']=='fit' for r in records]);lens={}
        for p in ALL_POINTS:
            scores=[]
            for l in range(52):
                a=torch.tensor(states[p][fit,l].mean(0),device='cuda:0',dtype=torch.float32)
                x=torch.tensor(states[p][:,l],device='cuda:0',dtype=torch.float32)
                with torch.no_grad():z=project_jacobian(norm,head,a,x).cpu().numpy()
                score,_=fit_score(z,records);scores.append(score);del z
            lens[p]=np.stack(scores,axis=1)
            print('Full-vocabulary norm/head Jacobian trajectory point complete:',p,flush=True)
        lens_report=summarize_trajectory(lens,records);save('trajectory-lens-report.json',lens_report)
        np.savez_compressed(out/'trajectory-all-layer-scores.npz',
          **{'hidden_'+p:x for p,x in baseline.items()},**{'lens_'+p:x for p,x in lens.items()})
        artifacts.commit()
        report={**provenance,'hidden_contrastive':hidden_report,'norm_head_jacobian':lens_report,
          'trajectory_tokens':token_provenance,'forward_passes':passes,
          'jacobian_scope':'Exact final norm/full-unembedding Jacobian at fit-only anchors; not full transformer network Jacobian',
          'elapsed_seconds':round(time.monotonic()-started,2),
          'runtime':{'torch':str(torch.__version__),'transformers':str(transformers.__version__),
            'gpu':torch.cuda.get_device_name(),'peak_gpu_memory_bytes':torch.cuda.max_memory_allocated(),'vocab_coordinates':int(head.shape[0])},
          'artifact_directory':str(out),'status':'complete','phase3_enabled':False}
        save('trajectory-report.json',report);return report
    except Exception as exc:
        save('trajectory-failure.json',{'error_type':type(exc).__name__,'error':str(exc)[:1200],
          'elapsed_seconds':round(time.monotonic()-started,2),'reservation':reservation,'phase3_enabled':False})
        raise


@app.local_entrypoint()
def run(inputs:str,output:str,gpu_window:bool=False):
    import sys
    sys.path.insert(0,str(HERE))
    from paired_analysis import validate_records
    from budget import reserve_window,record_result
    if not gpu_window:raise ValueError('Explicit finite window required')
    raw=Path(inputs).read_bytes();input_sha=hashlib.sha256(raw).hexdigest()
    if input_sha!='1f8fe74d3300b7aa09f1a76e723e5a323e686c5289c72fb95dfc8066bc33c17a':
        raise ValueError('Frozen camera payload changed')
    payload=json.loads(raw);validate_records(payload['records'])
    path=Path.home()/'.local/state/ambient-field-lens/budget.json'
    ledger=json.loads(path.read_text())
    if any(w.get('experiment')=='teacher-forced-trajectory-2026-10-28' for w in ledger['windows']):
        raise ValueError('Exactly one window authorized; recover artifacts, do not rerun')
    source=checked_download.remote()
    if source['revision']!='cec94fcfd6512f2cfe708138c32533b346ea4f69':raise ValueError('Checkpoint revision drift')
    preflight=trajectory_preflight.remote(payload['records'],payload['frames'])
    target=Path(output);target.parent.mkdir(parents=True,exist_ok=True)
    target.with_name('trajectory-cpu-preflight.json').write_text(json.dumps(preflight,indent=2))
    reservation=reserve_window(path)
    record_result(path,reservation['id'],experiment='teacher-forced-trajectory-2026-10-28',status='reserved')
    print('RESERVATION',json.dumps(reservation),flush=True)
    try:
        report=trajectory_research.remote(payload,reservation,preflight,input_sha)
        target.write_text(json.dumps(report,indent=2)+'\n')
        record_result(path,reservation['id'],status='complete',elapsed_seconds=report['elapsed_seconds'],artifact_directory=report['artifact_directory'])
        print('TRAJECTORY COMPLETE',output,flush=True)
    except BaseException as exc:
        record_result(path,reservation['id'],status='failed',error_type=type(exc).__name__,error=str(exc)[:500])
        raise
