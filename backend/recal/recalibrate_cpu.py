"""Refit step 3 from already measured prefill scores; no model load or GPU."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from analysis import calibrate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scores', required=True)
    parser.add_argument('--questions', required=True)
    parser.add_argument('--report', required=True)
    args = parser.parse_args()
    started = time.monotonic()
    scored = [json.loads(line) for line in Path(args.scores).read_text().splitlines() if line.strip()]
    raw_questions = Path(args.questions).read_bytes()
    source = [json.loads(line) for line in raw_questions.decode().splitlines() if line.strip()]
    by_id = {row['id']: row for row in scored}
    if len(by_id) != len(source) or len(scored) != len(source):
        raise ValueError('Question IDs/counts must match the original measured scores')
    questions, values = [], []
    for row in source:
        score = by_id[row['question_id']]
        if score['answerable'] != row['answerable']: raise ValueError('Labels changed after GPU scoring')
        questions.append({'id': row['question_id'], 'group': row['category'], 'answerable': row['answerable']})
        values.append(score['score'])
    result = calibrate(np.array(values), questions)
    result.update(gpu_used=False, elapsed_seconds=round(time.monotonic() - started, 4),
                  measured_scores_sha256=hashlib.sha256(Path(args.scores).read_bytes()).hexdigest(),
                  external_question_sha256=hashlib.sha256(raw_questions).hexdigest(),
                  split_repair='The initial hash split lacked a test class; this assignment uses labels/groups only, not model performance.')
    report_path = Path(args.report)
    report = json.loads(report_path.read_text())
    report.setdefault('initial_calibration', report['calibration'])
    report['calibration'] = result
    report['step3_rerun_on_cpu'] = True
    report_path.write_text(json.dumps(report, indent=2))
    report_path.with_name('glimmer-domain-calibration.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
