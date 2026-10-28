"""One explicit paid SAM request; raw evidence stays outside the repository.

Docs: https://dev.meta.ai/docs/sam/segmenting and /sam/reading-segmentation.
No retries. An attempted request consumes this diagnostic's local receipt even
on failure. Box prompts test mask transport, not autonomous object recognition.
"""
import argparse
import base64
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prompt', required=True)
    args = parser.parse_args()
    image = args.image.read_bytes()
    key = os.environ.get('MODEL_API_KEY')
    if not key:
        fetch = Path.home() / 'projects/agentic-fleet-hub/vault/agent-fetch.sh'
        result = subprocess.run([str(fetch), 'MODEL_API_KEY', 'dev'], cwd=fetch.parent.parent,
                                capture_output=True, timeout=30)
        if result.returncode:
            raise SystemExit('Could not retrieve API credential; diagnostics withheld.')
        key = result.stdout.decode().strip()
    if not key or '\n' in key:
        raise SystemExit('Credential unavailable or malformed.')
    args.output.mkdir(parents=True, exist_ok=True)
    receipt = args.output / 'attempt.json'
    with receipt.open('x') as f:
        json.dump({'attempted_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   'model': 'sam-3.1', 'image_sha256': hashlib.sha256(image).hexdigest(),
                   'prompt': args.prompt, 'metadata': {'mask_encoding': 'one_bit'},
                   'image_bytes': len(image), 'max_requests': 1, 'automatic_retries': 0}, f, indent=2)
    payload = {'model': 'sam-3.1', 'input': [{'type': 'message', 'role': 'user', 'content': [
        {'type': 'input_text', 'text': args.prompt},
        {'type': 'input_image', 'image_url': 'data:image/jpeg;base64,' + base64.b64encode(image).decode()}]}],
        'stream': True, 'metadata': {'mask_encoding': 'one_bit'}}
    request_bytes = json.dumps(payload).encode()
    (args.output / 'request.json').write_bytes(request_bytes)
    request = urllib.request.Request('https://api.meta.ai/v1/responses', data=request_bytes,
                                    headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    events, types, output, completed = [], [], [], False
    try:
        with urllib.request.urlopen(request, timeout=90) as response, (args.output / 'raw.sse').open('wb') as raw:
            status = response.status
            for line in response:
                raw.write(line)
                if not line.startswith(b'data:'):
                    continue
                value = line[5:].strip()
                if value == b'[DONE]':
                    break
                event = json.loads(value)
                events.append(event)
                types.append(event.get('type'))
                if event.get('type') == 'response.output_text.delta':
                    output.append(event.get('delta', ''))
                if event.get('type') == 'response.completed':
                    completed = True
                    break
    except urllib.error.HTTPError as exc:
        (args.output / 'summary.json').write_text(json.dumps({'http_status': exc.code, 'completed': False, 'retry': False}))
        raise SystemExit('SAM returned HTTP ' + str(exc.code) + '; no retry performed.') from None
    except Exception:
        raise SystemExit('SAM diagnostic did not complete; partial private evidence retained, no retry performed.') from None
    (args.output / 'events.json').write_text(json.dumps(events))
    text = ''.join(output)
    (args.output / 'output.txt').write_text(text)
    summary = {'http_status': status, 'completed': completed, 'event_types': types,
               'output_characters': len(text), 'mask_tokens': text.count('<|mask;'), 'retry': False}
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
