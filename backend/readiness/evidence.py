"""Immutable provenance for offline observation adapters; no provider clients."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Provenance:
    provider: str
    model: str
    response_id: str
    frame_sha256: str
    width: int
    height: int
    camera: str
    rig: str
    surface_pose: str
    tool: str
    controller_session: str
    frame_captured_at: float
    capture_clock_verified: bool
    request_started_at: float
    response_created_at: float
    response_completed_at: float
    ingested_at: float
    mode: str
    receipt_sha256: str
    request_sha256: str
    request_digest_basis: str
    response_sha256: str
    prompt_sha256: str
    semantic_origin: str
    object_id: str
    role: str
    parser: str
    linkage: str
    coordinate_space: str = 'native_full_frame_pixels'
    spatial_transform: str = 'identity_only'
    mask_encoding: str = ''
    object_bounds: tuple[int, int, int, int] | None = None


REQUIRED_CHECK_NAMES = (
    'paper_present', 'pen_holder_observable_presence', 'pen_fitted',
    'footprint_inside_paper', 'calibration_ready', 'approved_current_step',
)
