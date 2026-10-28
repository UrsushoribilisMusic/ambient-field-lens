"""Fresh paired, grouped comparison; never exposes a product verdict."""
import numpy as np
from scipy.stats import binomtest
from sklearn.metrics import roc_auc_score


def validate_records(records):
    if len(records) != 36 or len({r['id'] for r in records}) != 36:
        raise ValueError('Frozen pilot requires 36 unique records')
    pairs = {}
    for r in records:
        if r['fold'] not in ('fit', 'validation', 'test') or type(r['supported']) is not bool:
            raise ValueError('Invalid fold or label')
        pairs.setdefault(r['pair_id'], []).append(r)
    groups = {}
    for pair in pairs.values():
        if len(pair) != 2 or {p['supported'] for p in pair} != {False, True}:
            raise ValueError('Pair must contain both conditions')
        for key in ('question', 'candidate', 'group', 'fold') + (('frame_sha256',) if any('frame_sha256' in p for p in pair) else ()):
            if len({p[key] for p in pair}) != 1: raise ValueError('Pair mismatch: '+key)
        if pair[0]['text'] == pair[1]['text']: raise ValueError('No evidence intervention')
        g=pair[0]['group'];groups.setdefault(g,set()).add(pair[0]['fold'])
    if len(groups)!=6 or any(len(v)!=1 for v in groups.values()):
        raise ValueError('Topic leakage or missing groups')
    for fold in ('fit','validation','test'):
        if sum(r['fold']==fold for r in records)!=12: raise ValueError('Unbalanced frozen folds')
    return pairs


def fit_score(features, records):
    x=np.asarray(features,dtype=np.float64)
    if not np.isfinite(x).all():raise ValueError('Nonfinite feature')
    fit=np.array([r['fold']=='fit' for r in records]); y=np.array([r['supported'] for r in records])
    direction=x[fit&y].mean(0)-x[fit&~y].mean(0)
    norm=np.linalg.norm(direction)
    if norm <= 1e-12: raise ValueError('Degenerate direction')
    direction/=norm
    return (x@direction)/np.maximum(np.linalg.norm(x,axis=1),1e-12),direction


def choose_layer(scores, records):
    val=np.array([r['fold']=='validation' for r in records]); y=np.array([r['supported'] for r in records])
    aucs=[float(roc_auc_score(y[val],scores[val,l])) for l in range(scores.shape[1])]
    return int(np.argmax(aucs)),aucs


def summarize(scores, records):
    pairs=validate_records(records);scores=np.asarray(scores)
    if scores.shape[0]!=len(records) or not np.isfinite(scores).all():raise ValueError('Invalid scores')
    layer,aucs=choose_layer(scores,records);s=scores[:,layer]
    y=np.array([r['supported'] for r in records]); test=np.array([r['fold']=='test' for r in records])
    margins=[]
    for pair in pairs.values():
        if pair[0]['fold']!='test':continue
        pos=next(r for r in pair if r['supported']);neg=next(r for r in pair if not r['supported'])
        a=records.index(pos);b=records.index(neg)
        margins.append({'pair_id':pos['pair_id'],'group':pos['group'],'positive':float(s[a]),'negative':float(s[b]),'margin':float(s[a]-s[b])})
    wins=sum(m['margin']>0 for m in margins);ties=sum(m['margin']==0 for m in margins)
    topic_margins={g:float(np.mean([m['margin'] for m in margins if m['group']==g])) for g in sorted({m['group'] for m in margins})}
    topic_wins=sum(v>0 for v in topic_margins.values());topic_n=sum(v!=0 for v in topic_margins.values())
    # Entire test topic clusters resampled, not independent rows/pair members.
    rng=np.random.default_rng(31);gs=sorted({r['group'] for r in records if r['fold']=='test'});boot=[]
    for _ in range(1000):
        sample=rng.choice(gs,len(gs),replace=True)
        ix=np.concatenate([np.flatnonzero([r['fold']=='test' and r['group']==g for r in records]) for g in sample])
        boot.append(roc_auc_score(y[ix],s[ix]))
    return {'selected_layer':layer,'validation_auc_per_layer':aucs,'validation_auc':aucs[layer],
            'test_auc':float(roc_auc_score(y[test],s[test])),
            'test_auc_group_bootstrap_95':np.quantile(boot,[.025,.975]).tolist(),
            'test_pairs':len(margins),'test_records':int(test.sum()),'test_topic_clusters':len(gs),
            'pair_accuracy':(wins+.5*ties)/len(margins),'pair_wins':wins,'pair_ties':ties,
            'paired_sign_test_two_sided_p':float(binomtest(wins,len(margins)-ties).pvalue) if len(margins)>ties else 1.,
            'pair_sign_test_caveat':'Unadjusted diagnostic; paraphrases within topics are correlated',
            'topic_mean_margins':topic_margins,
            'topic_sign_test_two_sided_p':float(binomtest(topic_wins,topic_n).pvalue) if topic_n else 1.,
            'test_pair_margins':margins,'enabled':False,'target':'support present in supplied manual context; not generated answer correctness',
            'limitations':['Tiny pilot: only two test topic clusters','Teacher-forced fixed candidate; no generated-answer correctness labels','Image inclusion is recorded in image_input; camera robustness and physical readiness remain untested']}
