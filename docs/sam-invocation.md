# SAM 3.1 mask contract — official documentation checked 2026-10-26

No paid call was used to investigate the earlier empty text response.

The documented POST is `https://api.meta.ai/v1/responses`: one user message,
`model: sam-3.1`, a short object noun phrase in `input_text`, and the still in
`input_image.image_url` (public URL or data URL). Set `stream: true` and
`metadata: {"mask_encoding": "one_bit"}`. Consume output-text deltas through
`response.completed`; use the published `meta_sam_parser` Python dependency to
decode masks. Do not invent output-format or tool parameters.

Masks are carried in the output-text lane using SAM's grammar, not a separate
binary lane. Empty output is a documented zero-match outcome. Questions and
commands are poor segmentation prompts; use one concrete concept, such as
`pen holder`. Retain the unmodified event envelope for one authorized diagnostic
call before concluding that the client dropped a populated output.

Primary references:

- [Overview](https://dev.meta.ai/docs/sam/overview)
- [Request shape and prompt guidance](https://dev.meta.ai/docs/sam/segmenting)
- [Output and zero-match semantics](https://dev.meta.ai/docs/sam/reading-segmentation)
- [Published parser](https://dev.meta.ai/docs/sam/client-libraries)

Spark is a separate text/reasoning model. Preserve output-token headroom for
its reasoning and response; do not carry a tiny SAM/text smoke-test limit into
Spark requests. The project currently reports Spark working with approximately
eight reasoning tokens before visible text; that is an observation, not a fixed
token guarantee.
