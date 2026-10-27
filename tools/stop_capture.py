"""Gracefully finalize one operator-requested camera take, without moving Ross."""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import signal
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--id', required=True)
parser.add_argument('--output-dir', type=Path)
args = parser.parse_args()
if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', args.id):
    parser.error('Invalid scene ID')
root = args.output_dir or (Path.home() / 'Movies/Ambient-Field-Lens' /
                          datetime.date.today().isoformat() / 'drawing-readiness')
receipt = root / (args.id + '.recording.json')
data = json.loads(receipt.read_text())
pid = int(data['pid'])
clip = root / (args.id + '.mp4')
if data['clip'] != str(clip):
    raise SystemExit('Recording receipt does not match requested take')
# Validate PID identity in memory; never print credential-bearing process argv.
comm = subprocess.run(['ps', '-p', str(pid), '-o', 'comm='], capture_output=True, text=True)
argv = subprocess.run(['ps', '-p', str(pid), '-o', 'args='], capture_output=True, text=True)
if comm.returncode or Path(comm.stdout.strip()).name != 'ffmpeg' or str(clip) not in argv.stdout:
    raise SystemExit('Recording process identity not verified; no signal sent')
data['stop_requested'] = True
receipt.write_text(json.dumps(data, indent=2))
os.kill(pid, signal.SIGINT)
print('Finalizing requested camera take; no robot command sent.')
