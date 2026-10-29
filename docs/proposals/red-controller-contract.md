# Proposed RED controller-state extension — review only

Status: **proposal, not implemented or approved**. Existing wire contract remains
amber `verdict: verify`, `step: null`. No enum, iOS color, admission rule, controller
command, lock deletion or calibration reset is changed by this document.

## Meaning and precedence

- Amber/`verify`: evidence missing, unclear, stale, unbound, or an observable setup
  fault such as an absent pen. No step is authorized.
- Proposed red/`blocked`, severity`critical`: a positively established controller
  invariant failure prevents proceeding, independently of visual/model evidence.
  "Critical" is workflow-blocking, not a claim that immediate physical danger
  was measured. No step is authorized. Red cannot be overridden by a good mask,
  retrieval passage, pen observation or any internal-model score.
- Green remains disabled under today's product policy. This proposal introduces
  no path to green, no calibrated weight-based gate and no threshold tuning.

## Evidence eligible for review as a RED reason

1. Controller-confirmed failed/aborted execution leaves a lock preventing new
   work, corroborated by current status plus stable lock/process/log evidence in
   the bound controller session. An old log line or a lock file alone is not enough.
2. A known robot worker is actually a zombie (`ps` stateZ), correlated with the
   active job/session and a controller-reported job state that cannot reconcile.
   A missing worker or an empty process scan does NOT prove a zombie.
3. A controller-attested invalidated calibration/tool/surface binding while the
   operation requires that binding. Mere existence of calibration.json or the
   ready flag is neither an attestation nor evidence of current physical contact.

`possible_stale_job_lock_requires_operator_review` currently remains an AMBER
candidate diagnosis. No automated "stale" conclusion from age, guessed PID,
no-job status alone, or a log that could be from another session. The process
start identity, calibration/ready hashes, tool, surface and controller instance
must agree. Process/HTTP/file reads are not atomic; disagreement stays unresolved.

## Proposed versioned response (shape only)

```json
{
  "verdict": "blocked",
  "severity": "critical",
  "block_code": "controller_state_inconsistent",
  "step": null,
  "score": 0.0,
  "detail": "Controller state is inconsistent; no instruction authorized.",
  "controller_receipt": {
    "snapshot_sha256": "<actual evidence hash>",
    "controller_session": "<reviewed binding id>",
    "observed_at": "<actual observation time>",
    "calibration_sha256": "<actual calibration hash>"
  }
}
```

Reasons and details come from a finite reviewed vocabulary. Any technical
correction/recovery instruction must be an exact retrieved passage with chunk
ID/source hash; model-generated repair text is prohibited. Geometry corrections
remain numeric measured proposals and cannot clear a controller block.

## Clear/acknowledgment behavior

No automatic unlock, PID killing, job cancellation, reset, firmware action or
movement. An operator investigates using the approved procedure. Acknowledging
the card alone does not clear it: take new status/process/file snapshots, bind
the current tool/surface/session, and recompute. Preserve original receipts.

## Required reviews before implementation

- Muse reviews the wire version and server-owned RED reason policy.
- Miguel confirms which controller failures merit red vs amber in the demo.
- Independent implementation review covers spoofed/stale status, PID reuse,
  unrelated logs, duplicate/replayed receipts, ambiguous locks, actual zombie
  process evidence, response validation and iOS handling of unknown verdicts.
- Test amber and proposed red cases always suppress steps; no model or client
  can supply a verdict, clear a block or invent a recovery instruction.

Current read-only provider: `providers.robot_state.capture` and `.assess` return
amber only. A pass means coherent controller metadata under a reviewed binding,
never physical calibration success or an authorization to move.
