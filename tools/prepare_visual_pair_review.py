#!/usr/bin/env python3
from pathlib import Path
from PIL import Image
import json,hashlib,subprocess,datetime
repo=Path(__file__).resolve().parents[1]
archive=Path.home()/'Movies/Ambient-Field-Lens/2026-10-27/drawing-readiness'
root=Path.home()/'Movies/Ambient-Field-Lens/2026-10-28/visual-grounding-review'
(root/'frames').mkdir(parents=True,exist_ok=True)
if (root/'human-review-frozen.json').exists():raise ValueError('Labels frozen; do not reauthor this packet')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def asset(src,name,crop,seconds=None):
    source=archive/src;source_hash=sha(source)
    if seconds is not None:
        raw=root/'frames'/f'{name}-full.jpg'
        subprocess.run(['ffmpeg','-y','-v','error','-ss',str(seconds),'-i',str(source),'-frames:v','1',str(raw)],check=True)
    else:raw=source
    im=Image.open(raw).convert('RGB');w,h=im.size
    x0,y0,x1,y1=crop;assert 0<=x0<x1<=w and 0<=y0<y1<=h
    target=root/'frames'/f'{name}.png';im.crop(crop).save(target)
    return {'image_asset':str(target),'image_sha256':sha(target),'width':x1-x0,'height':y1-y0,
      'archived_source':str(source),'source_sha256':source_hash,'source_frame_sha256':sha(raw),
      'source_dimensions':[w,h],'source_seconds':seconds,'crop_xyxy':crop,
      'transformation':'Native-pixel crop only; no retouching, synthesis, sharpening or inferred content',
      'archival':True,'fresh_live_evidence':False}

paper_before=asset('S28-before-move-t000.jpg','placement-before',[220,280,650,505])
paper_after=asset('S28-paper-outside-fixed-drawing-position.jpg','placement-after',[220,280,650,505])
contact_low=asset('S06-calibration-process.mp4','contact-low',[170,260,370,410],30)
contact_high=asset('S06-calibration-process.mp4','contact-high',[170,260,370,410],60)
outline_gap=asset('S19-square-repeat-result.jpg','outline-gap',[1050,1170,1430,1370])
outline_complete=asset('S22-square-post-fix-result.jpg','outline-complete',[1050,1170,1430,1370])
points=[[130,122],[157,103],[194,117],[165,138]]
neutral='Use only the supplied image and explicitly provided visual target. Report UNKNOWN if the requested state is not visually resolvable. Manual instructions describe norms, not the state of this archived scene.'

def member(code,im,proposal):return dict(id=code,**im,author_proposed_label=proposal,human_label=None)
pairs=[
 {'id':'VG01','check':'paper_position','capture_group':'paper-displacement-S28','fold':'fit',
  'question':'Is the white drawing paper positioned beneath the robot pen tip, rather than leaving the tip above bare desk?',
  'candidate':'The white drawing paper is positioned under the pen tip.',
  'scope':'Qualitative visible paper placement relative to the fixed tip; no metric robot registration or dimensional pass.',
  'members':[member('VG01-A',paper_after,'fail'),member('VG01-B',paper_before,'pass')],
  'author_note':'The same camera/pen position is shown before and after the paper/book moves. Room/person/monitor are cropped out.'},
 {'id':'VG02','check':'footprint_inside_paper','capture_group':'paper-displacement-S28','fold':'fit',
  'question':'The cyan quadrilateral is a supplied proposed footprint in image coordinates. Does the entire footprint lie inside the white drawing paper boundary, rather than on the book or desk?',
  'candidate':'The entire supplied footprint is contained by the white drawing paper.',
  'scope':'Image-space containment of an explicitly supplied visual target ONLY; not an accepted robot-coordinate plan or recovered calibration.',
  'visual_target':{'kind':'provided_svg_polygon','coordinate_frame':'cropped_model_image','points_xy':points,'stroke':'#00d9e8','stroke_width_pixels':2,
    'same_for_both_members':True,'origin':'Hand-traced reference quadrilateral around the visible outline in archived before frame; fixed pixel coordinates in both images, not a projection from robot coordinates.',
    'requires_human_scope_approval':True},
  'members':[member('VG02-A',paper_before,'pass'),member('VG02-B',paper_after,'fail')],
  'author_note':'Raw frames contain no visible future robot footprint. This supplied cyan target makes the question visually defined. Reject this pair if the requested target must instead be a registered physical toolpath. No nominal mapping is invented.'},
 {'id':'VG03','check':'pen_contact','capture_group':'contact-calibration-S06','fold':'validation',
  'question':'Is the pen tip visibly touching the white drawing paper in this frame? If the gap or contact cannot be resolved, answer UNKNOWN.',
  'candidate':'The pen tip is visibly in contact with the drawing paper.',
  'scope':'Visible tip/surface relationship only; not contact force, controller readiness, successful writing or a substitution of pen presence for contact.',
  'members':[member('VG03-A',contact_low,'pass'),member('VG03-B',contact_high,'fail')],
  'author_note':'Same archived calibration clip,30s and60s. Proposed contact at30s and visible gap at60s need Miguel confirmation at native-pixel detail; do not use controller flags or the action name as the answer.'},
 {'id':'VG04','check':'drawing_has_no_blank_areas','capture_group':'outline-results-S19-S22','fold':'test',
  'question':'Are the visible lower and right-hand edge strokes of the small central rectangular outline present, rather than missing? The unfilled interior is intentional; ignore handwritten labels.',
  'candidate':'The visible lower and right-hand edges of the intended rectangular outline are drawn.',
  'scope':'Missing requested outline strokes, not solid-fill coverage, dimensional accuracy or an assertion about occluded portions of the drawing.',
  'members':[member('VG04-A',outline_gap,'fail'),member('VG04-B',outline_complete,'pass')],
  'author_note':'The failed-result crop has missing right/lower strokes; the later result shows those edges. Other marks are pre-existing labels. Pen pose also differs, a nuisance correlation to retain in reporting, not a causal contact validation.'}]
