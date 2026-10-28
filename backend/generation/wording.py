"""Finite, receipted text authoring. No scoring, images, retries, or GPU imports."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request

ROUTES = {
    'baseten': ('https://inference.baseten.co/v1/chat/completions',
                'meta-models/muse-spark-open-1026', 'BASETEN_API_KEY'),
    'meta': ('https://api.meta.ai/v1/chat/completions',
             'muse-spark-1.3', 'MODEL_API_KEY'),
}
PURPOSES = {'pair_phrasings', 'step_text', 'review_copy'}
RATES = {'baseten': (1.25, 4.25), 'meta': (1.25, 4.25)}
PRICING = {'baseten': 'https://www.baseten.co/library/muse-spark-open/',
           'meta': 'https://dev.meta.ai/docs/pricing-rate-limits'}
SYSTEM = ('Draft wording for human review only. Do not assign or change evaluation '
          'labels, claim checks passed, authorize equipment actions, or invent evidence. '
          'Preserve supplied technical facts and uncertainty. Return the requested text.')
DEFAULT_LEDGER = Path.home() / '.local/state/ambient-field-lens/api-calls.jsonl'
DEFAULT_OUTPUT = Path.home() / 'Movies/Ambient-Field-Lens/generation'


def utc():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def private_write(path, data):
    with Path(path).open('xb') as stream:
        os.chmod(path, 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def append_event(ledger, event, *, unique_attempt=False):
    """Lock and fsync each reservation/outcome; never rewrite historical events."""
    ledger = Path(ledger)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open('a+', encoding='utf-8') as stream:
        os.chmod(ledger, 0o600)
        fcntl.flock(stream, fcntl.LOCK_EX)
        stream.seek(0)
        rows = [json.loads(line) for line in stream if line.strip()]
        if unique_attempt and any(r['job_id'] == event['job_id'] for r in rows):
            raise ValueError('job_already_recorded_no_retry')
        stream.seek(0, 2)
        stream.write(canonical(event).decode() + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def plan(job_id, purpose, text, provider='baseten', max_tokens=2048):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', job_id):
        raise ValueError('invalid_job_id')
    if purpose not in PURPOSES or provider not in ROUTES:
        raise ValueError('wording_route_only_no_sam_or_readouts')
    if not isinstance(text, str) or not text.strip() or len(text.encode()) > 12000:
        raise ValueError('text_required_max_12000_utf8_bytes')
    if type(max_tokens) is not int or not 64 <= max_tokens <= 4096:
        raise ValueError('max_tokens_must_be_64_to_4096')
    endpoint, model, _ = ROUTES[provider]
    body = {'model': model, 'messages': [{'role': 'system', 'content': SYSTEM},
                                       {'role': 'user', 'content': text}],
            'stream': False, 'max_tokens': max_tokens}
    return {'job_id': job_id, 'purpose': purpose, 'provider': provider,
            'endpoint': endpoint, 'model': model, 'request': body,
            'request_sha256': digest(canonical(body)), 'automatic_retries': 0,
            'pricing_source': PRICING[provider], 'pricing_checked': '2026-10-28',
            'input_usd_per_million': RATES[provider][0],
            'output_usd_per_million': RATES[provider][1],
            'cost_basis': 'uncached estimate from provider usage, not invoice',
            'gpu_used': False, 'human_review_required': True}


def credential(provider):
    # Runtime vault only. No credential cached in source, disk receipts, or stdout.
    fetch = Path.home() / 'projects/agentic-fleet-hub/vault/agent-fetch.sh'
    try:
        result = subprocess.run([str(fetch), ROUTES[provider][2], 'dev'],
                                cwd=fetch.parent.parent, capture_output=True, timeout=30)
    except Exception:
        raise RuntimeError('credential_unavailable') from None
    key = result.stdout.decode().strip() if result.returncode == 0 else ''
    if not key or any(c.isspace() for c in key):
        raise RuntimeError('credential_unavailable')
    return key


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError('provider_redirect_rejected')


def transport(endpoint, body, key):
    request = urllib.request.Request(endpoint, data=body, method='POST', headers={
        'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=120) as response:
        raw = response.read(4_194_305)
        if len(raw) > 4_194_304:
            raise RuntimeError('provider_response_too_large')
        return response.status, raw


def usage_cost(response, provider):
    usage = response.get('usage')
    if not isinstance(usage, dict):
        return None, None
    keys = ('prompt_tokens', 'completion_tokens', 'total_tokens')
    if any(type(usage.get(k)) is not int or usage[k] < 0 for k in keys):
        return None, None
    if usage['total_tokens'] != usage['prompt_tokens'] + usage['completion_tokens']:
        return None, None
    counts = {k: usage[k] for k in keys}
    input_rate, output_rate = RATES[provider]
    cost = (counts['prompt_tokens'] * input_rate + counts['completion_tokens'] * output_rate) / 1e6
    return counts, cost


def execute(job_id, purpose, text, *, provider='baseten', max_tokens=2048,
            output_root=DEFAULT_OUTPUT, ledger=DEFAULT_LEDGER,
            send=transport, fetch=credential):
    job = plan(job_id, purpose, text, provider, max_tokens)
    key = fetch(provider)
    body = canonical(job['request'])
    if not key or key.encode() in body:
        raise ValueError('credential_in_request_or_unavailable')
    folder = Path(output_root) / job_id
    folder.mkdir(parents=True, exist_ok=False, mode=0o700)
    private_write(folder / 'request.json', body)
    receipt = {k: v for k, v in job.items() if k != 'request'}
    receipt.update(event='attempt', attempted_at=utc(), status='attempt_reserved',
                   usage=None, estimated_api_cost_usd_uncached=None)
    # Durable receipt and shared ledger entry precede any paid network operation.
    private_write(folder / 'attempt.json', canonical(receipt))
    append_event(ledger, receipt, unique_attempt=True)
    result = {**receipt, 'event': 'outcome', 'status': 'failed_no_retry',
              'response_sha256': None, 'http_status': None, 'finish_reason': None}
    generated = None
    try:
        status, raw = send(job['endpoint'], body, key)
        result['http_status'] = status
        if key.encode() in raw:
            raise RuntimeError('credential_echo_rejected')
        private_write(folder / 'response.json', raw)
        result['response_sha256'] = digest(raw)
        response = json.loads(raw)
        if not isinstance(response, dict):
            raise ValueError('invalid_response')
        result['usage'], result['estimated_api_cost_usd_uncached'] = usage_cost(response, provider)
        if status != 200:
            result['status'] = 'http_error_no_retry'
        elif response.get('model') != job['model']:
            result['status'] = 'response_model_mismatch'
        else:
            choices = response.get('choices')
            if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
                raise ValueError('invalid_choices')
            choice = choices[0]
            finish = choice.get('finish_reason')
            result['finish_reason'] = finish if finish in {'stop', 'length', 'tool_calls', 'content_filter'} else 'unknown'
            message = choice.get('message', {})
            content = message.get('content') if isinstance(message, dict) else None
            if finish != 'stop':
                result['status'] = 'incomplete_no_retry'
            elif not isinstance(content, str) or not content.strip():
                result['status'] = 'empty_text_no_retry'
            elif result['usage'] is None:
                result['status'] = 'usage_unknown_no_retry'
            else:
                generated = content
                result['status'] = 'draft_generated_pending_human_review'
    except urllib.error.HTTPError as exc:
        result.update(http_status=exc.code, status='http_error_no_retry')
    except Exception:
        # Never stringify arbitrary exceptions, provider text, headers, or credentials.
        result['status'] = 'failed_no_retry'
    result['completed_at'] = utc()
    private_write(folder / 'outcome.json', canonical(result))
    append_event(ledger, result)
    if generated is not None:
        private_write(folder / 'draft.txt', generated.encode())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job-id', required=True)
    parser.add_argument('--purpose', choices=sorted(PURPOSES), required=True)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--provider', choices=sorted(ROUTES), default='baseten')
    parser.add_argument('--max-tokens', type=int, default=2048)
    parser.add_argument('--output-root', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--ledger', type=Path, default=DEFAULT_LEDGER)
    parser.add_argument('--execute', action='store_true', help='One paid attempt; otherwise preview only')
    args = parser.parse_args()
    text = args.input.read_text()
    try:
        if args.execute:
            result = execute(args.job_id, args.purpose, text, provider=args.provider,
                             max_tokens=args.max_tokens, output_root=args.output_root, ledger=args.ledger)
            print(json.dumps({k: result[k] for k in ('job_id', 'provider', 'model', 'status',
                             'usage', 'estimated_api_cost_usd_uncached')}))
            return 0 if result['status'] == 'draft_generated_pending_human_review' else 1
        prepared = plan(args.job_id, args.purpose, text, args.provider, args.max_tokens)
        print(json.dumps({k: v for k, v in prepared.items() if k != 'request'}, indent=2))
        return 0
    except Exception:
        print('Generation did not execute or finalize; inspect private receipts. No automatic retry.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
