# Ambient Field Lens

Safety-gated wearable assistant for the Meta Global AI Developer Hackathon,
Startup track. Built Oct 26 – Nov 4, 2026.

**One-liner:** an operator looks at a machine through the phone (standing in
for glasses) and asks setup questions. The system answers amber cards with
evidence-backed refusals and corrections. It has never emitted a green step:
the backend is type-level incapable of one until a reviewed evidence contract
says what green requires.

## What it does today

- Frame a rig, tap **Ask**: the phone captures, the cloud runs retrieval over
  the Robot Ross manuals, segments paper candidates with SAM, and reads a
  frozen Glimmer grounding score — then refuses in amber with the evidence
  attached (mask count, manual chunk, uncalibrated score, everything else
  declared unverified).
- Displace the paper and Ask again: the refusal names the fault
  (`WORLD CHECK FAILED`) instead.
- Ask about something the manuals don't cover: `NOT COVERED` once the Q1
  coverage threshold is frozen (until then, covered-but-uncalibrated).
- Header chips (WORLD / COV) show only earned failures in color; everything
  unestablished renders gray. No chip can pass anything.

## What it does not do

- No green steps, no red blocks, no instructions to touch the machine.
- No weight readout in the verdict: four independent probes (contrastive,
  Jacobian lens, trajectory, live prefill) found no signal separating
  grounded from confabulated answers on our tasks. Groundedness here is a
  system property — retrieved passage, hash-bound evidence, fail-closed on
  anything missing — not a model readout.
- No capture-time proof: a receipt binds which frame, question, passage, and
  masks went into an answer — never when the photo was taken.

## Run the demo

Requires an open window (finite: 600 s, 4 single-use token calls):

```bash
cd backend
.venv/bin/python -c "
import modal
from providers import client
from live_backend import arm_tokens
r = client.open_window(seconds=600, max_calls=4)
d = modal.Dict.from_name('afl-live', create_if_missing=True)
rec = {'id': r['id'], 'expires_at': r['expires_at'], 'max_calls': 4, 'calls_used': 0}
d.put('active', rec); arm_tokens(rec)"
```

Then Ask from the phone (base URL in Setup; backend default-deny otherwise).
Windows cost nothing to open; each framed call burns one token, ~15–90 s of
Modal GPU/CPU plus one Meta SAM decode. Close with `client.close_window(id)`.

## Layout

- [ARCHITECTURE.md](ARCHITECTURE.md) — system as built, gates, contracts.
- [docs/submission.md](docs/submission.md) — hackathon narrative and limits.
- [docs/live-assist-wiring.md](docs/live-assist-wiring.md) — live path ops log.
- [docs/observable-checks-handoff.md](docs/observable-checks-handoff.md) — providers.
- [docs/proposals/red-controller-contract.md](docs/proposals/red-controller-contract.md) — red proposal (not implemented).

## Disclosure

Clean-room repo created Oct 26, 2026. Nothing copied from earlier private
prototypes; prior art is referenced as declared dependencies or in
[docs/existing-work.md](docs/existing-work.md) where present. Calibration
labels were reviewed by a human; scoring ran only on frozen labels.
