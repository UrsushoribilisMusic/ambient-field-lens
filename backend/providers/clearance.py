"""Live-mask containment and explicit mm uncertainty; never an equipment command."""
import math
import numpy as np
from readiness.geometry import _convex, _touches_cell, project


def measured_registration_error_mm(matrix, validation_plane_mm, validation_image_px):
    """Independent held-out residual in surface coordinates, not a global px/mm guess."""
    expected = np.asarray(validation_plane_mm, dtype=float)
    observed = np.asarray(validation_image_px, dtype=float)
    if expected.shape != observed.shape or expected.ndim != 2 or expected.shape[1] != 2 or len(expected) < 4:
        raise ValueError('four_independent_validation_correspondences_required')
    reconstructed = project(np.linalg.inv(matrix), observed)
    errors = np.linalg.norm(reconstructed - expected, axis=1)
    if not np.isfinite(errors).all():
        raise ValueError('nonfinite_registration_error')
    return float(errors.max())


def containment_clearance(paper, vertices_mm, matrix, *, frame_sha256,
                          registration_error_mm=None, reading_uncertainty_mm=None,
                          robot_allowance_mm=None, geometry_reviewed=False):
    """All numeric inputs are server-owned measured/reviewed values, never LLM estimates.

    Uses every footprint raster cell, including holes, and maps boundary distances
    into mm with the full projective transform. Sampling uncertainty is reported
    separately. The inherited 2px registration bar is not used in this check.
    """
    result = {'frame_sha256': frame_sha256, 'state': 'unknown',
              'reason': 'geometry_or_uncertainty_unavailable', 'clearance_mm': None,
              'registration_error_mm': registration_error_mm,
              'reading_uncertainty_mm': reading_uncertainty_mm,
              'robot_allowance_mm': robot_allowance_mm, 'sampling_uncertainty_mm': None,
              'required_clearance_mm': None, 'step': None}
    if (not geometry_reviewed or paper.frame_sha256 != frame_sha256 or paper.kind != 'paper'
            or paper.visible is not True or paper.ambiguous or not paper.pixels):
        return result
    values = (registration_error_mm, reading_uncertainty_mm, robot_allowance_mm)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in values):
        return result
    try:
        h = np.asarray(matrix, dtype=float)
        if h.shape != (3, 3) or not np.isfinite(h).all():
            return result
        inv = np.linalg.inv(h)
        polygon = _convex(project(h, _convex(vertices_mm)))
        lo = np.floor(polygon.min(axis=0)).astype(int)-1
        hi = np.ceil(polygon.max(axis=0)).astype(int)
        if (hi[0]-lo[0]+1)*(hi[1]-lo[1]+1) > 500_000 or len(paper.pixels) > 1_000_000:
            result['reason'] = 'geometry_budget_exceeded'
            return result
        cells = {(x, y) for y in range(lo[1], hi[1]+1) for x in range(lo[0], hi[0]+1)
                 if _touches_cell(polygon, x, y)}
        if not cells or any(not 0 <= x < paper.width or not 0 <= y < paper.height for x, y in paper.pixels):
            return result
        boundary = [(x+.5, y+.5) for x, y in paper.pixels
                    if any((x+dx, y+dy) not in paper.pixels for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)))]
        if not boundary:
            return result
        # All requested cells are tested, not just a bounding box or four corners.
        inside = cells <= paper.pixels
        centres = np.array([(x+.5, y+.5) for x, y in cells])
        from scipy.spatial import cKDTree
        border_mm = project(inv, boundary)
        footprint_mm = project(inv, centres)
        minimum = float(cKDTree(border_mm).query(footprint_mm)[0].min())
        # Conservative raster-center allowance: measure cell corner distances at
        # every relevant centre; perspective scale is not assumed constant.
        sample = np.concatenate((np.asarray(boundary), centres))
        projected = project(inv, sample)
        radius = max(float(np.linalg.norm(project(inv, sample+delta)-projected, axis=1).max())
                     for delta in ((-.5,-.5),(-.5,.5),(.5,-.5),(.5,.5)))
        sampling = 2*radius  # One cell on each of the two sampled shapes.
        clearance = minimum if inside else -minimum
        required = sum(values)+sampling
        result.update(clearance_mm=clearance, sampling_uncertainty_mm=sampling,
                      required_clearance_mm=required)
        if not inside:
            result.update(state='fail', reason='drawing_footprint_outside_paper_boundary')
        elif clearance <= required:
            result.update(state='unknown', reason='clearance_does_not_exceed_uncertainty')
        else:
            result.update(state='pass', reason='clearance_exceeds_combined_uncertainty')
        return result
    except (ValueError, TypeError, np.linalg.LinAlgError):
        return result
