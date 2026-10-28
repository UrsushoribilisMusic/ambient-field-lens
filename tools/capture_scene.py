"""Record an operator-staged scene; never move Ross or infer ground truth."""
import argparse
import datetime
import hashlib
import json
import re
from pathlib import Path
import subprocess
import urllib.request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', required=True)
    parser.add_argument('--condition', required=True)
    parser.add_argument('--seconds', type=int, default=20)
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', args.id):
        parser.error('Use a short scene ID containing only letters, digits, underscores or hyphens')
    if not 5 <= args.seconds <= 600: parser.error('Capture duration must be 5–600 seconds')
    scene = Path.home() / 'Library/Application Support/obs-studio/basic/scenes/Untitled.json'
    source = next(s for s in json.loads(scene.read_text())['sources'] if s.get('name') == 'Robot_Main_Cam')
    url = source['settings']['input']  # Never print credentials or put them in metadata.
    root = args.output_dir or (Path.home() / 'Movies/Ambient-Field-Lens' /
                              datetime.date.today().isoformat() / 'drawing-readiness')
    root.mkdir(parents=True, exist_ok=True)
    clip, frame = root / (args.id + '.mp4'), root / (args.id + '.jpg')
    if clip.exists(): parser.error('Scene already exists; use a new ID rather than overwriting evidence')
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    controller = {'available': False}
    try:
        with urllib.request.urlopen('http://127.0.0.1:7870/api/status', timeout=3) as response:
            status = json.load(response)
        controller = {'available': True, 'observed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      'calibration': status.get('calibration'), 'arm_port': status.get('arm_port'),
                      'job_running': status.get('job_running'), 'showcase_running': status.get('showcase_running'),
                      'session_binding_verified': False}
        if controller['job_running'] or controller['showcase_running']:
            raise RuntimeError('Controller has an active job; operator-staged capture requires idle Ross')
    except (OSError, ValueError):
        pass
    command = ['/opt/homebrew/bin/ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error',
               '-rtsp_transport', 'tcp', '-i', url, '-t', str(args.seconds), '-an', '-c:v', 'libx264',
               '-preset', 'veryfast', '-crf', '20', str(clip)]
    receipt = root / (args.id + '.recording.json')
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    receipt.write_text(json.dumps({'pid': process.pid, 'clip': str(clip), 'started_utc': started,
                                   'stop_requested': False}, indent=2))
    try:
        process.communicate(timeout=args.seconds + 15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise RuntimeError('Camera capture timed out; credential-bearing diagnostics withheld') from None
    stopped = json.loads(receipt.read_text()).get('stop_requested') is True
    if process.returncode != 0 and not (process.returncode == 255 and stopped):
        raise RuntimeError('Capture failed; credential-bearing diagnostics withheld')
    probe = subprocess.run(['/opt/homebrew/bin/ffprobe', '-v', 'error', '-show_entries',
                            'format=duration', '-of', 'json', str(clip)], capture_output=True, timeout=10)
    if probe.returncode: raise RuntimeError('Recorded clip could not be finalized')
    duration = float(json.loads(probe.stdout)['format']['duration'])
    if duration <= 0: raise RuntimeError('Recorded clip is empty')
    representative = max(0, duration - 3)
    extraction = subprocess.run(['/opt/homebrew/bin/ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error',
                    '-ss', str(representative), '-i', str(clip), '-frames:v', '1', str(frame)],
                    capture_output=True, timeout=10)
    if extraction.returncode: raise RuntimeError('Frame extraction failed')
    record = {'id': args.id, 'requested_condition': args.condition,
              'question': 'Can I draw this here?', 'capture_started_utc': started,
              'camera_id': 'ross-reolink-tripod', 'clip': str(clip), 'frame': str(frame),
              'clip_sha256': hashlib.sha256(clip.read_bytes()).hexdigest(),
              'frame_sha256': hashlib.sha256(frame.read_bytes()).hexdigest(),
              'representative_frame_seconds': representative,
              'actual_duration_seconds': duration, 'operator_stop_requested': stopped,
              'review_status': 'unreviewed', 'synthetic': False,
              'controller_snapshot': controller}
    (root / (args.id + '.capture.json')).write_text(json.dumps(record, indent=2))
    receipt.unlink()
    print(json.dumps({'id': args.id, 'clip': str(clip), 'frame': str(frame), 'review_status': 'unreviewed'}))


if __name__ == '__main__': main()
