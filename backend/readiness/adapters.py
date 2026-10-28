"""Frame-bound offline adapters. No network clients, secrets, GPU or motion IO.

LIVE rejects stale evidence. ARCHIVE decodes explicitly historical artifacts and
marks every record ineligible for live admission; it never changes timestamps.
Local receipt linkage is provenance, not a provider-signed image attestation.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
import hashlib
import io
import json
from math import isfinite
import re

from PIL import Image

from .checks import Fitment, Frame, Mask
from .evidence import Provenance
from .presence import Observation, Visibility

MAX_IMAGE_PIXELS = 16_777_216
MAX_RESPONSE_BYTES = 8_388_608
MAX_MASK_RASTER_PIXELS = 4_194_304
MAX_MASK_CELLS = 1_000_000
MAX_FRAME_AGE = 5.0
CLOCK_SKEW = 2.0


class AdapterError(ValueError):
    """Stable reason code only; never include provider payloads or image data."""


class Mode(str, Enum):
    LIVE = 'live'
    ARCHIVE = 'archival_replay'


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise AdapterError('duplicate_json_key')
            result[key] = value
        return result
    try:
        return json.loads(data, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(AdapterError('nonfinite_json')))
    except AdapterError:
        raise
    except (ValueError, TypeError, UnicodeError):
        raise AdapterError('invalid_json') from None


def _time(value):
    try:
        result = datetime.fromisoformat(value).timestamp() if isinstance(value, str) else float(value)
    except (ValueError, TypeError, OverflowError):
        raise AdapterError('invalid_timestamp') from None
    if isinstance(value, bool) or not isfinite(result):
        raise AdapterError('invalid_timestamp')
    if isinstance(value, str) and datetime.fromisoformat(value).tzinfo is None:
        raise AdapterError('timestamp_timezone_missing')
    return result


@dataclass(frozen=True)
class Binding:
    frame: Frame
    provider: str
    model: str
    response_id: str
    request_started_at: float
    prompt: str
    prompt_kind: str  # boxes, concept, structured_json
    object_roles: tuple[tuple[str, str], ...]
    receipt_sha256: str
    response_sha256: str
    request_sha256: str
    request_digest_basis: str
    capture_clock_verified: bool
    linkage: str


@dataclass(frozen=True)
class Adapted:
    masks: tuple[Mask, ...]
    observations: tuple[Observation, ...]
    fitment: Fitment | None
    provenance: Provenance
    warnings: tuple[str, ...] = ()

    def require_live(self, frame: Frame, *, now: float):
        p = self.provenance
        if p.mode != Mode.LIVE.value:
            raise AdapterError('archival_records_not_live')
        if p.capture_clock_verified is not True:
            raise AdapterError('capture_clock_unverified')
        identity = (p.frame_sha256, p.width, p.height, p.camera, p.rig,
                    p.surface_pose, p.tool, p.controller_session, p.frame_captured_at)
        if identity != _frame_identity(frame):
            raise AdapterError('frame_context_mismatch')
        for record in (*self.masks, *self.observations, *((self.fitment,) if self.fitment else ())):
            provenance = record.provenance
            if (record.frame_sha256 != frame.sha256 or provenance is None
                    or replace(provenance, role='', object_id='', object_bounds=None) != replace(p, role='', object_id='', object_bounds=None)):
                raise AdapterError('mixed_record_provenance')
            if isinstance(record, (Mask, Observation)) and (record.width, record.height) != (frame.width, frame.height):
                raise AdapterError('mixed_record_dimensions')
            role = record.kind if isinstance(record, Mask) else record.role if isinstance(record, Observation) else 'fitment'
            if provenance.role != role:
                raise AdapterError('mixed_record_role')
            if isinstance(record, Fitment) and record.tool != frame.tool:
                raise AdapterError('mixed_record_tool')
        _fresh(frame, now)
        if now + CLOCK_SKEW < p.response_completed_at:
            raise AdapterError('future_response')
        return self


def _frame_identity(frame):
    return (frame.sha256, frame.width, frame.height, frame.camera, frame.rig,
            frame.surface_pose, frame.tool, frame.controller_session, frame.captured_at)


def _fresh(frame, now):
    if not all(isfinite(v) for v in (frame.captured_at, now)) or not 0 <= now - frame.captured_at <= MAX_FRAME_AGE:
        raise AdapterError('stale_or_future_frame')


def request_body_from_receipt(image, receipt):
    media_type = 'image/png' if image.startswith(b'\x89PNG') else 'image/jpeg'
    stream = receipt.get('stream', True)  # Legacy S03 was streamed.
    if type(stream) is not bool:
        raise AdapterError('request_stream_invalid')
    body = {'model': receipt['model'], 'input': [{'type': 'message', 'role': 'user', 'content': [
        {'type': 'input_text', 'text': receipt['prompt']},
        {'type': 'input_image', 'image_url': 'data:' + media_type + ';base64,' + base64.b64encode(image).decode()}]}],
        'stream': stream, 'metadata': receipt.get('metadata', {})}
    if 'max_output_tokens' in receipt:
        limit = receipt['max_output_tokens']
        if type(limit) is not int or not 16 <= limit <= 8192:
            raise AdapterError('request_output_budget_invalid')
        body['max_output_tokens'] = limit
    if 'store' in receipt:
        if type(receipt['store']) is not bool:
            raise AdapterError('request_store_invalid')
        body['store'] = receipt['store']
    if 'reasoning' in receipt:
        if receipt['reasoning'] != {'effort': 'low'}:
            raise AdapterError('request_reasoning_invalid')
        body['reasoning'] = receipt['reasoning']
    return body


def reconstructed_request_hash(image, receipt):
    # Original S03 did not save the complete request bytes. Name the derivation.
    return sha256(canonical(request_body_from_receipt(image, receipt)))


def _validate(frame, binding, image, receipt_bytes, response_bytes, now, mode, request_bytes=None):
    if any(not isinstance(value, bytes) for value in (image, receipt_bytes, response_bytes)):
        raise AdapterError('artifact_bytes_required')
    if len(image) > 33_554_432:
        raise AdapterError('image_byte_budget_exceeded')
    for value in (frame.captured_at, binding.request_started_at, now):
        _time(value)
    if not isinstance(mode, Mode):
        raise AdapterError('invalid_mode')
    if _frame_identity(frame) != _frame_identity(binding.frame):
        raise AdapterError('frame_context_mismatch')
    if not re.fullmatch(r'[0-9a-f]{64}', frame.sha256) or sha256(image) != frame.sha256:
        raise AdapterError('image_digest_mismatch')
    if not all((frame.camera, frame.rig, frame.surface_pose, frame.tool, binding.provider,
                binding.model, binding.response_id, binding.linkage)):
        raise AdapterError('missing_provenance_identity')
    if sha256(receipt_bytes) != binding.receipt_sha256:
        raise AdapterError('receipt_digest_mismatch')
    if len(response_bytes) > MAX_RESPONSE_BYTES or sha256(response_bytes) != binding.response_sha256:
        raise AdapterError('response_digest_or_budget_mismatch')
    try:
        with Image.open(io.BytesIO(image)) as decoded:
            if (decoded.format not in ('JPEG', 'PNG') or decoded.size != (frame.width, frame.height)
                    or type(frame.width) is not int or type(frame.height) is not int
                    or frame.width <= 0 or frame.height <= 0 or frame.width * frame.height > MAX_IMAGE_PIXELS):
                raise AdapterError('image_dimensions_or_format_mismatch')
            if decoded.getexif().get(274, 1) != 1:
                raise AdapterError('image_orientation_not_normalized')
            decoded.load()
    except AdapterError:
        raise
    except Exception:
        raise AdapterError('image_decode_failed') from None
    receipt = _json(receipt_bytes)
    if (not isinstance(receipt, dict) or receipt.get('image_sha256') != frame.sha256 or receipt.get('model') != binding.model
            or receipt.get('prompt') != binding.prompt or receipt.get('image_bytes') != len(image)):
        raise AdapterError('request_receipt_mismatch')
    started = _time(receipt.get('attempted_at'))
    if started != binding.request_started_at or frame.captured_at > started + CLOCK_SKEW:
        raise AdapterError('request_frame_time_mismatch')
    if binding.request_digest_basis == 'captured_request_bytes':
        if (not isinstance(request_bytes, bytes) or len(request_bytes) > 50_331_648
                or sha256(request_bytes) != binding.request_sha256
                or canonical(_json(request_bytes)) != canonical(request_body_from_receipt(image, receipt))):
            raise AdapterError('captured_request_mismatch')
    elif binding.request_digest_basis == 'reconstructed_from_saved_receipt':
        if request_bytes is not None or reconstructed_request_hash(image, receipt) != binding.request_sha256:
            raise AdapterError('request_fingerprint_mismatch')
    else:
        raise AdapterError('request_fingerprint_mismatch')
    if not isfinite(now) or started > now + CLOCK_SKEW:
        raise AdapterError('future_request')
    if mode is Mode.LIVE:
        _fresh(frame, now)
        if binding.capture_clock_verified is not True:
            raise AdapterError('capture_clock_unverified')
    return receipt


def parse_sse(data):
    """Parse saved SSE only; reject truncation/trailing events later."""
    try:
        text = data.decode('utf-8')
    except UnicodeError:
        raise AdapterError('invalid_sse_encoding') from None
    events, buffer, event_name = [], [], None
    done = False
    def emit():
        nonlocal done
        if not buffer:
            return
        value = '\n'.join(buffer)
        if value == '[DONE]':
            done = True
            return
        if done:
            raise AdapterError('events_after_done')
        event = _json(value)
        if not isinstance(event, dict) or event_name is not None and event.get('type') != event_name:
            raise AdapterError('invalid_sse_event')
        events.append(event)
    for line in text.splitlines() + ['']:
        if not line:
            emit()
            buffer, event_name = [], None
        elif line.startswith('data:'):
            buffer.append(line[5:].lstrip(' '))
        elif line.startswith('event:'):
            event_name = line[6:].strip()
        elif line.startswith(':') or line.startswith('id:') or line.startswith('retry:'):
            continue
        else:
            raise AdapterError('unsupported_sse_field')
    return events


def _response_times(response, binding, now):
    if not isinstance(response, dict):
        raise AdapterError('provider_envelope_invalid')
    if response.get('id') != binding.response_id or response.get('model') != binding.model:
        raise AdapterError('provider_identity_mismatch')
    if response.get('status') != 'completed' or response.get('error') is not None or response.get('incomplete_details') is not None:
        raise AdapterError('provider_response_incomplete')
    created, completed = _time(response.get('created_at')), _time(response.get('completed_at'))
    if created < binding.request_started_at - CLOCK_SKEW or completed < created or completed > now + CLOCK_SKEW:
        raise AdapterError('response_time_mismatch')
    return created, completed


def _provenance(frame, binding, times, now, mode, origin, role='', object_id='', parser='', bounds=None):
    return Provenance(binding.provider, binding.model, binding.response_id, frame.sha256,
                      frame.width, frame.height, frame.camera, frame.rig, frame.surface_pose,
                      frame.tool, frame.controller_session, frame.captured_at, binding.capture_clock_verified, binding.request_started_at,
                      times[0], times[1], now, mode.value, binding.receipt_sha256, binding.request_sha256,
                      binding.request_digest_basis, binding.response_sha256, sha256(binding.prompt.encode()),
                      origin, object_id, role, parser, binding.linkage,
                      mask_encoding='one_bit' if parser == 'meta-sam-parser==0.1.0' else '', object_bounds=bounds)


def _sam_prompt(binding, frame):
    roles = dict(binding.object_roles)
    if len(roles) != len(binding.object_roles) or not roles or any(v not in ('paper', 'pen', 'holder') for v in roles.values()):
        raise AdapterError('invalid_semantic_role_bindings')
    if binding.prompt_kind == 'boxes':
        pattern = r'(\d+)<\|box;x1=(\d+);y1=(\d+);x2=(\d+);y2=(\d+);w=(\d+);h=(\d+)\|>'
        text = binding.prompt
        if not text.startswith('<0f>'):
            raise AdapterError('unsupported_sam_prompt')
        chunks = text[4:].split(',')
        seen = []
        for chunk in chunks:
            match = re.fullmatch(pattern, chunk)
            if not match:
                raise AdapterError('unsupported_sam_prompt')
            ident, x1, y1, x2, y2, w, h = match.groups()
            x1, y1, x2, y2, w, h = map(int, (x1, y1, x2, y2, w, h))
            if (w, h) != (frame.width, frame.height) or not (0 <= x1 <= x2 < w and 0 <= y1 <= y2 < h):
                raise AdapterError('sam_prompt_coordinates_mismatch')
            seen.append(ident)
        if len(seen) != len(set(seen)) or set(seen) != set(roles):
            raise AdapterError('sam_prompt_object_binding_mismatch')
        return roles, 'manual_box_prompt'
    if binding.prompt_kind == 'concept':
        concepts = {'paper': 'paper', 'graph paper': 'paper', 'pen': 'pen', 'pen holder': 'holder'}
        if roles != {'*': concepts.get(binding.prompt)}:
            raise AdapterError('sam_concept_binding_mismatch')
        return roles, 'model_concept'
    raise AdapterError('unsupported_sam_prompt')


async def adapt_sam(frame, binding, image, receipt_bytes, response_sse, *, now,
                    mode=Mode.LIVE, saved_events_json=None, request_bytes=None):
    receipt = _validate(frame, binding, image, receipt_bytes, response_sse, now, mode, request_bytes)
    if binding.model != 'sam-3.1' or receipt.get('metadata') != {'mask_encoding': 'one_bit'}:
        raise AdapterError('sam_request_contract_mismatch')
    roles, origin = _sam_prompt(binding, frame)
    events = parse_sse(response_sse)
    if saved_events_json is not None and canonical(_json(saved_events_json)) != canonical(events):
        raise AdapterError('saved_event_artifacts_disagree')
    if not events or events[0].get('type') != 'response.created' or events[-1].get('type') != 'response.completed':
        raise AdapterError('sam_stream_incomplete')
    sequences, completed = [], []
    for event in events:
        number = event.get('sequence_number')
        if type(number) is not int or number < 0:
            raise AdapterError('sam_sequence_invalid')
        sequences.append(number)
        if event.get('type') in ('error', 'response.failed', 'response.incomplete'):
            raise AdapterError('sam_stream_failed')
        if 'response' in event:
            response = event['response']
            if not isinstance(response, dict) or response.get('id') != binding.response_id or response.get('model') != binding.model:
                raise AdapterError('provider_identity_mismatch')
        if event.get('type') == 'response.completed':
            completed.append(event['response'])
    if len(completed) != 1 or any(b <= a for a, b in zip(sequences, sequences[1:])):
        raise AdapterError('sam_sequence_or_terminal_mismatch')
    times = _response_times(completed[0], binding, now)
    for event in events:
        response = event.get('response')
        if response is not None and (response.get('created_at') != completed[0].get('created_at')
                                     or response.get('metadata') != receipt['metadata']
                                     or response.get('error') is not None
                                     or response.get('incomplete_details') is not None):
            raise AdapterError('sam_response_snapshots_disagree')
    try:
        from meta_sam_parser import parse_responses_stream, image_segmentation_format, decode_mask_to_raster
        async def source():
            for event in events:
                yield event
        result = await parse_responses_stream(source(), image_segmentation_format()).final_result()
    except Exception:
        raise AdapterError('sam_parser_rejected') from None
    if result.outcome.status != 'completed' or result.diagnostics:
        raise AdapterError('sam_parser_incomplete_or_diagnostic')
    raw_boxes = re.findall(r'<\|box;([^|]+)\|>', result.raw_output)
    for box in raw_boxes:
        fields = dict(token.split('=', 1) for token in box.split(';'))
        if fields.get('w') != str(frame.width) or fields.get('h') != str(frame.height):
            raise AdapterError('sam_output_dimensions_mismatch')
    boxes, masks = {}, {}
    for record in result.records:
        if record.kind not in ('box', 'mask'):
            raise AdapterError('sam_unexpected_record')
        target = boxes if record.kind == 'box' else masks
        if record.object_id in target:
            raise AdapterError('sam_duplicate_object')
        target[record.object_id] = record
    if set(boxes) != set(masks) or len(masks) > 16:
        raise AdapterError('sam_object_pair_mismatch')
    normalized, budget = [], 0
    for ident, record in masks.items():
        role = roles.get(ident) if origin == 'manual_box_prompt' else roles['*']
        if role is None:
            raise AdapterError('sam_unbound_object')
        box, bounds = boxes[ident], record.bounds
        values = (box.left, box.top, box.right, box.bottom)
        if any(not isfinite(v) or not float(v).is_integer() for v in values):
            raise AdapterError('sam_noninteger_bounds')
        left, top, right, bottom = map(int, values)
        if not (0 <= left < right <= frame.width and 0 <= top < bottom <= frame.height):
            raise AdapterError('sam_bounds_outside_frame')
        if (bounds.left, bounds.top, bounds.right, bounds.bottom) != values:
            raise AdapterError('sam_mask_box_disagreement')
        w, h = record.mask.width, record.mask.height
        if record.mask.encoding != 'one_bit':
            raise AdapterError('sam_mask_encoding_mismatch')
        if (w, h) != (right-left, bottom-top):
            raise AdapterError('sam_resampling_not_supported')
        if w*h > MAX_MASK_RASTER_PIXELS:
            raise AdapterError('sam_mask_budget_exceeded')
        try:
            raster = decode_mask_to_raster(record.mask)
        except Exception:
            raise AdapterError('sam_mask_decode_failed') from None
        if len(raster) != w*h:
            raise AdapterError('sam_mask_size_mismatch')
        budget += sum(bool(value) for value in raster)
        if budget > MAX_MASK_CELLS:
            raise AdapterError('sam_mask_budget_exceeded')
        cells = frozenset((left+i%w, top+i//w) for i, value in enumerate(raster) if value)
        provenance = _provenance(frame, binding, times, now, mode, origin, role, ident, 'meta-sam-parser==0.1.0',
                                 (left, top, right, bottom))
        ambiguous = sum((roles.get(k) if origin == 'manual_box_prompt' else roles['*']) == role for k in masks) > 1
        normalized.append(Mask(frame.sha256, frame.width, frame.height, cells, role, True, ambiguous, provenance))
    provenance = _provenance(frame, binding, times, now, mode, origin, parser='meta-sam-parser==0.1.0')
    return Adapted(tuple(normalized), (), None, provenance,
                   ('Masks do not establish pen/holder presence or fitment.',))


def adapt_model(frame, binding, image, receipt_bytes, response_json, *, now, mode=Mode.LIVE, request_bytes=None):
    _validate(frame, binding, image, receipt_bytes, response_json, now, mode, request_bytes)
    if binding.prompt_kind != 'structured_json' or binding.object_roles:
        raise AdapterError('structured_request_contract_mismatch')
    response = _json(response_json)
    times = _response_times(response, binding, now)
    output = response.get('output')
    if not isinstance(output, list) or not output or len(output) > 8:
        raise AdapterError('structured_output_lane_mismatch')
    messages = []
    for item in output:
        if not isinstance(item, dict):
            raise AdapterError('structured_output_lane_mismatch')
        if item.get('type') == 'message':
            messages.append(item)
        elif item.get('type') == 'reasoning':
            # Responses may include opaque reasoning items. Never parse them as
            # observations or silently accept tools/extra assistant messages.
            allowed = {'type', 'id', 'summary', 'content', 'encrypted_content', 'status'}
            if (set(item) - allowed or not isinstance(item.get('id'), str)
                    or item.get('content', []) != [] or item.get('summary', []) != []
                    or item.get('encrypted_content') is not None and not isinstance(item['encrypted_content'], str)
                    or item.get('status', 'completed') != 'completed'):
                raise AdapterError('structured_reasoning_lane_mismatch')
        else:
            raise AdapterError('structured_output_lane_mismatch')
    if len(messages) != 1:
        raise AdapterError('structured_output_lane_mismatch')
    message = messages[0]
    content = message.get('content') if isinstance(message, dict) else None
    if (not isinstance(message, dict) or message.get('type') != 'message' or message.get('role') != 'assistant'
            or not isinstance(content, list) or len(content) != 1 or not isinstance(content[0], dict)
            or content[0].get('type') != 'output_text'):
        raise AdapterError('structured_output_lane_mismatch')
    data = _json(content[0].get('text'))
    if not isinstance(data, dict) or set(data) != {'schema_version', 'objects', 'fitment'} or data['schema_version'] != 'drawing-observations-v1':
        raise AdapterError('structured_schema_mismatch')
    objects = data['objects']
    if not isinstance(objects, list) or len(objects) > 2:
        raise AdapterError('structured_objects_invalid')
    observations, seen = [], set()
    for obj in objects:
        if not isinstance(obj, dict) or set(obj) != {'role', 'visibility', 'observed_present'}:
            raise AdapterError('structured_object_schema_mismatch')
        role, present = obj['role'], obj['observed_present']
        if role not in ('pen', 'holder') or role in seen or present is not None and type(present) is not bool:
            raise AdapterError('structured_object_value_mismatch')
        try:
            visible = Visibility(obj['visibility'])
        except (ValueError, TypeError):
            raise AdapterError('structured_visibility_invalid') from None
        seen.add(role)
        provenance = _provenance(frame, binding, times, now, mode, 'structured_model_observation', role, parser='drawing-observations-v1')
        observations.append(Observation(frame.sha256, frame.width, frame.height, role, visible, present, 'model_observation', provenance))
    fitment = None
    if data['fitment'] is not None:
        obj = data['fitment']
        if not isinstance(obj, dict) or set(obj) != {'visible', 'fitted'}:
            raise AdapterError('structured_fitment_schema_mismatch')
        if type(obj['visible']) is not bool or obj['fitted'] is not None and type(obj['fitted']) is not bool:
            raise AdapterError('structured_fitment_value_mismatch')
        if not obj['visible'] and obj['fitted'] is not None:
            raise AdapterError('structured_hidden_fitment_claim')
        provenance = _provenance(frame, binding, times, now, mode, 'structured_model_observation', 'fitment', parser='drawing-observations-v1')
        fitment = Fitment(frame.sha256, frame.tool, obj['fitted'], obj['visible'], provenance)
    provenance = _provenance(frame, binding, times, now, mode, 'structured_model_observation', parser='drawing-observations-v1')
    warnings = ('Contradictory presence/fitment claims must be resolved by six-check veto, not averaging.',) if fitment and fitment.fitted and any(o.visible is Visibility.OCCLUDED or o.observed_present is False for o in observations) else ()
    return Adapted((), tuple(observations), fitment, provenance, warnings)
