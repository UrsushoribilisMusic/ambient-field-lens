"""Frozen trajectory selection; pure CPU analysis, never a product verdict."""
import numpy as np
from paired_analysis import summarize

PRIOR_ENDPOINT_AUC = 0.888888888888889
POINTS = ('early', 'mid', 'late')
ALL_POINTS = ('true_prefill',) + POINTS


def candidate_start(tokenizer, token_ids, candidate):
    """Find the shortest exact decoded candidate suffix; no nominal token offset."""
    if not candidate.strip():
        raise ValueError('Empty candidate')
    for start in range(len(token_ids) - 1, max(-1, len(token_ids) - 257), -1):
        decoded = tokenizer.decode(token_ids[start:], skip_special_tokens=True)
        if decoded.strip() == candidate.strip():
            if start < 1:
                raise ValueError('No pre-candidate control position')
            return start
    raise ValueError('Candidate is not an exact suffix within 256 tokens')


def trajectory_indices(n):
    if n < 3:
        raise ValueError('At least three candidate tokens required')
    # Slice includes the preceding token at index zero; actual token index k is
    # the residual AFTER consuming k teacher-forced candidate tokens.
    return dict(true_prefill=0, early=1, mid=(n + 1)//2, late=n)


def summarize_trajectory(scores, records):
    if set(scores) != set(ALL_POINTS):
        raise ValueError('All preregistered trajectory points required')
    reports = {p: summarize(scores[p], records) for p in ALL_POINTS}
    # Validation only, earliest trajectory point then smallest layer on ties.
    selected = max(POINTS, key=lambda p: reports[p]['validation_auc'])
    auc = reports[selected]['test_auc']
    return {
        'points': reports, 'selected_point': selected,
        'selected_layer': reports[selected]['selected_layer'],
        'selection_rule': 'validation AUROC only; early/mid/late tie order, lowest layer on ties',
        'selected_test_auc': auc, 'prior_endpoint_auc': PRIOR_ENDPOINT_AUC,
        'heldout_delta_vs_prior': auc - PRIOR_ENDPOINT_AUC,
        'beats_prior': bool(auc > PRIOR_ENDPOINT_AUC + 1e-12),
        'decision': 'retain_for_review' if auc > PRIOR_ENDPOINT_AUC + 1e-12 else 'retire',
        'enabled': False,
        'scope': 'Teacher-forced fixed-candidate support discrimination, not free generation or validated visual grounding',
    }
