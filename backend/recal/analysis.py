"""Clean-room contrastive baseline and research-only calibration, authored in-event."""
import math
import re

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from scipy.stats import spearmanr

AXES = ('confident', 'uncertain', 'curious', 'concern', 'reluctant', 'warm', 'mischief')


def unit(values):
    return values / np.maximum(np.linalg.norm(values, axis=-1, keepdims=True), 1e-9)


def training_item(record):
    # OOD and matched negatives never enter the fitted directions. The fixed
    # parity split is declared before seeing any Glimmer activation or score.
    if record['pool'] != 'core': return False
    return int(re.findall(r'\d+', record['id'])[-1]) % 2 == 0


def select_directions(states, records):
    train = np.array([training_item(r) for r in records])
    heldout = np.array([r['pool'] == 'core' and not training_item(r) for r in records])
    normalized = unit(states)
    directions, selection = {}, {}
    for axis in AXES:
        positive = np.array([r['label'] == axis and r['positive'] for r in records])
        fit_pos, fit_neg = train & positive, train & ~positive
        if fit_pos.sum() < 2 or fit_neg.sum() < 2:
            raise ValueError('Insufficient training examples for ' + axis)
        directions[axis] = unit(states[fit_pos].mean(axis=0) - states[fit_neg].mean(axis=0))
        scores = np.einsum('nlh,lh->nl', normalized, directions[axis])
        aucs = [float(roc_auc_score(positive[heldout], scores[heldout, layer])) for layer in range(states.shape[1])]
        best = int(np.argmax(aucs))
        details = {}
        for pool in ('matched', 'ood'):
            mask = np.array([r['pool'] == pool for r in records])
            if not mask.any(): continue
            p = positive[mask]
            details[pool] = {'count': int(mask.sum()),
                             'auc': float(roc_auc_score(p, scores[mask, best])) if len(set(p)) == 2 else None,
                             'mean_score': float(scores[mask, best].mean())}
        selection[axis] = {'layer': best, 'heldout_auc': aucs[best], 'per_layer_auc': aucs,
                           'fit_positive': int(fit_pos.sum()), 'fit_negative': int(fit_neg.sum()),
                           'heldout_count': int(heldout.sum()), 'external_checks': details}
    return directions, selection


def question_scores(states, directions, selection):
    normalized = unit(states)
    parts = []
    for axis in ('confident', 'uncertain'):
        layer = selection[axis]['layer']
        parts.append(normalized[:, layer] @ directions[axis][layer])
    return parts[0] - parts[1]


def wilson_lower(successes, count):
    if count == 0: return 0.0
    z = 1.959963984540054
    p = successes / count
    return float((p + z*z/(2*count) - z*math.sqrt(p*(1-p)/count + z*z/(4*count*count))) / (1 + z*z/count))


def calibrate(scores, questions, target=0.90):
    # Keep topical categories together, preventing paraphrase/category leakage
    # between Platt fitting, threshold selection, and the final untouched test.
    labels = np.array([q['answerable'] for q in questions], dtype=int)
    groups = np.array([q['group'] for q in questions])
    if len(set(labels)) < 2 or any(len(set(groups[labels == label])) < 3 for label in (0, 1)):
        return {'enabled': False, 'status': 'insufficient_grouped_split',
                'target_precision': target, 'phase3_review_required': True}
    # Assignment uses only labels and groups, never model scores. Whole topics
    # stay together, with both classes represented in each of three folds.
    buckets = np.zeros(len(questions), dtype=int)
    splitter = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=0)
    for fold, (_, indices) in enumerate(splitter.split(np.zeros((len(questions), 1)), labels, groups)):
        buckets[indices] = fold
    fit, choose, test = buckets == 0, buckets == 1, buckets == 2
    for name, mask in (('fit', fit), ('threshold', choose), ('test', test)):
        if len(set(labels[mask])) < 2:
            return {'enabled': False, 'status': 'insufficient_grouped_split', 'partition': name,
                    'target_precision': target, 'phase3_review_required': True}
    platt = LogisticRegression(C=1.0, random_state=0).fit(np.asarray(scores)[fit, None], labels[fit])
    probabilities = platt.predict_proba(np.asarray(scores)[:, None])[:, 1]
    candidates = []
    for threshold in sorted(set(probabilities[choose])):
        accepted = choose & (probabilities >= threshold)
        count, successes = int(accepted.sum()), int(labels[accepted].sum())
        if count >= 5 and successes / count >= target:
            candidates.append((count, float(threshold)))
    threshold = max(candidates)[1] if candidates else 2.0
    accepted = test & (probabilities >= threshold)
    count, successes = int(accepted.sum()), int(labels[accepted].sum())
    return {'enabled': False, 'status': 'research_only' if candidates else 'no_supported_threshold',
            'phase3_review_required': True, 'target_precision': target, 'threshold': threshold,
            'target': 'corpus-answerability, not generated-answer correctness',
            'split_method': 'StratifiedGroupKFold(3, shuffle=True, random_state=0); whole topics',
            'threshold_selection': 'empirical precision target; uncertainty reported separately',
            'platt_coefficient': float(platt.coef_[0, 0]), 'platt_intercept': float(platt.intercept_[0]),
            'split_counts': {'fit': int(fit.sum()), 'threshold': int(choose.sum()), 'test': int(test.sum())},
            'test_accepted': count, 'test_correct': successes,
            'test_precision': successes / count if count else None,
            'test_precision_wilson_lower_95': wilson_lower(successes, count),
            'test_auc': float(roc_auc_score(labels[test], probabilities[test]))}


def steering_summary(alphas, projections):
    rho = float(spearmanr(alphas, projections).statistic) if np.ptp(projections) else float('nan')
    return {'spearman': rho if math.isfinite(rho) else None,
            'monotone_readout': bool(math.isfinite(rho) and rho > .8),
            'semantic_causal_claim': False, 'human_text_review_required': True}