for pair in pairs:
 pair.update(instruction=neutral,manual_context='',human_review_status='pending',text_only_expected='unknown',manual_only_answerable=None)
 for m in pair['members']:
  m['model_visible_metadata']=[]
  if pair.get('visual_target'):
   target=pair['visual_target'];points_attr=' '.join(f'{x},{y}' for x,y in target['points_xy'])
   image_name=Path(m['image_asset']).name
   svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{m["width"]}" height="{m["height"]}" viewBox="0 0 {m["width"]} {m["height"]}"><image href="{image_name}" width="{m["width"]}" height="{m["height"]}"/><polygon points="{points_attr}" fill="none" stroke="#00d9e8" stroke-width="2"/></svg>'
   p=root/'frames'/f'{m["id"]}-provided-target.svg';p.write_text(svg);m['review_svg_asset']=str(p);m['review_svg_sha256']=sha(p)
manifest={'schema':'visual-grounding-review-v1','status':'human_review_pending','origin_main':'9e55904',
 'authored_by':'Codi (agent), proposed labels only; no human approval claimed','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'role':'Four-pair seed review, not a meaningful accuracy/calibration benchmark',
 'human_reviewer':None,'scoring_enabled':False,'gpu_authorized':False,'new_filming':False,
 'image_required':True,'labels_frozen':False,'pairs':pairs,
 'fold_policy':'Same capture family stays in one fold. S28 placement/target pairs fit; S06 contact validation; S19/S22 outline results test. One test pair only. Same rig/physical marks recur across captures; no independent-view robustness claim.',
 'release_requirements':['Miguel independently reviews every member of every pair','Exactly one visually supported PASS and one FAIL per pair; unresolved/UNKNOWN/rejected pair blocks whole-set scoring','Each pair must be image-dependent and not answerable from manual text alone','Footprint target is explicitly approved as image-space only, or pair is rejected/replaced','Source/image/target hashes and frozen folds remain unchanged; no label/state metadata in model prompts'],
 'excluded_text_questions':['Must paper be positioned correctly before drawing?','Should the pen touch the paper?','Does a lock prevent concurrent jobs?'],
 'physical_boundary':'No result accepts robot registration, paper-to-robot coordinates, contact force, calibration or green instructions. /assist stays default-deny; archived frames are not live evidence.'}
manifest.update(pair_count=4,image_condition_count=8,unique_native_crops=len({x['image_sha256'] for q in pairs for x in q['members']}))
p=root/'manifest.json';p.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
(repo/'docs/verification/visual-pair-manifest-2026-10-28.json').write_text(p.read_text())
print('Authored4 pairs /8 conditions; source photos remain private; no calls or scores')
print('Manifest SHA',sha(p))
