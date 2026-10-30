"""Gap reports: operator-pressed button on a NOT COVERED card.

One tap files the missing instruction into Sovereign Mind's Feedback
Flywheel, where a drafted candidate answer awaits Miguel's edit/approval.
This is a request, not a repair: it claims nothing about the model, the
verdict, or coverage. Separate route; the /assist default-deny contract
is untouched.

Secrets: runtime vault only (agent-fetch.sh), Modal Secret env fallback
in-container. Nothing is logged, persisted, or echoed.
"""
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path

SM_FEEDBACK_URL = 'https://sm.flotilla.cc/api/feedback'
SM_COLLECTION_ID = 'robot-ross-atf'
SM_ENV_VAR = 'SM_MOBILE_SESSION_TOKEN'
FULL_ID = re.compile(r'[0-9a-f]{16,128}')


class GapReportError(Exception):
    pass


def credential():
    """Bearer token, vault-first, env-fallback. Never logged or stored."""
    fetch = Path.home() / 'projects/agentic-fleet-hub/vault/agent-fetch.sh'
    try:
        result = subprocess.run([str(fetch), SM_ENV_VAR, 'dev'],
                                cwd=fetch.parent.parent, capture_output=True,
                                timeout=30)
    except Exception:
        result = None
    key = result.stdout.decode().strip() if result is not None and result.returncode == 0 else ''
    if not key or any(c.isspace() for c in key):
        env_key = os.environ.get(SM_ENV_VAR, '')
        if not env_key or any(c.isspace() for c in env_key):
            raise GapReportError('credential_unavailable')
        return env_key
    return key


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise GapReportError('sm_redirect_rejected')


def validated(question, answer, chunk_ids, distance, comment):
    """Fail-closed input shaping. Returns the SM payload or raises."""
    if not isinstance(question, str) or not 1 <= len(question.encode()) <= 2000:
        raise GapReportError('bad_question')
    if not isinstance(answer, str) or not answer.startswith('NOT COVERED'):
        raise GapReportError('not_a_coverage_refusal')
    if len(answer.encode()) > 2000:
        raise GapReportError('answer_too_long')
    if (not isinstance(chunk_ids, list) or not 1 <= len(chunk_ids) <= 8
            or any(not isinstance(c, str) or not FULL_ID.fullmatch(c)
                   for c in chunk_ids)):
        raise GapReportError('bad_chunk_ids')
    if not isinstance(distance, (int, float)) or not 0 <= distance < 10:
        raise GapReportError('bad_distance')
    if comment is None:
        comment = ''
    if not isinstance(comment, str) or len(comment.encode()) > 500:
        raise GapReportError('bad_comment')
    return {'collectionId': SM_COLLECTION_ID, 'question': question.strip(),
            'answer': answer, 'retrievedChunkIds': chunk_ids,
            'comment': comment.strip(), 'model': 'afl-live',
            'persona': 'field-engineer'}


def forward(payload, post=None, token=None):
    """POST the shaped payload to SM. Returns True on 201. Injected
    transport and token in tests; real urllib and vault otherwise.
    Raises GapReportError."""
    body = json.dumps(payload).encode()
    if token is None:
        token = credential()
    request = urllib.request.Request(
        SM_FEEDBACK_URL, data=body, method='POST',
        headers={'Authorization': 'Bearer ' + token,
                 'Content-Type': 'application/json'})
    sender = post or (lambda req: urllib.request.build_opener(NoRedirect()).open(req, timeout=120))
    try:
        with sender(request) as response:
            status = getattr(response, 'status', None)
            raw = response.read(65537)
    except GapReportError:
        raise
    except Exception as exc:
        raise GapReportError('sm_unreachable') from exc
    if status != 201 or len(raw) > 65536:
        raise GapReportError('sm_rejected')
    return True


def report_gap(question, answer, chunk_ids, distance, comment=None,
               post=None, token=None):
    """Route logic without HTTP: (ok, error). Error is a short code, never
    provider text, image data, or secret material."""
    try:
        payload = validated(question, answer, chunk_ids, distance, comment)
    except GapReportError as exc:
        return False, str(exc)
    try:
        forward(payload, post=post, token=token)
    except GapReportError as exc:
        return False, str(exc)
    return True, ''
