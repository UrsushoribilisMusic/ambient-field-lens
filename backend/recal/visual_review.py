"""Human-label release checks only. No model/provider imports or scoring path."""
import hashlib,json
from pathlib import Path

CHECKS={'paper_position','footprint_inside_paper','pen_contact','drawing_has_no_blank_areas'}


def digest_manifest(manifest):
    return hashlib.sha256(json.dumps(manifest,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def validate_draft(manifest):
    pairs=manifest['pairs']
    if len(pairs)!=4 or {p['check'] for p in pairs}!=CHECKS:raise ValueError('Four unique requested checks required')
    if manifest.get('scoring_enabled') or manifest.get('gpu_authorized'):raise ValueError('Authoring packet cannot authorize scoring')
    families={};images={}
    for p in pairs:
        if p['fold'] not in ('fit','validation','test') or not p['question'].strip() or not p['candidate'].strip():raise ValueError('Missing frozen prompt/fold')
        if p.get('manual_context')!='':raise ValueError('Manual text must not answer image-only task')
        families.setdefault(p['capture_group'],set()).add(p['fold'])
        ms=p['members']
        if len(ms)!=2 or ms[0]['id']==ms[1]['id'] or ms[0]['image_sha256']==ms[1]['image_sha256']:raise ValueError('Distinct paired image conditions required')
        if len({(m['width'],m['height']) for m in ms})!=1:raise ValueError('Paired image geometry mismatch')
        for m in ms:
            if not m['archival'] or m['fresh_live_evidence'] or m.get('human_label') is not None:raise ValueError('Draft cannot claim live or human-labelled evidence')
            if m['model_visible_metadata']:raise ValueError('Scene/condition metadata cannot be passed to model')
            images.setdefault(m['image_sha256'],set()).add(p['fold'])
        if p.get('visual_target') and not p['visual_target']['same_for_both_members']:raise ValueError('Target must be identical across conditions')
    if any(len(f)>1 for f in families.values()) or any(len(f)>1 for f in images.values()):raise ValueError('Source-family/image fold leakage')
    if {p['fold'] for p in pairs}!={'fit','validation','test'}:raise ValueError('All three declared folds required')
    return True


def validate_human_review(manifest,review):
    validate_draft(manifest)
    if review.get('manifest_digest')!=digest_manifest(manifest):raise ValueError('Review is not bound to this draft')
    name=review.get('reviewer_name','').strip()
    if 'miguel' not in name.lower() or review.get('independently_reviewed') is not True:raise ValueError('Miguel must supply his own independent review')
    if review.get('footprint_scope_approved') is not True:raise ValueError('Explicit image-space footprint target needs review')
    entries=review.get('pairs',[])
    if len(entries)!=4 or len({r['id'] for r in entries})!=4:raise ValueError('Every pair must be reviewed exactly once')
    by_id={r['id']:r for r in entries}
    for p in manifest['pairs']:
        r=by_id.get(p['id'])
        if r is None:raise ValueError('Missing pair review')
        if r.get('manual_only_answerable') is not False:raise ValueError('Reject manual-only or unresolved answerability')
        if r.get('image_evidence_sufficient') is not True:raise ValueError('Insufficient image evidence; pair must be rejected/replaced')
        labels=r.get('member_labels',{})
        if (not isinstance(labels,dict) or set(labels)!={m['id'] for m in p['members']}
            or list(labels.values()).count('pass')!=1 or list(labels.values()).count('fail')!=1):
            raise ValueError('Need one human-reviewed pass/fail; unknown/rejected pairs block whole set')
    # This is a reviewed label artifact only. There is deliberately no GPU launch,
    # model score, readiness verdict or /assist integration here.
    return {'status':'labels_reviewed_for_offline_planning','reviewer_name':name,
        'manifest_digest':digest_manifest(manifest),'pair_count':4,'gpu_launched':False,'live_green_enabled':False}
