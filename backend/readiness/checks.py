"""Deterministic evidence checks; unknown never passes. No model or IO calls.

Footprint cells must come from the separately validated geometry stage. This
module cannot establish a real registration from a mask or calibration file.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite


class State(str, Enum):
    PASS = 'pass'
    FAIL = 'fail'
    UNKNOWN = 'unknown'


@dataclass(frozen=True)
class Check:
    name: str
    state: State
    reason: str
    correction: str


@dataclass(frozen=True)
class Frame:
    sha256: str
    width: int
    height: int
    captured_at: float
    camera: str
    rig: str
    surface_pose: str
    tool: str
    controller_session: str


@dataclass(frozen=True)
class Mask:
    frame_sha256: str
    width: int
    height: int
    pixels: frozenset[tuple[int, int]]
    kind: str
    visible: bool | None
    ambiguous: bool = False


@dataclass(frozen=True)
class Fitment:
    frame_sha256: str
    tool: str
    fitted: bool | None
    visible: bool


@dataclass(frozen=True)
class Footprint:
    frame_sha256: str
    camera: str
    rig: str
    surface_pose: str
    cells: frozenset[tuple[int, int]]
    registration_validated: bool
    margin_mm: float
    required_margin_mm: float


@dataclass(frozen=True)
class Calibration:
    observed_at: float
    calibrated: bool
    session_ready: bool
    controller_session: str
    tool: str
    surface_pose: str
    binding_verified: bool


@dataclass(frozen=True)
class ProcedureStep:
    procedure: str
    version: str
    step: str
    text: str
    source_sha256: str


@dataclass(frozen=True)
class ApprovedProcedure:
    current: ProcedureStep
    approved: bool


@dataclass(frozen=True)
class Decision:
    checks: tuple[Check, ...]

    @property
    def verdict(self) -> str:
        return 'green' if len(self.checks) == 5 and all(c.state is State.PASS for c in self.checks) else 'amber'


def _result(name, state, reason, correction):
    return Check(name, state, reason, '' if state is State.PASS else correction)


def _mask(frame, mask, kind):
    correction = 'Show the paper clearly.' if kind == 'paper' else 'Show the intended pen and its holder clearly.'
    name = 'paper_present' if kind == 'paper' else 'pen_fitted'
    if mask is None:
        return _result(name, State.UNKNOWN, 'No current-frame mask.', correction)
    if (mask.frame_sha256 != frame.sha256 or (mask.width, mask.height) != (frame.width, frame.height)
            or mask.kind != kind or mask.ambiguous or mask.visible is not True):
        return _result(name, State.UNKNOWN, 'Mask is mismatched, ambiguous or insufficiently visible.', correction)
    if any(type(x) is not int or type(y) is not int or not (0 <= x < frame.width and 0 <= y < frame.height)
           for x, y in mask.pixels):
        return _result(name, State.UNKNOWN, 'Mask has invalid image coordinates.', correction)
    if not mask.pixels:
        return _result(name, State.FAIL, 'No matching region observed.', correction)
    return _result(name, State.PASS, 'Current-frame region observed.', '')


def check_pen(frame, mask, fitment):
    observed = _mask(frame, mask, 'pen')
    if observed.state is not State.PASS:
        return observed
    correction = 'Fit the intended pen in the holder and show the fitment clearly.'
    if (fitment is None or fitment.frame_sha256 != frame.sha256 or fitment.tool != frame.tool
            or not fitment.visible or fitment.fitted is None):
        return _result('pen_fitted', State.UNKNOWN, 'A pen mask does not establish fitment.', correction)
    return _result('pen_fitted', State.PASS if fitment.fitted is True else State.FAIL,
                   'Pen is fitted.' if fitment.fitted is True else 'Pen is not fitted.', correction)


def check_footprint(frame, paper, footprint):
    correction = 'Register this camera and surface pose, then recompute the footprint with its margin.'
    if _mask(frame, paper, 'paper').state is not State.PASS:
        return _result('footprint_inside_paper', State.UNKNOWN, 'Paper boundary is unavailable.', 'Show the complete drawing paper.')
    if (footprint is None or not footprint.registration_validated
            or (footprint.frame_sha256, footprint.camera, footprint.rig, footprint.surface_pose)
            != (frame.sha256, frame.camera, frame.rig, frame.surface_pose)
            or not footprint.cells
            or not all(isfinite(v) and v >= 0 for v in (footprint.margin_mm, footprint.required_margin_mm))
            or footprint.margin_mm < footprint.required_margin_mm):
        return _result('footprint_inside_paper', State.UNKNOWN, 'Missing, stale or unvalidated footprint geometry.', correction)
    if any(type(x) is not int or type(y) is not int for x, y in footprint.cells):
        return _result('footprint_inside_paper', State.UNKNOWN, 'Footprint cells are not raster coordinates.', correction)
    # Set containment checks holes and offscreen cells too; no bounding-box shortcut.
    inside = footprint.cells <= paper.pixels
    return _result('footprint_inside_paper', State.PASS if inside else State.FAIL,
                   'Every footprint cell is on paper.' if inside else 'Footprint extends beyond observed paper.',
                   'Reposition the paper or reduce the drawing, then re-register and check the preview.')


def check_calibration(frame, calibration, now, max_age=5.0):
    correction = 'Read fresh controller state bound to this session, pen and surface pose; calibrate this setup if needed.'
    if (calibration is None or not calibration.binding_verified
            or not all((frame.controller_session, frame.tool, frame.surface_pose))
            or (calibration.controller_session, calibration.tool, calibration.surface_pose)
            != (frame.controller_session, frame.tool, frame.surface_pose)
            or not all(isfinite(v) for v in (now, max_age, calibration.observed_at)) or max_age <= 0
            or not 0 <= now - calibration.observed_at <= max_age):
        return _result('calibration_ready', State.UNKNOWN, 'Controller state is missing, stale or not bound to this setup.', correction)
    ready = calibration.calibrated is True and calibration.session_ready is True
    return _result('calibration_ready', State.PASS if ready else State.FAIL,
                   'Calibration ready for this setup.' if ready else 'Current setup is not calibrated and ready.', correction)


def check_procedure(selected, approved):
    correction = 'Return to the current approved procedure step and retrieve its exact source/version.'
    if approved is None or approved.approved is not True or selected is None:
        return _result('approved_current_step', State.UNKNOWN, 'Approved current procedure evidence is missing.', correction)
    step = approved.current
    if not all((step.procedure, step.version, step.step, step.text, step.source_sha256)):
        return _result('approved_current_step', State.UNKNOWN, 'Approved source identity is incomplete.', correction)
    match = selected == step
    return _result('approved_current_step', State.PASS if match else State.FAIL,
                   'Exact current approved step matched.' if match else 'Requested step differs from the approved current source.', correction)


def evaluate(frame, paper=None, pen=None, fitment=None, footprint=None, calibration=None,
             selected_step=None, approved_procedure=None, *, now, max_frame_age=5.0):
    names = ('paper_present', 'pen_fitted', 'footprint_inside_paper', 'calibration_ready', 'approved_current_step')
    if (not frame.sha256 or frame.width <= 0 or frame.height <= 0
            or not all(isfinite(v) for v in (now, frame.captured_at, max_frame_age))
            or max_frame_age <= 0 or not 0 <= now - frame.captured_at <= max_frame_age):
        return Decision(tuple(_result(n, State.UNKNOWN, 'Frame identity or freshness is invalid.',
                                      'Capture a fresh identified frame and re-check the setup.') for n in names))
    return Decision((_mask(frame, paper, 'paper'), check_pen(frame, pen, fitment),
                     check_footprint(frame, paper, footprint), check_calibration(frame, calibration, now),
                     check_procedure(selected_step, approved_procedure)))
