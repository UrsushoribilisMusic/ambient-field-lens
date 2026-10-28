"""Live demo retrieval and frozen-prefill scoring. No benchmark or new fit protocol."""
import hashlib
import json
from pathlib import Path
import time
import modal

HERE=Path(__file__).resolve().parent
app=modal.App('ambient-field-lens-live-providers')
weights=modal.Volume.from_name('glimmer-weights',create_if_missing=False)
artifacts=modal.Volume.from_name('afl-recal-artifacts',create_if_missing=False)
corpus=modal.Volume.from_name('afl-ross-chroma',create_if_missing=False)
BASE=Path('/artifacts/live-providers')
RESIDUALS='/artifacts/578c40bb-df38-4b11-a342-f612685d75bd/heldout-prefill-residuals.npz'
SCORES='/artifacts/578c40bb-df38-4b11-a342-f612685d75bd/heldout-scores.npz'
REVISION='cec94fcfd6512f2cfe708138c32533b346ea4f69'
LAYER=27
cpu_base=modal.Image.debian_slim(python_version='3.12').pip_install('numpy==2.5.4','pillow','fastapi')
cpu=cpu_base.add_local_dir(HERE,'/opt/afl/providers')
retrieval_image=cpu_base.pip_install('chromadb==1.5.9').add_local_dir(HERE,'/opt/afl/providers')
gpu=(modal.Image.debian_slim(python_version='3.12')
 .pip_install('torch==2.14.1','transformers==5.21.0','accelerate==1.15.0','safetensors',
              'numpy==2.5.4','scikit-learn==1.9.1','scipy==1.18.1','pillow')
 .env({'HF_HUB_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1'})
 .pip_install('torchvision==0.29.1')
 .add_local_dir(HERE,'/opt/afl/providers'))


def _sys():
    import sys
    if '/opt/afl' not in sys.path:sys.path.insert(0,'/opt/afl')


@app.function(image=gpu,gpu=None,cpu=(1,2),memory=(4096,8192),volumes={'/artifacts':artifacts,'/weights':weights},timeout=180,
              min_containers=0,max_containers=1,scaledown_window=2,retries=0)
def export_frozen_direction(payload,expected_prefixes):
    records=payload['records']
    """Recover the existing fit-only direction, verify saved scores; no new cases."""
    import numpy as np
    import base64,io
    from PIL import Image
    from transformers import AutoProcessor
    proc=AutoProcessor.from_pretrained('/weights/Muse-Glimmer-30B',local_files_only=True,trust_remote_code=False)
    # Admission requires the serving prefix to reproduce the saved true-prefill
    # tokens. This is interface verification on old inputs, not a new score run.
    for i in (0,6,12,18,24,30):
        record=records[i]
        frame=payload['frames'][record['frame_sha256']]
        raw=base64.b64decode(frame['jpeg_base64'],validate=True)
        image=Image.open(io.BytesIO(raw)).convert('RGB')
        _sys()
        from providers.payloads import encode_prefill
        encoded=encode_prefill(proc,image,record['text'])
        prefix=hashlib.sha256(json.dumps(encoded['input_ids'][0].tolist()).encode()).hexdigest()
        if prefix!=expected_prefixes[i]:raise ValueError('serving_prefix_differs_from_frozen_prefix')
    if len(records)!=84 or len({r['id'] for r in records})!=84:
        raise ValueError('existing_84_record_manifest_required')
    with np.load(RESIDUALS) as data:states=data['states'][:,LAYER].astype(np.float64)
    with np.load(SCORES) as data:expected=data['hidden']
    if states.shape!=(84,6656):raise ValueError('residual_shape_changed')
    fit=np.array([r['fold']=='fit' for r in records]);supported=np.array([r['supported'] for r in records])
    if int(fit.sum())!=12:raise ValueError('frozen_fit_count_changed')
    direction=states[fit&supported].mean(0)-states[fit&~supported].mean(0)
    direction/=np.linalg.norm(direction)
    reproduced=(states@direction)/np.maximum(np.linalg.norm(states,axis=1),1e-12)
    difference=float(np.max(np.abs(reproduced-expected)))
    if difference>1e-12:raise ValueError('frozen_score_reproduction_failed')
    BASE.mkdir(parents=True,exist_ok=True)
    path=BASE/'frozen-prefill-layer27.npy'
    np.save(path,direction)
    meta={'schema':'frozen-contrastive-prefill-v1','model_revision':REVISION,'layer':LAYER,
          'direction_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'dimension':6656,
          'source_residuals':RESIDUALS,'source_scores':SCORES,'control_score_max_difference':difference,
          'fit_record_ids':[r['id'] for r in records if r['fold']=='fit'],
          'candidate_tokens_consumed':0,'threshold':None,'probability':False,'serving_prefix_controls_verified':6,
          'scope':'support in supplied manual context; not answer correctness or physical readiness'}
    (BASE/'frozen-prefill.json').write_text(json.dumps(meta,indent=2));artifacts.commit()
    return meta


