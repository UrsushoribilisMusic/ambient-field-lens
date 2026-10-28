"""Modal-hosted /assist stub — mirrors backend/app.py default-deny behavior.

Demo transport only: puts the Phase 1 stub on a public HTTPS endpoint so
the phone app needs no LAN path. No model, no corpus, no probes here.
"""

import modal

app = modal.App("afl-assist-stub")

image = (
    modal.Image.debian_slim()
    .pip_install("fastapi", "pydantic", "pillow")
    .add_local_dir(".", "/root/backend")
)


@app.function(image=image)
@modal.asgi_app()
def api():
    import sys

    sys.path.insert(0, "/root/backend")
    import app as assist_app

    return assist_app.app
