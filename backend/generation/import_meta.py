"""Import existing private Meta attempt receipts; never send a provider request."""
import argparse
import json
from pathlib import Path
from generation.wording import DEFAULT_LEDGER, append_event, canonical, digest, utc, usage_cost


def import_receipt(path, ledger=DEFAULT_LEDGER):
    path = Path(path)
    receipt_bytes = path.read_bytes()
    receipt = json.loads(receipt_bytes)
    model = receipt.get('model')
    if model not in {'muse-spark-1.3', 'sam-3.1'}:
        raise ValueError('not_a_known_meta_receipt')
    response_path = path.parent / 'response.json'
    events_path = path.parent / 'events.json'
    response, raw = {}, None
    if response_path.exists():
        raw = response_path.read_bytes()
        response = json.loads(raw)
    elif events_path.exists():
        raw = events_path.read_bytes()
        events = json.loads(raw)
        for event in events:
            if event.get('type') == 'response.completed':
                response = event.get('response', {})
    original_usage = response.get('usage')
    counts, cost = None, None
    if isinstance(original_usage, dict):
        # Meta Responses counts include reasoning in output_tokens already.
        translated = {'prompt_tokens': original_usage.get('input_tokens'),
                      'completion_tokens': original_usage.get('output_tokens'),
                      'total_tokens': original_usage.get('total_tokens')}
        counts, estimate = usage_cost({'usage': translated}, 'meta')
        if model == 'muse-spark-1.3':
            cost = estimate
        # SAM modality pricing is not assumed to equal Spark pricing.
    identity = digest(canonical({'path': str(path.resolve()), 'receipt_sha256': digest(receipt_bytes)}))
    row = {'job_id': 'meta-archive-' + identity[:24], 'event': 'historical_import',
           'provider': 'meta', 'model': model, 'purpose': 'archived_observation',
           'imported_at': utc(), 'attempted_at': receipt.get('attempted_at'),
           'receipt_sha256': digest(receipt_bytes), 'source_receipt': str(path.resolve()),
           'response_sha256': digest(raw) if raw else None, 'usage': counts,
           'estimated_api_cost_usd_uncached': cost,
           'cost_basis': 'Spark uncached usage estimate; SAM cost unknown',
           'status': 'historical_attempt_not_rerun', 'new_paid_call': False}
    try:
        append_event(ledger, row, unique_attempt=True)
    except ValueError as exc:
        if str(exc) != 'job_already_recorded_no_retry':
            raise
        return False
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-root', type=Path, required=True)
    parser.add_argument('--ledger', type=Path, default=DEFAULT_LEDGER)
    args = parser.parse_args()
    imported = sum(import_receipt(p, args.ledger) for p in sorted(args.archive_root.rglob('attempt.json')))
    print(json.dumps({'imported_attempts': imported, 'new_paid_calls': 0}))
