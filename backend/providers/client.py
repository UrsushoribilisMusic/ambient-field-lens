"""Runtime provider facade for Muse's /assist integration. No verdict or motion IO."""
from dataclasses import asdict
import json
from pathlib import Path
import time
import uuid
from generation.wording import DEFAULT_LEDGER, append_event, private_write, utc
from readiness.adapters import canonical
from providers.payloads import validate,sha

APP='ambient-field-lens-live-providers'
PRIVATE=Path.home()/'Movies/Ambient-Field-Lens/live-provider-receipts'


def rpc(name,payload,*,ledger=DEFAULT_LEDGER,output_root=PRIVATE):
    """One attempted authenticated Modal call; durable local receipt, no retry."""
    import modal
    ident='modal-'+str(uuid.uuid4())
    folder=Path(output_root)/ident;folder.mkdir(parents=True,mode=0o700)
    request=canonical(payload);private_write(folder/'request.json',request)
    row={'job_id':ident,'event':'attempt','provider':'modal','purpose':name,
         'attempted_at':utc(),'request_sha256':sha(request),'usage':None,
         'estimated_api_cost_usd_uncached':None,'automatic_retries':0}
    private_write(folder/'attempt.json',canonical(row));append_event(ledger,row,unique_attempt=True)
    row={**row,'event':'outcome','status':'failed_no_retry'}
    started=time.monotonic()
    try:
        result=modal.Function.from_name(APP,name).remote(payload)
        private_write(folder/'response.json',canonical(result))
        row.update(status='complete',response_sha256=sha(canonical(result)))
        return result
    finally:
        row['completed_at']=utc();row['elapsed_seconds']=round(time.monotonic()-started,3)
        private_write(folder/'outcome.json',canonical(row));append_event(ledger,row)


def open_window(*,seconds=600,max_calls=4):
    from recal.budget import reserve_window,record_result
    if type(seconds) is not int or not 30<=seconds<=600 or type(max_calls) is not int or not 1<=max_calls<=4:
        raise ValueError('finite_window_required')
    # Even the H100 fallback plus maximum CPU/RAM fits the existing $4 envelope.
    if 3002*(.001097+4*.0000131+64*.00000222)>=4.:
        raise ValueError('gpu_rate_exceeds_reserved_window')
    ledger=Path.home()/'.local/state/ambient-field-lens/budget.json'
    reservation=reserve_window(ledger)
    window={'id':reservation['id'],'expires_at':time.time()+seconds,'max_calls':max_calls,'reserved_usd':4.0}
    record_result(ledger,reservation['id'],purpose='live-provider-window',status='reserved',expires_at=window['expires_at'])
    try:
        result=rpc('configure_window',window)
        record_result(ledger,reservation['id'],status='window_open')
        return result
    except Exception:
        record_result(ledger,reservation['id'],status='configure_failed_no_retry')
        raise


def retrieve(question,frame_sha256):
    return rpc('retrieve',{'question':question,'frame_sha256':frame_sha256})


def grounding(*,request_id,question,evidence,image_jpeg_base64,frame_sha256,window_id):
    if evidence['frame_sha256']!=frame_sha256 or not evidence['chunks']:
        raise ValueError('retrieval_frame_mismatch_or_empty')
    if sha(evidence['context'].encode())!=evidence['context_sha256']:
        raise ValueError('retrieval_context_digest_mismatch')
    payload={'request_id':request_id,'question':question,'context':evidence['context'],
             'image_jpeg_base64':image_jpeg_base64,'frame_sha256':frame_sha256,'window_id':window_id}
    validate(payload)
    result=rpc('score_request',payload)
    if (result['frame_sha256']!=frame_sha256 or result['context_sha256']!=evidence['context_sha256']
            or result['question_sha256']!=sha(question.encode())):
        raise ValueError('readout_binding_mismatch')
    return {**result,'retrieved_chunk_ids':[c['id'] for c in evidence['chunks']]}


def collect(*,image,request_id,question,window_id,paper_box=None):
    """One frame through retrieval, SAM and Glimmer. Muse composes world checks.

    Returns real mask candidates even when ambiguous; never treats a paper mask
    as pen presence, fitment, controller calibration, or approved procedure.
    """
    import base64
    from providers.sam import segment_paper
    frame=sha(image)
    evidence=retrieve(question,frame)
    segmentation=segment_paper(image,request_id=request_id,output_root=PRIVATE,box=paper_box)
    if not segmentation['masks']:
        return {'frame_sha256':frame,'retrieval':evidence,'segmentation':segmentation,
                'grounding':None,'reason':'paper_mask_unavailable','step':None}
    score=grounding(request_id=request_id,question=question,evidence=evidence,
        image_jpeg_base64=base64.b64encode(image).decode(),frame_sha256=frame,window_id=window_id)
    return {'frame_sha256':frame,'retrieval':evidence,'segmentation':segmentation,'grounding':score}


def close_window(window_id):
    from recal.budget import record_result
    result=rpc('close_window',{'id':window_id})
    ledger=Path.home()/'.local/state/ambient-field-lens/budget.json'
    record_result(ledger,window_id,status='closed',provider_attempts=result['attempts'])
    return result
