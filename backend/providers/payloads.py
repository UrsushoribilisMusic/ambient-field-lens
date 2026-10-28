"""Bound provider inputs and retain identities shared by /assist receipts."""
import base64
import hashlib
import io
import re
from PIL import Image

REVISION = 'cec94fcfd6512f2cfe708138c32533b346ea4f69'
LAYER = 27
COLLECTION = 'ross-manuals-2ca5f2f152267049'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def validate(payload):
    if not isinstance(payload, dict):
        raise ValueError('invalid_payload')
    allowed = {'request_id', 'question', 'context', 'image_jpeg_base64', 'frame_sha256', 'window_id'}
    if set(payload) - allowed:
        raise ValueError('unsupported_provider_fields')
    if not re.fullmatch('[A-Za-z0-9_-]{1,80}', payload.get('request_id', '')):
        raise ValueError('invalid_request_id')
    question, context = payload.get('question'), payload.get('context')
    if not isinstance(question, str) or not 1 <= len(question.encode()) <= 1000:
        raise ValueError('invalid_question')
    if not isinstance(context, str) or not 1 <= len(context.encode()) <= 12000:
        raise ValueError('retrieved_context_required')
    encoded = payload.get('image_jpeg_base64')
    if not isinstance(encoded, str) or len(encoded) > 4_194_304:
        raise ValueError('image_byte_limit')
    raw = base64.b64decode(encoded, validate=True)
    if sha(raw) != payload.get('frame_sha256'):
        raise ValueError('frame_digest_mismatch')
    with Image.open(io.BytesIO(raw)) as image:
        if image.format != 'JPEG' or image.width*image.height > 4_194_304 or image.getexif().get(274, 1) != 1:
            raise ValueError('normalized_jpeg_required')
        image.load()
    return raw


def text(question, context):
    # Preserve the frozen experiment's user-text template, without consuming a
    # candidate token. Scope remains support in supplied context, not truth.
    return ('Read the supplied manual excerpt and assess the candidate step.\n'
            'Manual excerpt: '+context+'\nQuestion: '+question)


def encode_prefill(processor,image,prompt):
    """Use the exact frozen continue-final-message template, then cut candidate.

    add_generation_prompt produces different model-specific reasoning tokens.
    The boundary sentinel is tokenized only to locate the cut and NEVER passed
    to the model; this is still one candidate-free prefill forward pass.
    """
    boundary='AFL_PREFILL_BOUNDARY'
    messages=[{'role':'user','content':[{'type':'image','image':image},{'type':'text','text':prompt}]},
              {'role':'assistant','content':boundary}]
    encoded=processor.apply_chat_template(messages,add_generation_prompt=False,continue_final_message=True,
        tokenize=True,return_tensors='pt',return_dict=True,reasoning_strength='low',max_image_tokens=256)
    ids=encoded['input_ids'][0].tolist()
    tokenizer=processor.tokenizer
    starts=[start for start in range(len(ids)-1,max(-1,len(ids)-257),-1)
            if tokenizer.decode(ids[start:],skip_special_tokens=True).strip()==boundary]
    if not starts or starts[0]<1:raise ValueError('prefill_boundary_not_found')
    start=starts[0]
    result=dict(encoded)
    for key in ('input_ids','attention_mask','token_type_ids','position_ids'):
        if key in result:
            if int(result[key].shape[-1])!=len(ids):raise ValueError('unaligned_prefix_tensor')
            result[key]=result[key][...,:start]
    return result
