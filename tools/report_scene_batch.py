"""Inventory private captures and replay two pure checks without network/model IO.

Actual missing observations remain unknown. Human-reference replay is a separate
column and never counted as autonomous recognition or GPU eligibility.
Only whitelisted provenance leaves the private capture directory.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import re
from pathlib import Path
import subprocess

from readiness.checks import Frame, Mask, check_footprint
from readiness.presence import Observation, Visibility, check_pen_holder_presence


def resolve_asset(root, value):
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    if not path.is_relative_to(root.resolve()) or path.suffix.lower() not in ('.jpg', '.jpeg', '.png'):
        raise ValueError('Image asset must remain inside its capture directory')
    if not path.is_file():
        raise ValueError('Image asset missing: ' + path.name)
    return path


def digest(path, expected):
    observed = hashlib.sha256(path.read_bytes()).hexdigest()
    if not expected or observed != expected:
        raise ValueError('Image digest missing/mismatch: ' + path.name)
    return observed


def camera_bucket(width, height, phone=False):
    # Dimensions identify the stream, not lens intrinsics or equal FOV/crop.
    return ('phone' if phone else 'reolink') + f'-{width}x{height}-intrinsics-unknown'


def pose_bucket(record, phone=False):
    if phone:
        return 'phone-overhead-unmeasured'
    ident = record.get('id', '')
    pose = record.get('pose_bucket', '')
    for letter in 'ABCDEF':
        if pose.startswith('tripod-' + letter):
            return 'tripod-' + letter + '-unmeasured'
    # Capture sequence fallback, never an inferred numerical camera pose.
    match = re.match(r'S(\d+)', ident)
    if not match:
        return 'unassigned'
    number = int(match.group(1))
    letter = 'A' if number <= 8 else 'B' if number == 9 else 'C' if number == 10 else 'D' if number <= 23 else 'E' if number == 24 else 'F'
    return 'tripod-' + letter + '-unmeasured'


def load_records(root):
    records = {}
    def add(record, source):
        if not record.get('frame'):
            return
        record = dict(record)
        if record.get('orientation_normalized_frame'):
            record['frame'] = record['orientation_normalized_frame']
            record['frame_sha256'] = record['orientation_normalized_sha256']
        path = resolve_asset(root, record['frame'])
        previous = records.get(path, {})
        records[path] = {**previous, **record, '_source': source, '_path': path}
    for path in sorted(root.glob('*.capture.json')):
        add(json.loads(path.read_text()), path.name)
    legacy = root / 'S00-capture.json'
    if legacy.exists():
        add(json.loads(legacy.read_text()), legacy.name)
    review = root / 'review-manifest.json'
    if review.exists():
        for record in json.loads(review.read_text()).get('scenes', []):
            add(record, review.name)
    # Samples override their parent frame identity, never share its digest.
    for parent in list(records.values()):
        for sample in parent.get('samples', []):
            add({**parent, 'id': parent['id'] + '@' + str(sample['seconds']),
                 'frame': sample['frame'], 'frame_sha256': sample['sha256'],
                 'representative_frame_seconds': sample['seconds'], 'samples': [],
                 'observed_condition': sample['condition'], 'review_status': 'visually-reviewed-reference-sample'}, parent['_source'])
    return sorted(records.values(), key=lambda r: r['_path'].name)


def dimensions(path):
    output = subprocess.check_output(['/opt/homebrew/bin/ffprobe', '-v', 'error', '-select_streams', 'v:0',
                                      '-show_entries', 'stream=width,height', '-of', 'json', str(path)])
    stream = json.loads(output)['streams'][0]
    return stream['width'], stream['height']


def reference_observation(frame, role, label):
    states = {'clear_present': (Visibility.CLEAR, True), 'clear_not_observed': (Visibility.CLEAR, False),
              'occluded': (Visibility.OCCLUDED, None), 'unresolved': (Visibility.UNKNOWN, None)}
    if label is None:
        return None
    visibility, present = states[label]
    return Observation(frame.sha256, frame.width, frame.height, role, visibility, present, 'human_reference')


def diagnostic_paper(root, frame):
    directory = root / 'sam-diagnostic-01'
    attempt = directory / 'attempt.json'
    if not attempt.exists() or json.loads(attempt.read_text())['image_sha256'] != frame.sha256:
        return None
    parsed = json.loads((directory / 'parsed.json').read_text())
    record = next(r for r in parsed['records'] if r['kind'] == 'mask' and r['object_id'] == '1')
    header, separator, raster = (directory / record['artifact']).read_bytes().partition(b'\n255\n')
    if not separator or len(raster) != record['width'] * record['height']:
        raise ValueError('Invalid saved diagnostic paper raster')
    bounds = record['bounds']
    cells = frozenset((bounds['left'] + i % record['width'], bounds['top'] + i // record['width'])
                      for i, value in enumerate(raster) if value)
    return Mask(frame.sha256, frame.width, frame.height, cells, 'paper', True)


def build_report(roots, references):
    rows, profiles = [], {}
    for root in roots:
        day = root.parent.name
        for record in load_records(root):
            path = record['_path']
            sha = digest(path, record.get('frame_sha256'))
            width, height = dimensions(path)
            phone = record.get('id') == 'S14' or record.get('camera_id', '').startswith('operator-phone')
            profile = camera_bucket(width, height, phone)
            profiles[profile] = {'id': profile, 'width': width, 'height': height,
                                 'intrinsics': None, 'distortion': None,
                                 'cross_stream_coordinate_transfer_validated': False}
            pose = pose_bucket(record, phone)
            frame = Frame(sha, width, height, 0, 'operator-phone' if phone else 'ross-reolink', pose,
                          record.get('surface_pose', 'surface-pose-unverified'), 'ross-pen', '')
            label = references.get(path.name, {})
            if label and label.get('frame_sha256') != sha:
                raise ValueError('Reference label image digest missing/mismatch: ' + path.name)
            ref = check_pen_holder_presence(frame, reference_observation(frame, 'pen', label.get('pen')),
                                           reference_observation(frame, 'holder', label.get('holder')))
            actual_presence = check_pen_holder_presence(frame)  # No model presence observations supplied.
            footprint = check_footprint(frame, diagnostic_paper(root, frame), None)
            expected = label.get('expected_presence')
            rows.append({'scene_id': record.get('id'), 'asset': day + '/drawing-readiness/' + path.name,
                         'frame_sha256': sha, 'source_record': day + '/drawing-readiness/' + record['_source'],
                         'camera_profile': profile, 'pose_bucket': pose,
                         'pose_assignment_method': 'operator stage/capture sequence, not measured metric pose',
                         'review_status': record.get('review_status', 'reference-reviewed' if record.get('reviewer') else 'unreviewed'),
                         'observed_variations': record.get('known_variations', []),
                         'observed_note': record.get('observed_condition', record.get('observed', '')),
                         'reference_labels': label, 'reference_presence_logic': asdict(ref),
                         'actual_presence_check': asdict(actual_presence), 'actual_footprint_check': asdict(footprint),
                         'expected_reference_presence': expected,
                         'reference_logic_disagreement': expected is not None and ref.state.value != expected,
                         'note': 'Reference replay is not a detector evaluation; actual missing inputs remain unknown.'})
    return {'dataset': 'drawing-readiness-through-2026-10-27', 'scene_count': len(rows),
            'profiles': sorted(profiles.values(), key=lambda p: p['id']), 'scenes': rows,
            'reference_logic_disagreements': [r['asset'] for r in rows if r['reference_logic_disagreement']],
            'gpu_eligible': False, 'viewpoint_invariance': 'untested; views captured, no cross-view calibrated evaluation',
            'live_gate_wiring': False,
            'gaps': ['No real marker/robot registration accepted; S12 nominal/refined fits failed.',
                     'Quantitative out-of-paper footprint and robot registration unvalidated; qualitative placement labels do not substitute.',
                     'Presence outputs from an image recognizer absent; references are human-reviewed only.',
                     'Paper masks available only for the one S03 SAM diagnostic, not the whole batch.',
                     'No fresh controller session/tool/surface binding or exact approved current corpus step.',
                     'Physical drawing commanded40x40mm measured45x40mm; not a dimensional pass.']}


def write_markdown(report):
    text = ['# Codi — CPU scene inventory, 27 October 2026', '',
            f"Inventoried **{report['scene_count']} image assets** with verified hashes, actual stream dimensions and coarse pose buckets.", '',
            '**No autonomous presence accuracy, real containment pass or viewpoint-invariance result is claimed.**',
            'Reference observations are hand labels. Replaying them tests logic, not image recognition.', '',
            '| Scene / frame | Profile | Pose | Human-reference presence logic | Actual presence | Actual footprint |',
            '| --- | --- | --- | --- | --- | --- |']
    for row in report['scenes']:
        text.append('| ' + ' | '.join([row['scene_id'] + ' / ' + Path(row['asset']).name, row['camera_profile'],
                                      row['pose_bucket'], row['reference_presence_logic']['state'],
                                      row['actual_presence_check']['state'], row['actual_footprint_check']['state']]) + ' |')
    text.extend(['', '## Evidence gaps', ''] + ['- ' + gap for gap in report['gaps']])
    text.extend(['', 'GPU eligibility remains **false**. The live backend is unchanged and default-deny.',
                 'Only scene metadata is versioned; source photos/videos remain private outside the repository.', ''])
    return '\n'.join(text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--capture-dir', action='append', type=Path, required=True)
    parser.add_argument('--reference-labels', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    report = build_report(args.capture_dir, json.loads(args.reference_labels.read_text())['frames'])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / 'scene-batch-2026-10-27.json').write_text(json.dumps(report, indent=2))
    (args.output_dir / 'scene-batch-2026-10-27.md').write_text(write_markdown(report))
    print(json.dumps({'scene_count': report['scene_count'], 'profiles': len(report['profiles']),
                      'reference_logic_disagreements': report['reference_logic_disagreements'], 'gpu_eligible': False}))


if __name__ == '__main__':
    main()
