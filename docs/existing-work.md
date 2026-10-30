# Existing work (disclosure boundary)

This repo was created empty on Oct 26, 2026. Everything in it was written
here, against public SDK docs and declared dependencies — nothing was
copied from earlier private prototypes.

Declared influences (dependency or reference only, never vendored):

- `jlens.py` (Canis project): the Jacobian-lens idea was reimplemented from
  the method description for the paired comparison, then retired when it
  showed no advantage. No code shared.
- Sovereign Mind chunkers: referenced as prior art for corpus chunking;
  the Ross corpus pipeline here (`backend/recal/corpus_cpu.py`) is original.
- Meta DAT iOS samples (`DisplayAccess`, `CameraAccess`): consulted as
  API documentation for session/camera/display setup; app code retyped.
- Meta SAM / Spark / Glimmer docs and MCP references: used as live
  documentation during development.

What this means for judges: any resemblance to the authors' earlier
private work is convergent (same problem, same public APIs), not copied.
Where an approach was tried and retired (contrastive probe, Jacobian lens,
trajectory scoring), the protocols and negative results are in-repo under
`docs/` and `docs/verification/`.

## Platform boundary (Rule 4)

Code provenance above is about *source*. Rule 4 also asks what pre-existed as
a platform. Stated plainly:

**Pre-existing, not built here:**

- Robot Ross — the Huenit arm, its controller and the physical rig. It is the
  machine under test, not a deliverable of this hackathon.
- The ATF wiki corpus (Robot Ross manuals), used as the operator's documents.
- Sovereign Mind — the wiki and review console the repair loop writes into.
  Its Feedback Flywheel UI pre-existed; the integration that files a gap
  report from a refusal, and the corpus re-versioning that follows approval,
  were built here.

**Built here:** everything listed under "Built during the hackathon" in the
README — the iOS app, the `/assist` contract, SAM gating, the Glimmer probes
and their negative results, the coverage gate and its calibration, corpus
versioning with a reviewed pin registry, and the repair loop end to end.
