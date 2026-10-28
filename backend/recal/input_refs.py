"""Read declared external evaluation references without copying dataset files."""
import hashlib
import json
from pathlib import Path


def load_reference(path, role):
    path = Path(path).expanduser().resolve()
    raw = path.read_bytes()
    rows = [json.loads(line) for line in raw.decode().splitlines() if line.strip()]
    return rows, {'role': role, 'filename': path.name, 'sha256': hashlib.sha256(raw).hexdigest(),
                  'count': len(rows), 'pre_existing': True, 'vendored': False,
                  'origin': 'Ross pre-event question reference' if role == 'domain-questions'
                  else 'Canis ancillary evaluation reference'}


def evaluation_inputs(core_path, matched_path, ood_path, questions_path):
    cases, refs = [], []
    for pool, path in (('core', core_path), ('matched', matched_path), ('ood', ood_path)):
        rows, reference = load_reference(path, pool)
        refs.append(reference)
        for row in rows:
            cases.append({'id': row['item_id'], 'label': row['target_class'],
                          'positive': row['split'] == 'positive', 'pool': pool,
                          'text': row['prompt'], 'label_status': row.get('label_status', 'source-label')})
    rows, reference = load_reference(questions_path, 'domain-questions')
    refs.append(reference)
    questions = [{'id': r['question_id'], 'group': r['category'], 'text': r['prompt'],
                  'answerable': bool(r['answerable'])} for r in rows]
    if len({r['id'] for r in cases}) != len(cases): raise ValueError('Duplicate evaluation IDs')
    if len({r['id'] for r in questions}) != len(questions): raise ValueError('Duplicate question IDs')
    return cases, questions, refs
