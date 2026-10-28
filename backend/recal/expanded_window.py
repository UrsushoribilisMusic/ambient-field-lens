"""Finite offline paired comparison; same cases, activations and folds in both arms."""
import datetime,hashlib,json
from pathlib import Path
import modal
app=modal.App('ambient-field-lens-frozen-label-wording')
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
 .add_local_file(HERE/'trajectory_analysis.py','/opt/afl/trajectory_analysis.py')
 .add_local_file(HERE/'expanded_analysis.py','/opt/afl/expanded_analysis.py'))


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
def expanded_preflight(records,frames=None):
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
    from expanded_analysis import prefill_inputs
    prefixes=[prefill_inputs(e,start) for e,start in zip(enc,starts)]
    prefix_hashes=[hashlib.sha256(json.dumps(e['input_ids'][0].tolist()).encode()).hexdigest() for e in prefixes]
    positions=[trajectory_indices(n) for n in counts]
    return {'actual_prefix_tokens':starts,'actual_prefix_sha256':prefix_hashes,'candidate_tokens_consumed':0,'candidate_starts':starts,'candidate_counts':counts,'trajectory_indices':positions,'loader_kind':kind,'decoder_path':paths[0],'norm_path':norm_path,'norm_class':type(norm).__name__,
      'cases_checked':len(records),'maximum_prompt_tokens':max(lengths),'prompt_tokens':lengths,
      'image_input':bool(frames),'frame_count':len(frames or {}),'max_image_tokens':256 if frames else None,
      'image_grids':[e['image_grid_thw'].tolist() for e in enc] if frames else [],
      'actual_norm_jvp_cpu_verified':True,'candidate_token_readout_verified':True,'gpu_used':False}


@app.function(image=image,gpu='A100-80GB',cpu=(2,4),memory=(32768,65536),
 volumes={'/weights':weights,'/artifacts':artifacts},timeout=2700,startup_timeout=300,retries=0,
 min_containers=0,max_containers=1,buffer_containers=0,scaledown_window=2,single_use_containers=True)
def expanded_research(payload,reservation,preflight,input_sha):
    import copy,sys,time
    import numpy as np
    import torch,transformers
    from transformers import AutoProcessor,AutoModelForImageTextToText
    sys.path.insert(0,'/opt/afl')
    from expanded_analysis import validate,prefill_inputs,report
    from paired_analysis import fit_score
    from jacobian_lens import project_jacobian
    records=payload['records'];validate(records,payload['reviewed_records'])
    started=time.monotonic();out=Path('/artifacts')/reservation['id'];out.mkdir(parents=True,exist_ok=True)
    def save(name,obj):
        (out/name).write_text(json.dumps(obj,indent=2));artifacts.commit()
    provenance={k:payload[k] for k in ['sources','cache_sha256','base_inputs_sha256','review_sha256','reviewed_records_sha256','author_review','case_origin']}
    provenance.update(input_sha256=input_sha,reservation=reservation,preflight=preflight,phase3_enabled=False,
      source_revision='cec94fcfd6512f2cfe708138c32533b346ea4f69',fixed_layers={'hidden_contrastive':27,'norm_head_jacobian':22},
      candidate_tokens_consumed=0,sampling=False)
    save('heldout-provenance.json',provenance)
    try:
        root='/weights/Muse-Glimmer-30B'
        tok=AutoProcessor.from_pretrained(root,local_files_only=True,trust_remote_code=False)
        model=AutoModelForImageTextToText.from_pretrained(root,dtype=torch.bfloat16,device_map='cuda:0',local_files_only=True,trust_remote_code=False,attn_implementation='sdpa')
        model.eval();model.requires_grad_(False)
        layers=model.get_submodule(preflight['decoder_path']);captures={}
        def capture(i):
            def hook(module,args,output):
                h=output[0] if isinstance(output,tuple) else output
                captures[i]=h[0,-1].detach().float().cpu().numpy()
            return hook
        handles=[layer.register_forward_hook(capture(i)) for i,layer in enumerate(layers)]
        states=[];passes=0;tokens=[]
        try:
            for i,r in enumerate(records):
                full=encode_record(tok,r,payload['frames']);start=preflight['candidate_starts'][i]
                encoded=prefill_inputs(full,start)
                ids=encoded['input_ids'][0].tolist()
                if hashlib.sha256(json.dumps(ids).encode()).hexdigest()!=preflight['actual_prefix_sha256'][i]:raise ValueError('Native prefix drift')
                captures.clear()
                with torch.inference_mode():model(**{k:v.to('cuda:0') for k,v in encoded.items()},use_cache=False)
                passes+=1
                if len(captures)!=52:raise ValueError('Missing decoder layer')
                states.append(np.stack([captures[l] for l in range(52)]))
                tokens.append({'id':r['id'],'parent_id':r['parent_id'],'prefix_tokens':len(ids),'prefix_sha256':preflight['actual_prefix_sha256'][i],'candidate_tokens_consumed':0})
                print('Actual prefill',i+1,'/84',flush=True)
        finally:
            for h in handles:h.remove()
        states=np.stack(states)
        if states.shape!=(84,52,6656) or passes!=84:raise ValueError('Forward/shape invariant failed')
        np.savez_compressed(out/'heldout-prefill-residuals.npz',states=states);artifacts.commit()
        save('heldout-prefix-provenance.json',tokens)
        baseline,_=fit_score(states[:,27],records)
        hidden_report=report(baseline,records,27)
        norm=copy.deepcopy(model.get_submodule(preflight['norm_path'])).float()
        head=model.get_output_embeddings().weight.detach().float()
        fit=np.array([r['fold']=='fit' for r in records]);x=torch.tensor(states[:,22],device='cuda:0',dtype=torch.float32)
        anchor=torch.tensor(states[fit,22].mean(0),device='cuda:0',dtype=torch.float32)
        with torch.no_grad():z=project_jacobian(norm,head,anchor,x).cpu().numpy()
        lens,_=fit_score(z,records);lens_report=report(lens,records,22)
        np.savez_compressed(out/'heldout-scores.npz',hidden=baseline,jacobian_lens=lens);artifacts.commit()
        result={**provenance,'hidden_contrastive':hidden_report,'norm_head_jacobian':lens_report,
          'prefix_provenance':tokens,'forward_passes':passes,
          'record_metadata':[{k:r[k] for k in ['id','pair_id','parent_id','group','fold','partition','supported','frame_sha256']} for r in records],
          'jacobian_scope':'Final norm/full-unembedding readout derivative at fit-only anchor; not complete transformer Jacobian',
          'elapsed_seconds':round(time.monotonic()-started,2),
          'runtime':{'torch':str(torch.__version__),'transformers':str(transformers.__version__),'gpu':torch.cuda.get_device_name(),
            'peak_gpu_memory_bytes':torch.cuda.max_memory_allocated(),'vocab_coordinates':int(head.shape[0])},
          'artifact_directory':str(out),'status':'complete','phase3_enabled':False}
        save('heldout-report.json',result);return result
    except Exception as exc:
        save('heldout-failure.json',{'error_type':type(exc).__name__,'error':str(exc)[:1200],'reservation':reservation,'elapsed_seconds':round(time.monotonic()-started,2)})
        raise


