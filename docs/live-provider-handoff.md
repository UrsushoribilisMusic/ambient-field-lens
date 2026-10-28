# Live demo provider handoff — Codi to Muse, 28 October 2026

Director's brief is the target. This branch supplies **runtime providers** for
Muse's `/assist` path. No new research, comparison, label collection or tuning.
It deliberately leaves server-owned green admission and iOS composition to Muse.

## Callable interfaces

From `backend/`, install `requirements-providers.txt`; run with the authenticated
Modal profile `miguel-40686`. The deployed app name is
`ambient-field-lens-live-providers`. No Glimmer API credential is sent to phones.
The Python SDK uses existing Modal authentication. An HTTP facade also exists at
`https://miguel-40686--ambient-field-lens-live-providers-grounding.us-east.modal.run`
and requires Modal proxy authentication before any function/container allocation.
Do not expose proxy credentials in iOS or application logs. HTTP and RPC route
through ONE serial CPU admission function before GPU invocation.

```python
from providers.client import open_window, retrieve, grounding, close_window
from providers.sam import segment_paper
from providers.clearance import containment_clearance, estimate_surface_mapping
```

1. `open_window(seconds=600, max_calls=4)` reserves$4 in the grant ledger, then
   authorizes that exact finite server window. It does not load a GPU. Defaults
   are at most10min /4 calls. Always `close_window(window['id'])` in cleanup.
2. `retrieve(question, frame_sha256)` queries existing Chroma collection
   `ross-manuals-2ca5f2f152267049` (38chunks, original fingerprint unchanged).
   Returns highest-ranked stored chunk text, actual chunk ID, original source
   hash/commit, distance, context hash and frame hash. No generated evidence or
   cached decision. The finite context is the first stored chunk, not a truncated
   dump of all search results. No new ingestion or corpus changes.
3. `segment_paper(jpeg_bytes, request_id=..., output_root=private_root, box=None)`
   sends THAT JPEG to Meta `sam-3.1` via documented Responses stream invocation.
   Runtime vault `MODEL_API_KEY`; original request/SSE/decoded PNG and receipts
   stay private. Returns `(object_id, readiness.checks.Mask)` candidates plus
   receipt. Multiple masks are ambiguous. Optional `box=(x1,y1,x2,y2)` is an
   explicit server-owned ROI on this frame, not automatic object recognition.
   The first real transport check uses a manually selected ROI; that assumption
   must stay visible. No segmentation on Baseten and no silent old-frame reuse.
4. `grounding(request_id=..., question=..., evidence=..., image_jpeg_base64=...,
   frame_sha256=..., window_id=...)` returns raw cosine score, layer27, frozen
   vector/model hashes, candidate_tokens_consumed0, native prefix hash, timing,
   GPU hardware, and retrieved chunk IDs. The image is actually consumed by the
   native multimodal processor/model. Score is NOT a probability or an approval.
   `threshold` is null until Muse's separately reviewed evidence contract owns
   one. Missing/mismatched evidence, expired windows, reused request IDs and
   excess calls reject. No generated candidate text enters the forward pass.
5. `containment_clearance(mask, vertices_mm, matrix, frame_sha256=...,
   registration_error_mm=..., reading_uncertainty_mm=..., robot_allowance_mm=...,
   geometry_reviewed=True)` returns component `state` and always all three
   requested fields: `clearance_mm`, `registration_error_mm`,
   `reading_uncertainty_mm` (null if unmeasured). Also returns robot allowance,
   raster sampling allowance and total required clearance. `step` is ALWAYS null.
   Muse's composition selects an approved procedure only when all gates pass.

`providers.client.collect` is a convenience call connecting one JPEG through
retrieval, SAM and Glimmer; it stops before Glimmer when no mask is available.
The individual functions allow Muse to schedule CPU/network work concurrently,
inspect candidate identities and compose the required six world checks.

## Frozen scoring, not another experiment

Existing true-prefill residuals are at the already measured layer27. The runtime
exports the identical normalized support-minus-control fit direction from the
existing12 fit records, checks all84 saved scores against their saved values,
and verifies native serving-prefix token identity on six old control cases.
No new fit labels, layer search, trajectory, or evaluation scores. Original
comparison artifacts remain unchanged. Raw scores measure supplied-context
support, not generated-answer correctness, calibrated hallucination probability,
or visual readiness. Do not label0.889/0.861 as true-prefill results; see the
original reports for the distinct measured endpoints.

