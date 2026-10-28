"""Fixed-layer prompt expansion, inheriting only the exact human-reviewed facts."""
import copy
import numpy as np
from scipy.stats import binomtest
from sklearn.metrics import roc_auc_score

QUESTIONS={
 'locking':[
  'How is simultaneous execution of drawing jobs prevented?',
  'What stops a second drawing job from running alongside the first?',
  'What does the documented job lock enforce?',
  'Which control keeps execution to one drawing job?',
  'How does job orchestration stop overlapping drawing jobs?',
  'Which lock is used to prevent concurrent job execution?',
  'What mechanism serializes drawing jobs?',
  'What ensures two submitted drawing jobs cannot execute together?',
  'Which documented safeguard prevents drawing jobs from overlapping?',
  'What is the purpose of the robot_ross_running.lock file during jobs?',
  'How is the one-job-at-a-time rule enforced?',
  'What prevents parallel drawing execution?'],
 'narration':[
  'Which drawing option suppresses spoken narration?',
  'How can a drawing be requested without voice commentary?',
  'What command-line flag disables narration for a drawing?',
  'Which option should I use when I want the arm to draw silently?',
  'How does the documented drawing command omit narration?',
  'What flag makes a drawing run without speech?',
  'Which argument requests drawing with no spoken commentary?',
  'How do I request a drawing job with the narrator turned off?',
  'What documented flag produces a silent draw?',
  'Which option leaves out the voice narration during drawing?',
  'How can voice output be disabled for the requested drawing job?',
  'What drawing flag should be supplied to avoid narration?']}


def expand(base):
    records=[]
    for r in base['records']:
        records.append(dict(r,parent_id=r['id'],partition='legacy'))
    for group,questions in QUESTIONS.items():
        parents=[r for r in base['records'] if r['group']==group]
        pairs=list(dict.fromkeys(r['pair_id'] for r in parents))
        assert len(pairs)==3
        for i,q in enumerate(questions):
            for parent in [r for r in parents if r['pair_id']==pairs[i%3]]:
                pair=f'{group}-expanded-{i:02}'
                r=dict(parent,id=pair+('-support' if parent['supported'] else '-control'),pair_id=pair,
                    parent_id=parent['id'],partition='novel_wording',question=q,
                    text=parent['text'].rsplit('\nQuestion: ',1)[0]+'\nQuestion: '+q)
                records.append(r)
    validate(records,base['records']);return records


def validate(records,base):
    if len(records)!=84 or len({r['id'] for r in records})!=84:
        raise ValueError('Exactly36 original and48 expanded records required')
    original={r['id']:r for r in base}
    if len(original)!=36:raise ValueError('Reviewed base must contain36 records')
    legacy=[r for r in records if r['partition']=='legacy']
    if {r['id'] for r in legacy}!=set(original):raise ValueError('Original controls changed')
    pairs={}
    for r in records:
        parent=original[r['parent_id']]
        if r['partition']=='legacy':
            if any(r[k]!=v for k,v in parent.items()):raise ValueError('Legacy record changed')
        elif r['partition']=='novel_wording':
            if r['group'] not in QUESTIONS or r['fold']!='test':raise ValueError('Only held-out wording may expand')
            if r['question'] not in QUESTIONS[r['group']]:raise ValueError('Undeclared question')
            for key in ('candidate','group','fold','supported','frame_sha256','frame_asset'):
                if r[key]!=parent[key]:raise ValueError('Frozen label inheritance violated: '+key)
            expected=parent['text'].rsplit('\nQuestion: ',1)[0]+'\nQuestion: '+r['question']
            if r['text']!=expected:raise ValueError('Reviewed context changed')
        else:raise ValueError('Unknown partition')
        pairs.setdefault(r['pair_id'],[]).append(r)
    if len(pairs)!=42:raise ValueError('Expected42 pairs')
    for p in pairs.values():
        if len(p)!=2 or {r['supported'] for r in p}!={True,False}:raise ValueError('Pair incomplete')
        for key in ('question','candidate','group','fold','frame_sha256','partition'):
            if p[0][key]!=p[1][key]:raise ValueError('Pair mismatch: '+key)
    novel=[r for r in records if r['partition']=='novel_wording']
    if len(novel)!=48:raise ValueError('Expected48 new held-out records')
    for group,qs in QUESTIONS.items():
        actual=[r['question'] for r in novel if r['group']==group]
        if sorted(actual)!=sorted(qs*2):raise ValueError('New wording coverage changed')
    if {f:sum(r['fold']==f for r in records) for f in ('fit','validation','test')}!={'fit':12,'validation':12,'test':60}:
        raise ValueError('Fixed folds changed')
    return pairs


def cohort(scores,records,partition):
    ix=[i for i,r in enumerate(records) if r['fold']=='test' and r['partition']==partition]
    y=np.array([r['supported'] for r in records]);s=np.asarray(scores)
    if not np.isfinite(s).all():raise ValueError('Nonfinite scores')
    pairs={}
    for i in ix:pairs.setdefault(records[i]['pair_id'],{})[records[i]['supported']]=i
    margins=[]
    for name,p in pairs.items():
        a,b=p[True],p[False]
        margins.append(dict(pair_id=name,group=records[a]['group'],positive=float(s[a]),negative=float(s[b]),margin=float(s[a]-s[b])))
    gs=sorted({m['group'] for m in margins});means={g:float(np.mean([m['margin'] for m in margins if m['group']==g])) for g in gs}
    n=sum(v!=0 for v in means.values());wins=sum(v>0 for v in means.values())
    correct=sum(m['margin']>0 for m in margins);ties=sum(m['margin']==0 for m in margins)
    return dict(auc=float(roc_auc_score(y[ix],s[ix])),pairs=len(pairs),records=len(ix),topic_clusters=len(gs),
       pair_accuracy=(correct+.5*ties)/len(pairs),pair_wins=correct,pair_ties=ties,
       topic_mean_margins=means,topic_sign_test_two_sided_p=float(binomtest(wins,n).pvalue) if n else 1.,
       pair_margins=margins)


def report(scores,records,layer):
    val=[i for i,r in enumerate(records) if r['fold']=='validation']
    return dict(fixed_layer=layer,layer_selected_in='Prior round, before expanded wording scores; no reselection',
       validation_auc=float(roc_auc_score([records[i]['supported'] for i in val],np.asarray(scores)[val])),
       novel_wording_test=cohort(scores,records,'novel_wording'),legacy_test_control=cohort(scores,records,'legacy'),
       enabled=False,target='Support present in exact reviewed manual context; not answer correctness',
       limitations=['Only TWO held-out fact/topic clusters; new paraphrases are not independent tasks',
         'Candidate, context and frame combinations unchanged from Miguel-reviewed set',
         'Same camera frames recur across folds; no visual-grounding claim',
         'No new labels: evidence-candidate labels inherited only under strict identity checks'])


def prefill_inputs(encoded,start):
    full=int(encoded['input_ids'].shape[-1])
    if not 0<start<full:raise ValueError('Actual pre-candidate boundary required')
    out=dict(encoded)
    for key in ('input_ids','attention_mask','token_type_ids','position_ids'):
        if key in out:
            if int(out[key].shape[-1])!=full:raise ValueError('Unaligned token tensor: '+key)
            out[key]=out[key][...,:start]
    return out