@app.function(image=cpu,gpu=None,volumes={'/artifacts':artifacts},timeout=30,
              min_containers=0,max_containers=1,scaledown_window=2,retries=0)
def configure_window(window):
    """RPC-authenticated finite reservation; called only after the local grant ledger."""
    import math,re
    if (set(window)!={'id','expires_at','max_calls','reserved_usd'}
            or not re.fullmatch('[A-Za-z0-9_-]{1,80}',window['id'])
            or type(window['max_calls']) is not int or not 1<=window['max_calls']<=4
            or not isinstance(window['expires_at'],(int,float)) or not math.isfinite(window['expires_at'])
            or not time.time()<window['expires_at']<=time.time()+600
            or window['reserved_usd']!=4.0):
        raise ValueError('finite_four_dollar_window_required')
    BASE.mkdir(parents=True,exist_ok=True)
    path=BASE/'window.json'
    if path.exists():
        prior=json.loads(path.read_text())
        if prior['id']==window['id'] or prior['expires_at']>time.time():
            raise ValueError('window_already_used_or_active')
    if not (BASE/'frozen-prefill.json').exists():raise ValueError('frozen_direction_not_exported')
    path.write_text(json.dumps({**window,'attempts':[]}));artifacts.commit()
    return window


@app.function(image=retrieval_image,gpu=None,cpu=(1,2),memory=(2048,4096),volumes={'/corpus':corpus},timeout=120,
              min_containers=0,max_containers=1,scaledown_window=2,retries=0)
def retrieve(request:dict):
    _sys()
    from providers.payloads import COLLECTION
    import chromadb
    from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
    question=request.get('question');frame=request.get('frame_sha256')
    import re
    if not isinstance(question,str) or not 1<=len(question.encode())<=1000 or not re.fullmatch('[0-9a-f]{64}',frame or ''):
        raise ValueError('invalid_retrieval_request')
    report=json.loads(Path('/corpus/ingestion-report.json').read_text())
    if report['collection']!=COLLECTION:raise ValueError('corpus_fingerprint_changed')
    client=chromadb.PersistentClient(path='/corpus/chroma')
    collection=client.get_collection(COLLECTION,embedding_function=ONNXMiniLM_L6_V2(preferred_providers=['CPUExecutionProvider']))
    if collection.count()!=38:raise ValueError('corpus_count_changed')
    found=collection.query(query_texts=[question],n_results=3,include=['documents','metadatas','distances'])
    chunks=[{'id':ident,'text':text,'source':meta['source'],'source_sha256':meta['source_sha256'],
             'source_commit':meta['source_commit'],'distance':float(distance)}
            for ident,text,meta,distance in zip(found['ids'][0],found['documents'][0],found['metadatas'][0],found['distances'][0])]
    if not chunks:raise ValueError('no_ross_evidence')
    # Stable source order; no generated summaries inserted into evidence.
    context='\n\n'.join(c['text'] for c in chunks)
    return {'frame_sha256':frame,'collection':COLLECTION,'chunks':chunks,'context':context,
            'context_sha256':hashlib.sha256(context.encode()).hexdigest(),'gpu_used':False}


@app.cls(image=gpu,gpu='A100-80GB',cpu=(2,4),memory=(32768,65536),
         volumes={'/weights':weights,'/artifacts':artifacts},timeout=300,startup_timeout=300,
         min_containers=0,max_containers=1,buffer_containers=0,scaledown_window=2,retries=0)
