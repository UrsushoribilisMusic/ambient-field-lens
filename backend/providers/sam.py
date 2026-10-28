"""One receipted Meta SAM call on the supplied demo frame; no retries."""
import asyncio
from dataclasses import asdict
import json
from pathlib import Path
import time
import urllib.error
import urllib.request
from generation.wording import append_event, credential, DEFAULT_LEDGER, private_write, utc
from providers.payloads import sha
from readiness.adapters import canonical, parse_sse
from readiness.checks import Mask

ENDPOINT = 'https://api.meta.ai/v1/responses'


async def decode(raw, frame_sha256, width, height):
    from meta_sam_parser import parse_responses_stream, image_segmentation_format, decode_mask_to_raster
    events = parse_sse(raw)
    if not events or events[-1].get('type') != 'response.completed':
        raise ValueError('sam_incomplete')
    terminal = events[-1]['response']
    if terminal.get('model') != 'sam-3.1' or terminal.get('error') or terminal.get('incomplete_details'):
        raise ValueError('sam_terminal_error')
    async def source():
        for event in events:
            yield event
    result = await parse_responses_stream(source(), image_segmentation_format()).final_result()
    if result.outcome.status != 'completed' or result.diagnostics:
        raise ValueError('sam_parser_diagnostic')
    boxes, masks = {}, {}
    for record in result.records:
        target = masks if record.kind == 'mask' else boxes if record.kind == 'box' else None
        if target is None or record.object_id in target:
            raise ValueError('sam_unexpected_or_duplicate_object')
        target[record.object_id] = record
    if set(boxes) != set(masks) or len(masks) > 16:
        raise ValueError('sam_object_mismatch')
    output = []
    for ident, record in masks.items():
        box = boxes[ident]
        coords = (box.left, box.top, box.right, box.bottom)
        if any(not float(v).is_integer() for v in coords):
            raise ValueError('sam_noninteger_bounds')
        left, top, right, bottom = map(int, coords)
        if not (0 <= left < right <= width and 0 <= top < bottom <= height):
            raise ValueError('sam_bounds_mismatch')
        if (record.mask.width, record.mask.height) != (right-left, bottom-top):
            raise ValueError('sam_resampling_not_accepted')
        if record.mask.width*record.mask.height > 4_194_304 or record.mask.encoding != 'one_bit':
            raise ValueError('sam_encoding_or_size')
        raster = decode_mask_to_raster(record.mask)
        if len(raster) != (right-left)*(bottom-top):
            raise ValueError('sam_raster_size')
        cells = frozenset((left+i%(right-left), top+i//(right-left)) for i, value in enumerate(raster) if value)
        if len(cells) > 1_000_000:
            raise ValueError('sam_pixel_budget')
        output.append((ident, Mask(frame_sha256, width, height, cells, 'paper', True, len(masks) != 1)))
    return output, terminal.get('usage')


def segment_paper(image, *, request_id, output_root, box=None, ledger=DEFAULT_LEDGER):
    """Returns candidate masks. Multiple candidates stay ambiguous for identity review.

    Optional box is an explicit server-reviewed ROI in THIS frame, never a cached
    output mask. A box-prompted mask is not autonomous object recognition.
    """
    import base64, io, re
    from PIL import Image
    if not re.fullmatch('[A-Za-z0-9_-]{1,80}', request_id):
        raise ValueError('invalid_request_id')
    with Image.open(io.BytesIO(image)) as decoded:
        width, height = decoded.size
        if decoded.format != 'JPEG' or width*height > 4_194_304 or decoded.getexif().get(274, 1) != 1:
            raise ValueError('normalized_jpeg_required')
        decoded.load()
    if box is None:
        prompt = 'white drawing paper'
        origin = 'concept_candidates_require_identity'
    else:
        if len(box) != 4 or any(type(v) is not int for v in box):
            raise ValueError('invalid_reviewed_roi')
        x1,y1,x2,y2 = box
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            raise ValueError('invalid_reviewed_roi')
        prompt = f'<0f>0<|box;x1={x1};y1={y1};x2={x2};y2={y2};w={width};h={height}|>'
        origin = 'explicit_manual_box_requires_identity_review'
    body = {'model':'sam-3.1', 'input':[{'type':'message','role':'user','content':[
        {'type':'input_text','text':prompt}, {'type':'input_image','image_url':
        'data:image/jpeg;base64,'+base64.b64encode(image).decode()}]}],
        'stream':True, 'metadata':{'mask_encoding':'one_bit'}}
    request_bytes = canonical(body)
    key = credential('meta')
    folder = Path(output_root)/('sam-'+request_id)
    folder.mkdir(parents=True, exist_ok=False, mode=0o700)
    private_write(folder/'frame.jpg',image)
    private_write(folder/'request.json',request_bytes)
    row = {'job_id':'sam-'+request_id,'event':'attempt','attempted_at':utc(), 'provider':'meta',
           'model':'sam-3.1','frame_sha256':sha(image),'request_sha256':sha(request_bytes),
           'purpose':'live_demo_segmentation','origin':origin,'automatic_retries':0,
           'usage':None,'estimated_api_cost_usd_uncached':None}
    private_write(folder/'attempt.json',canonical(row)); append_event(ledger,row,unique_attempt=True)
    row={**row,'event':'outcome','status':'failed_no_retry'}
    started=time.monotonic()
    try:
        request=urllib.request.Request(ENDPOINT,data=request_bytes,headers={
            'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        # No credential-bearing redirect or unbounded response buffering.
        from generation.wording import NoRedirect
        with urllib.request.build_opener(NoRedirect()).open(request,timeout=90) as response:
            raw=response.read(8_388_609); row['http_status']=response.status
        if len(raw)>8_388_608 or key.encode() in raw:
            raise ValueError('sam_response_rejected')
        private_write(folder/'raw.sse',raw)
        masks,usage=asyncio.run(decode(raw,sha(image),width,height))
        row.update(usage=usage,status='mask_candidates_decoded',mask_count=len(masks),response_sha256=sha(raw))
        for ident,mask in masks:
            # PNG is a lossless mask at original frame dimensions, not a bbox.
            bitmap=Image.new('1',(width,height)); bitmap.putdata([
                (x,y) in mask.pixels for y in range(height) for x in range(width)])
            name='mask-'+str(len(list(folder.glob('mask-*.png'))))+'.png'
            bitmap.save(folder/name)
        private_write(folder/'masks.json',canonical({'frame_sha256':sha(image),'origin':origin,
            'candidates':[{'object_id':str(ident),'pixel_count':len(mask.pixels),
                           'ambiguous':mask.ambiguous} for ident,mask in masks]}))
    except urllib.error.HTTPError as exc:
        row.update(http_status=exc.code,status='http_error_no_retry'); masks=[]
    except Exception:
        row['status']='failed_no_retry'; masks=[]
    row.update(completed_at=utc(),elapsed_seconds=round(time.monotonic()-started,3))
    private_write(folder/'outcome.json',canonical(row)); append_event(ledger,row)
    return {'receipt':row,'masks':masks,'folder':str(folder)}
