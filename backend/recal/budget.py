"""Conservative, nonrefundable reservations for finite GPU windows on this Mac."""
import datetime
import fcntl
import json
from pathlib import Path
import uuid

CEILING_USD = 100.0
CPU_AND_BUILD_RESERVE_USD = 2.0
WINDOW_RESERVE_USD = 4.0
# 45m function + 5m startup + 2s scale-down, with resource *limits* below.
MAX_WINDOW_SECONDS = 3002
MAX_WINDOW_RATE = 0.000694 + 4 * 0.0000131 + 64 * 0.00000222


def reserve_window(path):
    if MAX_WINDOW_SECONDS * MAX_WINDOW_RATE >= WINDOW_RESERVE_USD:
        raise ValueError('Resource envelope no longer fits the reservation')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix('.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ledger = json.loads(path.read_text()) if path.exists() else {
            'ceiling_usd': CEILING_USD, 'cpu_and_build_reserve_usd': CPU_AND_BUILD_RESERVE_USD, 'windows': []}
        if ledger.get('ceiling_usd') == 20.0:
            ledger['previous_ceiling_usd'] = 20.0
            ledger['ceiling_usd'] = CEILING_USD
            ledger['authorization'] = {'workspace': 'miguel-40686', 'grant_usd': 100,
                'confirmed_by': 'Miguel, 2026-10-28 screenshot and instruction', 'expires': '2027-10-31'}
        extra = ledger.get('authorized_extra_usd', 0.0)
        if (ledger.get('ceiling_usd') != CEILING_USD or
            ledger.get('cpu_and_build_reserve_usd') != CPU_AND_BUILD_RESERVE_USD or
            not isinstance(extra, (int, float)) or extra < 0 or extra % WINDOW_RESERVE_USD != 0 or
            any(w.get('reserved_usd') != WINDOW_RESERVE_USD for w in ledger['windows'])):
            raise ValueError('Budget ledger does not match the fixed resource envelope')
        reserved = CPU_AND_BUILD_RESERVE_USD + sum(w['reserved_usd'] for w in ledger['windows'])
        if reserved + WINDOW_RESERVE_USD > CEILING_USD + extra:
            raise ValueError('Hard local budget reservation ceiling reached; no GPU launched')
        item = {'id': str(uuid.uuid4()), 'reserved_usd': WINDOW_RESERVE_USD,
                'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
        ledger['windows'].append(item)
        staged = path.with_suffix('.tmp')
        staged.write_text(json.dumps(ledger, indent=2))
        staged.chmod(0o600)
        staged.replace(path)
        return item


def authorize_extra_usd(path, amount_usd, authorization):
    """Record a human-authorized extension of the reservation ceiling.

    The ceiling itself never moves: the exception and its evidence
    (who, metered spend, purpose) are ledger data, reviewed like any
    other entry. Amount must be a positive multiple of WINDOW_RESERVE_USD.
    """
    if (not isinstance(amount_usd, (int, float)) or amount_usd <= 0
            or amount_usd % WINDOW_RESERVE_USD != 0):
        raise ValueError('exception_must_be_window_sized')
    if not isinstance(authorization, dict) or not authorization.get('by'):
        raise ValueError('exception_needs_named_authorization')
    path = Path(path)
    with path.with_suffix('.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ledger = json.loads(path.read_text())
        ledger['authorized_extra_usd'] = float(
            ledger.get('authorized_extra_usd', 0.0)) + float(amount_usd)
        ledger.setdefault('authorizations', []).append(dict(
            authorization, amount_usd=float(amount_usd),
            recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
        staged = path.with_suffix('.tmp')
        staged.write_text(json.dumps(ledger, indent=2))
        staged.chmod(0o600)
        staged.replace(path)
    return ledger['authorized_extra_usd']


def record_result(path, reservation_id, **result):
    """Preserve the nonrefundable charge bound, including failed attempts."""
    path=Path(path)
    if {'id','reserved_usd'} & result.keys():raise ValueError('Reservation is immutable')
    with path.with_suffix('.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        ledger=json.loads(path.read_text())
        item=next(w for w in ledger['windows'] if w['id']==reservation_id)
        item.update(result);item['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        staged=path.with_suffix('.tmp');staged.write_text(json.dumps(ledger,indent=2));staged.chmod(0o600);staged.replace(path)