The serving template uses the frozen continue-final-message form, with a
sentinel solely to find the pre-candidate boundary, removed BEFORE forwarding.
`add_generation_prompt` was tested on CPU and rejected because its prefix differs.
Never silently substitute it. Frozen vector SHA256:
`dd1149b0067c6189417871f87c8ee461efd088e433b37a9bf10dcce991373bb7`.
Model revision `cec94fcfd6512f2cfe708138c32533b346ea4f69`, verified BF16 snapshot
59,553,435,272bytes; no new local model download or quantization.

## Clearance acceptance

`estimate_surface_mapping(fit, validation)` consumes measured correspondences,
fits the planar mapping and reports independent residual in mm using its inverse.
It does not reject an estimate solely because residual exceeds2px. Nor does it
approve geometry: `geometry_reviewed=False` until the server-owned contract binds
camera/rig/pose, source measurements, support region and robot-to-plane linkage.
The original historical2px result remains unchanged as a historical result.

Clearance uses ALL footprint cells against the actual mask, including internal
holes. Signed distances are mapped through the full homography; no global guessed
pixel/mm scale. Pass requires nominal containment AND clearance strictly greater
than registration error + reading uncertainty + robot allowance + raster allowance.
These inputs must be measured/reviewed, not estimated by an LLM or invented from
the old approximately45x40mm drawing. A margin near uncertainty remains unknown.
Outside-paper returns `fail`, reason `drawing_footprint_outside_paper_boundary`,
with no step. The combined application must preserve this veto regardless of the
Glimmer score. Synthetic control tests establish code behavior, not current rig
acceptance. Real measured geometry and phone two-state validation remain required.

## Windows, costs, failures

All local provider attempts/outcomes append to
`~/.local/state/ambient-field-lens/api-calls.jsonl`; exact requests/responses under
`~/Movies/Ambient-Field-Lens/live-provider-receipts/`. Modal requests also retain
window-bound private receipts on `afl-recal-artifacts`. SAM masks/usage retain the
original frame hash. Unknown modality/token costs stay null, never free. Modal
reservations remain in the separate `budget.json` grant ledger.

GPU preference A100-80GB then H100, same model/dtype/readout, hardware reported.
The fallback resource upper bound includingCPU4/RAM64GiB remains below$4 for3002s
at published rates checked28Oct. Live windows are shorter (600s), maximum4 calls,
max1 GPU container, min0/buffer0,2s scale-down. CPU admission has a240s inclusive
wait on the GPU call and explicitly cancels failed/queued work; GPU entry checks
window expiry BEFORE loading weights. No retries or unattended keepalive. Stop
and verify containers after each filmed/test window; deployment alone uses no GPU.
An A100-only attempt queued with0 workers and was stopped before GPU allocation;
its reservation and failed receipt remain in the ledger.

## Muse's integration acceptance

- Server-owned frame/camera/capture-clock and motion freshness, measured geometry,
  pen/holder presence + fitment, controller calibration/session, and approved
  procedure selection remain required. These providers cannot manufacture them.
- `/assist` currently has a2.5s timeout; real cold starts/SAM exceed it. Set an
  explicit reviewed execution timeout for the narrow demo and display progress;
  never silently refresh capture timestamps to make old results appear fresh.
- Green must consume THIS frame's mask and THIS request's Glimmer response plus
  real retrieval. Displaced paper must name the containment fault and carry no
  step. Missing data, exceptions, timeouts or physical vetoes stay amber.
- Record both real phone responses with frame hash, mask digest, source chunk IDs,
  raw grounding score + reviewed threshold, all mm terms and final verdict.
- No recorded phone green/amber acceptance yet. Do not call the end-to-end demo
  complete based on component tests or a single provider response.

## Verified runtime result tonight

[Machine-readable receipts summary](verification/live-provider-integration-2026-10-28.json).
New Reolink frame SHA2672d519…: one Meta SAM paper mask decoded, overlay visually
checked; existing Ross collection returned actual source chunk IDs. H100 served
one frozen layer27 true-prefill score -0.024460947181109742,861prefix tokens,
zero candidate tokens, one forward. Forward timing3.033s; actual client roundtrip
including cold start62.216s. This is NOT a3s end-to-end phone demonstration.
The2s idle scale-down means a later request may cold-start again; plan the filmed
window/latency explicitly, not with unledgered keepalives or edited timing claims.

Both reservations retained: first A100 queue stopped with0GPU workers; second
H100 call completed and window closed. Total conservative grant reservations$30
(including prior$22), not invoiced usage. Final Modal container inventory`[]`.
No threshold selected, no current physical geometry accepted, no fresh readiness
claim, no phone green/amber acceptance. Private overlay for Clau:
`~/Movies/Ambient-Field-Lens/2026-10-28/live-provider-demo/paper-mask-overlay-01.jpg`.
For the final film, publish the approved demo frame/mask/receipt bundle together
so judges can check hashes; this development summary contains no raw room images.
