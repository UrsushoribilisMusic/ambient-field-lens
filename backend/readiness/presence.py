"""Observable pen/holder presence, separate from mechanical fitment.

Inputs are frame-bound observations, never a supplied verdict. Human reference
observations test the logic, not autonomous recognition. Occlusion fails the
observable-presence requirement without asserting physical object absence.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .checks import Check, Frame, State


class Visibility(str, Enum):
    CLEAR = 'clear'
    OCCLUDED = 'occluded'
    UNKNOWN = 'unknown'


@dataclass(frozen=True)
class Observation:
    frame_sha256: str
    width: int
    height: int
    role: str
    visible: Visibility
    observed_present: bool | None
    source: str  # human_reference or model_observation, not a verdict/score


def check_pen_holder_presence(frame: Frame, pen: Observation | None = None,
                              holder: Observation | None = None) -> Check:
    name = 'pen_holder_observable_presence'
    correction = 'Show the pen and holder clearly; fit the pen if it is absent.'
    missing, failed = [], []
    if not frame.sha256 or frame.width <= 0 or frame.height <= 0:
        return Check(name, State.UNKNOWN, 'Frame identity/dimensions missing.', correction)
    for role, observation in [('pen', pen), ('holder', holder)]:
        if (observation is None or observation.frame_sha256 != frame.sha256
                or (observation.width, observation.height) != (frame.width, frame.height)
                or observation.role != role
                or observation.source not in ('human_reference', 'model_observation')
                or not isinstance(observation.visible, Visibility)
                or observation.observed_present not in (True, False, None)
                or (observation.observed_present is not None and type(observation.observed_present) is not bool)):
            missing.append(role + ': missing or mismatched observation')
        elif observation.visible is Visibility.OCCLUDED:
            failed.append(role + ': occluded; observable presence fails, physical absence not inferred')
        elif observation.visible is Visibility.UNKNOWN or observation.observed_present is None:
            missing.append(role + ': visibility or presence unresolved')
        elif observation.observed_present is False:
            failed.append(role + ': not observed in clear view')
    if failed:
        # Preserve missing components too; another component's pass cannot hide them.
        return Check(name, State.FAIL, '; '.join(failed + missing), correction)
    if missing:
        return Check(name, State.UNKNOWN, '; '.join(missing), correction)
    return Check(name, State.PASS, 'Pen and holder both observed clearly; mechanical fitment not established.', '')