@app.local_entrypoint()
def run(inputs:str,output:str,gpu_window:bool=False):
    import sys
    sys.path.insert(0,str(HERE))
    from expanded_analysis import validate
    from budget import reserve_window,record_result
    if not gpu_window:raise ValueError('Explicit finite window required')
    repo=HERE.parents[1]
    manifest=json.loads((repo/'docs/verification/heldout-wording-manifest-2026-10-28.json').read_text())
    raw=Path(inputs).read_bytes();input_sha=hashlib.sha256(raw).hexdigest()
    if input_sha!=manifest['input_sha256']:raise ValueError('Frozen expanded inputs changed')
    payload=json.loads(raw);validate(payload['records'],payload['reviewed_records'])
    base_path=Path.home()/'Movies/Ambient-Field-Lens/2026-10-28/paired-comparison/paired-camera-inputs.json'
    base_raw=base_path.read_bytes();base=json.loads(base_raw)
    if hashlib.sha256(base_raw).hexdigest()!=manifest['base_inputs_sha256']:raise ValueError('Reviewed snapshot changed')
    if payload['reviewed_records']!=base['records'] or payload['frames']!=base['frames']:raise ValueError('Only reviewed facts/frames allowed')
    review=(repo/'docs/verification/label-review-2026-10-28.md').read_bytes()
    if hashlib.sha256(review).hexdigest()!=manifest['review_sha256'] or payload['review_sha256']!=manifest['review_sha256']:raise ValueError('Label freeze changed')
    ledger_path=Path.home()/'.local/state/ambient-field-lens/budget.json'
    ledger=json.loads(ledger_path.read_text());tag='frozen-label-heldout-wording-2026-10-28'
    if any(w.get('experiment')==tag for w in ledger['windows']):raise ValueError('One window only; recover, do not rerun')
    source=checked_download.remote()
    if source['revision']!='cec94fcfd6512f2cfe708138c32533b346ea4f69':raise ValueError('Checkpoint drift')
    preflight=expanded_preflight.remote(payload['records'],payload['frames'])
    target=Path(output);target.parent.mkdir(parents=True,exist_ok=True)
    target.with_name('heldout-cpu-preflight.json').write_text(json.dumps(preflight,indent=2))
    reservation=reserve_window(ledger_path)
    record_result(ledger_path,reservation['id'],experiment=tag,status='reserved',input_sha256=input_sha,review_sha256=manifest['review_sha256'])
    print('RESERVATION',json.dumps(reservation),flush=True)
    try:
        result=expanded_research.remote(payload,reservation,preflight,input_sha)
        target.write_text(json.dumps(result,indent=2)+'\n')
        record_result(ledger_path,reservation['id'],status='complete',elapsed_seconds=result['elapsed_seconds'],artifact_directory=result['artifact_directory'])
        print('FROZEN-LABEL HELDOUT COMPLETE',output,flush=True)
    except BaseException as exc:
        record_result(ledger_path,reservation['id'],status='failed',error_type=type(exc).__name__,error=str(exc)[:500])
        raise