class Glimmer:
    @modal.enter()
    def load(self):
        import numpy as np
        import torch
        from transformers import AutoProcessor,AutoModelForImageTextToText
        _sys()
        root=Path('/weights/Muse-Glimmer-30B')
        verified=json.loads((root/'verified-download.json').read_text())
        if verified.get('revision')!=REVISION or not verified.get('verified') or verified.get('weight_bytes')!=59_553_435_272:
            raise ValueError('verified_checkpoint_changed')
        self.meta=json.loads((BASE/'frozen-prefill.json').read_text())
        raw=(BASE/'frozen-prefill-layer27.npy').read_bytes()
        if hashlib.sha256(raw).hexdigest()!=self.meta['direction_sha256']:
            raise ValueError('direction_digest_changed')
        self.direction=np.load(BASE/'frozen-prefill-layer27.npy')
        self.processor=AutoProcessor.from_pretrained(root,local_files_only=True,trust_remote_code=False)
        self.model=AutoModelForImageTextToText.from_pretrained(root,dtype=torch.bfloat16,device_map='cuda:0',
                   local_files_only=True,trust_remote_code=False,attn_implementation='sdpa')
        self.model.eval();self.model.requires_grad_(False)
        paths=[name for name,m in self.model.named_modules() if isinstance(m,torch.nn.ModuleList)
               and name.endswith('layers') and len(m)==52]
        if len(paths)!=1:raise ValueError('decoder_ambiguous')
        self.layer=self.model.get_submodule(paths[0])[LAYER]

    @modal.method()
    def score(self,payload:dict):
        import base64,io
        import numpy as np
        import torch
        from PIL import Image
        from providers.payloads import validate,text,sha,encode_prefill
        raw=validate(payload)
        artifacts.reload()
        window=json.loads((BASE/'window.json').read_text())
        if payload['window_id']!=window['id'] or time.time()>window['expires_at']:
            raise ValueError('window_closed')
        image=Image.open(io.BytesIO(raw)).convert('RGB')
        prompt=text(payload['question'],payload['context'])
        encoded=encode_prefill(self.processor,image,prompt)
        if int(encoded['input_ids'].shape[-1])>1024 or 'pixel_values' not in encoded:
            raise ValueError('prefill_token_or_image_budget')
        if int(encoded['image_grid_thw'].prod())//4>256:raise ValueError('vision_token_budget')
        captures=[]
        def capture(module,args,output):
            h=output[0] if isinstance(output,tuple) else output
            captures.append(h[0,-1].detach().float().cpu().numpy())
        handle=self.layer.register_forward_hook(capture)
        started=time.monotonic()
        try:
            with torch.inference_mode():self.model(**{k:v.to('cuda:0') for k,v in encoded.items()},use_cache=False)
        finally:handle.remove()
        if len(captures)!=1:raise ValueError('prefill_capture_missing')
        residual=captures[0].astype(np.float64)
        score=float(residual@self.direction/max(float(np.linalg.norm(residual)),1e-12))
        if not np.isfinite(score):raise ValueError('nonfinite_score')
        return {'request_id':payload['request_id'],'frame_sha256':sha(raw),'question_sha256':sha(payload['question'].encode()),
                'context_sha256':sha(payload['context'].encode()),'score':score,'threshold':None,
                'method':'frozen_contrastive_true_prefill','layer':LAYER,'model_revision':REVISION,
                'direction_sha256':self.meta['direction_sha256'],'candidate_tokens_consumed':0,
                'prefix_sha256':sha(json.dumps(encoded['input_ids'][0].tolist()).encode()),
                'prefix_tokens':int(encoded['input_ids'].shape[-1]),'forward_passes':1,
                'elapsed_seconds':round(time.monotonic()-started,3),'probability':False}


@app.function(image=cpu,gpu=None,timeout=600,
              min_containers=0,max_containers=1,scaledown_window=2)
@modal.fastapi_endpoint(method='POST',requires_proxy_auth=True,docs=False)
def grounding(payload:dict):
    """Authenticated CPU gate BEFORE GPU allocation; same core as the RPC facade."""
    return score_request.remote(payload)


@app.function(image=cpu,gpu=None,volumes={'/artifacts':artifacts},timeout=600,
              min_containers=0,max_containers=1,scaledown_window=2,retries=0)
def score_request(payload:dict):
    return dispatch_score(payload)


def dispatch_score(payload):
    _sys()
    from providers.payloads import validate
    validate(payload)
    # One serial RPC function owns admission for both RPC and HTTP callers.
    # No @concurrent decorator; max_containers=1. Never use volume files as a
    # distributed lock across independently scaled functions.
    artifacts.reload()
    path=BASE/'window.json';window=json.loads(path.read_text())
    if payload.get('window_id')!=window['id'] or time.time()>window['expires_at']:
        raise ValueError('window_closed_no_gpu')
    if len(window['attempts'])>=window['max_calls']:
        raise ValueError('window_call_limit_no_gpu')
    if payload['request_id'] in [r['request_id'] for r in window['attempts']]:
        raise ValueError('request_already_attempted_no_retry')
    entry={'request_id':payload['request_id'],'attempted_at':time.time(),'frame_sha256':payload['frame_sha256']}
    window['attempts'].append(entry);path.write_text(json.dumps(window));artifacts.commit()
    folder=BASE/window['id']/payload['request_id'];folder.mkdir(parents=True,exist_ok=False)
    (folder/'request.json').write_text(json.dumps(payload))
    try:
        result=Glimmer().score.remote(payload)
        entry.update(status='complete',score=result['score'])
        (folder/'response.json').write_text(json.dumps(result))
        return result
    except Exception:
        entry['status']='failed_no_retry'
        raise
    finally:
        path.write_text(json.dumps(window));(folder/'attempt.json').write_text(json.dumps(entry));artifacts.commit()


@app.local_entrypoint()
def prepare(inputs:str,preflight:str,output:str):
    payload=json.loads(Path(inputs).read_text())
    # Existing frozen input digest, no agent-defined replacement labels.
    if hashlib.sha256(Path(inputs).read_bytes()).hexdigest()!='1d3b686c80f2a2196813a92af0b95e051b9d772a322904947d13c879f69f3994':
        raise ValueError('frozen_manifest_changed')
    prefixes=json.loads(Path(preflight).read_text())['actual_prefix_sha256']
    result=export_frozen_direction.remote(payload,prefixes)
    Path(output).write_text(json.dumps(result,indent=2));print(json.dumps(result))
