"""Ambient Field Lens backend — Phase 1 /assist stub.

Default-deny: until the Glimmer recalibration + calibrated threshold land
(Phase 3), every response is a `verify` verdict with no instruction step.
The iOS HUD renders that as the amber "Verify in manual" card.
"""

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Ambient Field Lens /assist stub")


class AssistRequest(BaseModel):
    query: str = Field(default="", description="Operator voice query")
    image_jpeg_base64: str = Field(
        default="", description="Current frame as base64 JPEG (may be empty)"
    )


class AssistResponse(BaseModel):
    verdict: str
    step: str | None = None
    score: float = 0.0
    detail: str = ""


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "gate": "default-deny", "phase": 1}


@app.post("/assist", response_model=AssistResponse)
def assist(req: AssistRequest) -> AssistResponse:
    return AssistResponse(
        verdict="verify",
        step=None,
        score=0.0,
        detail=(
            "Calibration not yet run (Phase 1 stub). "
            "Verify in the manual before touching the machine."
        ),
    )
