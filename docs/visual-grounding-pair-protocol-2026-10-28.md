# Archived visual grounding — review before scoring

User's next-round instruction: four visual checks, no new filming; every pair
must be reviewed by Miguel before any scoring. Text-only/manual answerability
is excluded, not a successful substitute. No GPU window is authorized here.

The packet has four fixed questions/candidates, one pair per check: eight
conditions from six unique native crops (the two geometry checks reuse the
same images within the fit fold). The two
members receive identical text and task parameters; only visual conditions
differ. A supported candidate in one scene and a contradicted candidate in the
other replaces the earlier textual-support/unrelated-passage intervention.
Manual context is empty. Filenames, operator labels, controller flags and scene
conditions stay in provenance, never model prompts. Proposed labels are by
Codi; `human_label` and `human_reviewer` remain null, scoring/GPU flags false.

## Pair definitions and predeclared families/folds

| Pair | Image-dependent check | Archive | Fold |
|---|---|---|---|
| VG01 | Paper under the fixed pen tip versus tip over bare desk | S28 before/after paper displacement | fit |
| VG02 | Supplied cyan footprint entirely inside white paper | Same S28 family, fixed image-space polygon | fit |
| VG03 | Visible pen-tip/paper contact versus visible gap | S06 calibration at30s/60s | validation |
| VG04 | Visible lower/right outline edges present versus missing | S19 failed result / S22 later result | test |

Same capture family and duplicate image remain within one fold. There are
only four pairs and ONE test pair: this is an authoring/review seed, not an
accuracy/calibration benchmark. Same rig and physical marks recur across
captures; scene independence, viewpoint robustness and broader task coverage
are not established. More images are not created or requested in this round.

VG02 needs an explicit target because raw photos do not display an intended
future robot footprint. Its cyan quadrilateral is a separately supplied SVG
reference traced around the visible outline in the before frame, held fixed
in both image-coordinate systems. Original crop pixels are unmodified; the
review page layers the supplied vector on top. This is a visual image-space
containment question, NOT accepted robot registration or a physical path.
Miguel must explicitly accept this scope or reject/replace the pair. No nominal
robot coordinates or successful calibration are invented.

VG03 tests visible contact only; presence alone is insufficient. If native
pixels cannot resolve the tip/surface relationship, UNKNOWN/rejection blocks
that pair. Do not infer contact from calibration flags or action names.

VG04 asks about missing intended outline strokes, not whether the interior of
a line drawing is filled. Its existing handwriting is not a new requested
stroke. Pen pose also differs across captures; retain that nuisance correlation
in any later report, rather than claiming a causal contact test.

## Required human review and freeze

Private review page:
`~/Movies/Ambient-Field-Lens/2026-10-28/visual-grounding-review/review.html`.
It shows native crops, original-source links, the identical question/candidate,
proposed scope and optional hidden author suggestions. Every member starts
unreviewed. The reviewer supplies his own name, labels, corrections, sufficient-
evidence judgment and an image-required/manual-only-answerability judgment.
The provided footprint target also needs explicit scope approval.

Unknown, rejected, insufficient, partial or manual-answerable pairs BLOCK the
whole seed. Text-answerable questions must be discarded/replaced, never kept
and scored as visual successes. Illustrative excluded questions are recorded
in the manifest (e.g. “Should the pen touch paper?”); they are not test items.

The download is a local, digest-bound review JSON. No image upload, provider
request, inferred human signature, automatic GPU launch or product verdict.
`backend/recal/visual_review.py` validates the complete independent review;
even a valid artifact only authorizes separate offline planning, not green.
No genuine approved review artifact has been created by the agent.

[Manifest](verification/visual-pair-manifest-2026-10-28.json) records source and
crop hashes, native dimensions, frame times, target coordinates and grouped
folds. Raw frames/crops stay outside Git. Do not reauthor a hash-bound set after
human review without an explicit replacement/freeze. /assist remains default-
deny, fixture unchanged, archived images never relabeled as fresh live evidence.
