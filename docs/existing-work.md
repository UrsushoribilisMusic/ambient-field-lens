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
