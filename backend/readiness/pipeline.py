"""Join adapted observations into six raw checks; no model calls or live gate.

Archive runs preserve clocks and can never emit a live-ready result. Duplicate
roles are rejected rather than selected by score or most-recent arrival.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from math import isfinite

from .adapters import Adapted, AdapterError, Mode
from .checks import Frame, _mask, check_pen, evaluate
from .presence import check_pen_holder_presence


@dataclass(frozen=True)
class PipelineResult:
    checks: tuple
    evidence_errors: tuple[str, ...]
    provenance: tuple
    mode: str
    evidence_summary: dict
    component_checks: tuple

    def report(self):
        # This runner does not implement the product's grounding gate, controller
        # or procedure adapters. It never supplies a product step or green flag.
        return {'schema_version': 'drawing-pipeline-replay-v1', 'mode': self.mode,
                'checks': [asdict(c) for c in self.checks],
                'evidence_errors': list(self.evidence_errors),
                'provenance': [asdict(p) for p in self.provenance],
                'evidence_summary': self.evidence_summary,
                'archival_image_component_checks': [asdict(c) for c in self.component_checks],
                'component_checks_are_live_readiness': False,
                'verdict': 'amber', 'step': None, 'live_ready': False,
                'grounding_validated': False, 'network_calls': 0, 'gpu_used': False}


def _bound_archive(bundle, frame):
    p = bundle.provenance
    actual = (p.frame_sha256, p.width, p.height, p.camera, p.rig, p.surface_pose,
              p.tool, p.controller_session, p.frame_captured_at)
    expected = (frame.sha256, frame.width, frame.height, frame.camera, frame.rig,
                frame.surface_pose, frame.tool, frame.controller_session, frame.captured_at)
    if actual != expected:
        raise AdapterError('frame_context_mismatch')
    for record in (*bundle.masks, *bundle.observations, *((bundle.fitment,) if bundle.fitment else ())):
        rp = record.provenance
        if (record.frame_sha256 != frame.sha256 or rp is None
                or replace(rp, role='', object_id='', object_bounds=None)
                != replace(p, role='', object_id='', object_bounds=None)):
            raise AdapterError('mixed_record_provenance')
        if hasattr(record, 'width') and (record.width, record.height) != (frame.width, frame.height):
            raise AdapterError('mixed_record_dimensions')
        role = record.kind if hasattr(record, 'kind') else record.role if hasattr(record, 'role') else 'fitment'
        if rp.role != role or role == 'fitment' and record.tool != frame.tool:
            raise AdapterError('mixed_record_role_or_tool')


def run(frame: Frame, bundles: tuple[Adapted, ...], *, now: float, mode: Mode):
    if not isinstance(mode, Mode) or type(now) not in (int, float) or not isfinite(now):
        raise AdapterError('invalid_pipeline_clock_or_mode')
    masks, observations, fitments, provenances, errors = {}, {}, [], [], []
    for bundle in bundles:
        try:
            if bundle.provenance.mode != mode.value:
                raise AdapterError('mixed_pipeline_mode')
            if mode is Mode.LIVE:
                bundle.require_live(frame, now=now)
            else:
                _bound_archive(bundle, frame)
            provenances.append(bundle.provenance)
            for mask in bundle.masks:
                masks.setdefault(mask.kind, []).append(mask)
            for observation in bundle.observations:
                observations.setdefault(observation.role, []).append(observation)
            if bundle.fitment is not None:
                fitments.append(bundle.fitment)
        except AdapterError as error:
            errors.append(str(error))
    for kind, values in masks.items():
        if len(values) != 1 and not all(mask.ambiguous for mask in values):
            errors.append('duplicate_mask_role_' + kind)
    for role, values in observations.items():
        if len(values) != 1:
            errors.append('duplicate_observation_role_' + role)
    if len(fitments) > 1:
        errors.append('duplicate_fitment')
    def unique(mapping, key):
        values = mapping.get(key, [])
        return values[0] if len(values) == 1 else None
    # Any invalid or duplicated envelope invalidates the aggregate input rather
    # than allowing a later good envelope to hide it. Raw error codes retained.
    decision = evaluate(frame,
                        paper=unique(masks, 'paper') if not errors else None,
                        pen=unique(masks, 'pen') if not errors else None,
                        fitment=fitments[0] if len(fitments) == 1 and not errors else None,
                        pen_observation=unique(observations, 'pen') if not errors else None,
                        holder_observation=unique(observations, 'holder') if not errors else None,
                        now=now)
    summary = {'mask_pixels': {kind: [len(mask.pixels) for mask in values] for kind, values in masks.items()},
               'observation_roles': sorted(observations), 'fitment_observation_count': len(fitments),
               'aggregate_inputs_rejected': bool(errors),
               'ambiguous_mask_roles': sorted(kind for kind, values in masks.items() if len(values) > 1)}
    paper = unique(masks, 'paper') if not errors else None
    pen = unique(masks, 'pen') if not errors else None
    fitment = fitments[0] if len(fitments) == 1 and not errors else None
    components = (_mask(frame, paper, 'paper'),
                  check_pen_holder_presence(frame, unique(observations, 'pen') if not errors else None,
                                            unique(observations, 'holder') if not errors else None),
                  check_pen(frame, pen, fitment))
    return PipelineResult(decision.checks, tuple(errors), tuple(provenances), mode.value, summary, components)
