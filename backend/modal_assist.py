"""Modal-hosted /assist: stub by default, live amber-only composition on request.

- Default (AFL_LIVE_ASSIST unset): Phase 1 stub, default-deny, no providers.
- AFL_LIVE_ASSIST=1: serves LiveAssistService from live_backend.py — real
  retrieval, SAM, and Glimmer readout through the ambient-field-lens-live-
  providers app, still amber-only by contract (Literal['verify'], step None,
  score 0.0). Requires the afl-model-api Modal Secret (MODEL_API_KEY for the
  in-container SAM decode) and an open window in the afl-live Dict.

Demo transport only. Threshold unset; measured geometry unaccepted.
"""
import os

import modal

app = modal.App("afl-assist-stub")

LIVE = os.environ.get("AFL_LIVE_ASSIST") == "1"

image = (
    modal.Image.debian_slim()
    .pip_install("fastapi", "pydantic", "pillow", "modal==1.6.2", "meta-sam-parser")
    .env({"AFL_LIVE_ASSIST": "1"} if LIVE else {})
    .add_local_dir(".", "/root/backend")
)

secrets = [modal.Secret.from_name("afl-model-api")] if LIVE else []


# Single instance: the admission semaphore is process-local, so one container
# makes it mean what its docstring says. Spend itself is bounded by single-use
# tokens regardless of instance count; this closes the overlap window too.
@app.function(image=image, secrets=secrets, max_containers=1)
@modal.asgi_app()
def api():
    import sys

    sys.path.insert(0, "/root/backend")
    if os.environ.get("AFL_LIVE_ASSIST") == "1":
        import app as assist_app
        from live_backend import create_live_service

        return assist_app.create_app(service=create_live_service())
    import app as assist_app

    return assist_app.app
