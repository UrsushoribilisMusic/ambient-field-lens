"""CPU-only diagnostic from frozen manual readings; never accepts robot geometry.

Four corner IDs fit the homography; five independent IDs validate it. Reading
edits after inspecting residuals require a new record and independent review.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from readiness.geometry import Correspondence, _normalise, fit_registration, project


def report(readings, source_dir):
    if readings['fit_ids'] != [1, 2, 3, 4] or readings['validation_ids'] != [5, 6, 7, 8, 9]:
        raise ValueError('Declared split must remain corners 1-4 / held-out 5-9')
    if readings['acceptance_bar_px'] != 2.0:
        raise ValueError('Declared bar must remain 2px')
    for name, digest in [('source_frame', 'source_frame_sha256'),
                         ('physical_measurements', 'physical_measurements_sha256')]:
        path = (source_dir / readings[name]).resolve()
        if not path.is_relative_to(source_dir.resolve()):
            raise ValueError('Source must stay inside the capture directory')
        if hashlib.sha256(path.read_bytes()).hexdigest() != readings[digest]:
            raise ValueError('Source digest mismatch')
    with Image.open(source_dir / readings['source_frame']) as image:
        if list(image.size) != readings['image_size_px']:
            raise ValueError('Source image dimensions mismatch')
    points = readings['points']
    if [p['id'] for p in points] != list(range(1, 10)):
        raise ValueError('Nine distinct ordered readings required')
    fit, held = points[:4], points[4:]
    a, ta = _normalise([p['plane_mm'] for p in fit])
    b, tb = _normalise([p['image_px'] for p in fit])
    rows = []
    for (x, y), (u, v) in zip(a, b):
        rows.extend(([-x, -y, -1, 0, 0, 0, u*x, u*y, u],
                     [0, 0, 0, -x, -y, -1, v*x, v*y, v]))
    if np.linalg.matrix_rank(rows) < 8:
        raise ValueError('Degenerate fitting points')
    _, _, vt = np.linalg.svd(np.asarray(rows), full_matrices=True)
    h = np.linalg.inv(tb) @ vt[-1].reshape(3, 3) @ ta
    h /= np.linalg.norm(h)
    residuals = []
    predicted = project(h, [p['plane_mm'] for p in points])
    for point, prediction in zip(points, predicted):
        delta = prediction - np.asarray(point['image_px'])
        residuals.append({'id': point['id'], 'split': 'fit' if point['id'] < 5 else 'validation',
                          'observed_px': point['image_px'], 'projected_px': prediction.tolist(),
                          'residual_xy_px': delta.tolist(), 'error_px': float(np.linalg.norm(delta))})
    errors = [p['error_px'] for p in residuals if p['split'] == 'validation']
    result = {'measurement_record': readings, 'homography_paper_mm_to_image_px': h.tolist(),
              'residuals': residuals, 'held_out_rms_px': float(np.sqrt(np.mean(np.square(errors)))),
              'held_out_max_px': max(errors), 'acceptance_bar_px': 2.0,
              'network_calls': 0, 'gpu_used': False, 'robot_coordinate_linkage': 'unknown',
              'footprint_registration_accepted': False}
    def pairs(group):
        return [Correspondence(tuple(p['plane_mm']), tuple(p['image_px'])) for p in group]
    try:
        width, height = readings['image_size_px']
        fit_registration(pairs(fit), pairs(held), camera=f'reolink-{width}x{height}',
                         rig=readings.get('camera_pose', 'v2-2026-10-27'),
                         surface_pose='measured-paper-local-plane',
                         source_frame_sha256=readings['source_frame_sha256'], max_error_px=2.0)
        result['paper_plane_validation'] = 'PASS'
    except ValueError as error:
        result['paper_plane_validation'] = 'FAIL'
        result['rejection'] = str(error)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--readings', type=Path, required=True)
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = report(json.loads(args.readings.read_text()), args.source_dir)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('paper_plane_validation', 'held_out_rms_px',
                                                  'held_out_max_px', 'footprint_registration_accepted')}))
