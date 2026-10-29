"""Measured camera/robot linkage and numeric paper corrections. No motion IO."""
import hashlib
import itertools
import json
import math
import numpy as np
from providers.clearance import estimate_surface_mapping,containment_clearance
from readiness.geometry import Correspondence,_convex,_within_support,_hull,project


def _affine_link(record):
    if record.get('units')!='mm' or record.get('physically_measured') is not True:
        raise ValueError('physical_robot_link_measurements_required')
    fit=record['fit'];held=record['validation']
    if len(fit)<3 or len(held)<3:raise ValueError('robot_link_requires_three_fit_and_three_independent_checks')
    points=fit+held
    if len({tuple(p['robot_mm']) for p in points})!=len(points):raise ValueError('robot_link_coordinate_reuse')
    if len({p['id'] for p in points})!=len(points):raise ValueError('robot_link_point_reuse')
    x=np.array([p['robot_mm'] for p in fit],float);y=np.array([p['plane_mm'] for p in fit],float)
    design=np.column_stack((x,np.ones(len(x))))
    if np.linalg.matrix_rank(design)!=3 or not np.isfinite(design).all() or not np.isfinite(y).all():
        raise ValueError('invalid_robot_link')
    beta=np.linalg.lstsq(design,y,rcond=None)[0]
    matrix=np.vstack((beta.T,[0.,0.,1.]))
    if abs(np.linalg.det(matrix))<1e-9:raise ValueError('singular_robot_link')
    actual=np.array([p['plane_mm'] for p in held],float)
    error=float(np.linalg.norm(project(matrix,[p['robot_mm'] for p in held])-actual,axis=1).max())
    if not math.isfinite(error):raise ValueError('robot_link_validation_invalid')
    support=_hull(x.tolist())
    return matrix,error,support


def paper_translation(paper_vertices_mm,footprint_vertices_mm,margin_mm,robot_to_plane):
    """Minimum-norm translation of convex paper; signed offsets in robot axes.

    Proposal only: recheck the actual mask after the human moves the paper.
    An impossible fit is not converted into an instruction to move the robot.
    """
    paper=_convex(paper_vertices_mm);footprint=_convex(footprint_vertices_mm)
    if not math.isfinite(margin_mm) or margin_mm<0:raise ValueError('invalid_margin')
    normals=[];offsets=[]
    for i,start in enumerate(paper):
        edge=paper[(i+1)%len(paper)]-start
        n=np.array([edge[1],-edge[0]])/np.linalg.norm(edge)
        normals.append(n);offsets.append(float((footprint@n).max()-start@n+margin_mm))
    a=np.array(normals);b=np.array(offsets)
    candidates=[np.zeros(2)]+[b[i]*a[i] for i in range(len(a))]
    for i,j in itertools.combinations(range(len(a)),2):
        if abs(np.linalg.det(a[[i,j]]))>1e-9:candidates.append(np.linalg.solve(a[[i,j]],b[[i,j]]))
    feasible=[p for p in candidates if np.all(a@p>=b-1e-8)]
    result={'edge_signed_deficit_mm':b.tolist(),'paper_shift_plane_mm':None,'paper_shift_robot_mm':None,
            'correction':None,'source':'deterministic_measured_geometry','step':None}
    if not feasible:return {**result,'reason':'no_paper_translation_can_contain_footprint'}
    shift=min(feasible,key=lambda p:float(p@p))
    linear=np.asarray(robot_to_plane,float)[:2,:2]
    robot_shift=np.linalg.solve(linear,shift)
    result.update(paper_shift_plane_mm=shift.tolist(),paper_shift_robot_mm=robot_shift.tolist(),
                  reason='measured_translation_proposal_requires_recheck')
    if np.linalg.norm(shift)>1e-8:
        result['correction']=f'Move the paper {robot_shift[0]:+.3f} mm in X and {robot_shift[1]:+.3f} mm in Y (robot axes), then recheck.'
    return result


def paper_boundary_from_mask(paper,matrix,allowed_deviation_mm):
    """Conservative convex outline from this mask only; holes/concavity refuse guidance."""
    from scipy.ndimage import binary_fill_holes
    from scipy.spatial import ConvexHull
    if paper.width*paper.height>4_194_304 or len(paper.pixels)>1_000_000:return None
    bitmap=np.zeros((paper.height,paper.width),bool)
    for x,y in paper.pixels:
        if not (0<=x<paper.width and 0<=y<paper.height):return None
        bitmap[y,x]=True
    if not np.array_equal(binary_fill_holes(bitmap),bitmap):return None
    boundary=[(x+.5,y+.5) for x,y in paper.pixels if any((x+dx,y+dy) not in paper.pixels
                for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)))]
    points=project(np.linalg.inv(matrix),boundary)
    hull=ConvexHull(points);vertices=_convex(points[hull.vertices])
    if len(vertices)>64:return None
    # Large inward dents cannot be erased by a convex-hull approximation.
    distances=[]
    for i,a in enumerate(vertices):
        edge=vertices[(i+1)%len(vertices)]-a
        inward=np.array([-edge[1],edge[0]])/np.linalg.norm(edge)
        distances.append((points-a)@inward)
    if float(np.array(distances).min(axis=0).max())>allowed_deviation_mm:return None
    return vertices


def compute(frame,paper,record,robot_vertices_mm,*,now):
    """Call with server-owned measured artifact, never user/model-supplied geometry.

    Record must bind current camera/pose/frame and fixed coplanar fiducials.
    Shift guidance derives its boundary only from this frame's mask via the
    reviewed extractor; boundary vertices are never accepted from an LLM.
    """
    unknown={'state':'unknown','reason':'measured_geometry_unavailable','frame_sha256':frame.sha256,
             'clearance_mm':None,'registration_error_mm':None,'reading_uncertainty_mm':None,
             'signed_offsets':None,'correction':None,'step':None,'verdict':'verify'}
    try:
        if (not isinstance(record,dict) or record.get('reviewed_by_operator') is not True
                or record.get('units')!='mm'
                or record.get('markers_fixed_to_workspace') is not True
                or record.get('markers_coplanar_with_drawing_surface') is not True
                or record.get('camera')!=frame.camera or record.get('rig')!=frame.rig
                or record.get('surface_pose')!=frame.surface_pose
                or record.get('frame_sha256')!=frame.sha256
                or record.get('image_size')!=[frame.width,frame.height]
                or not 0<=now-frame.captured_at<=5):return unknown
        allowance=record.get('tool_repeatability_allowance_mm')
        if type(allowance) not in (int,float) or not math.isfinite(allowance) or allowance<0:return unknown
        hashes=record.get('measurement_sha256',[])
        import re
        if not hashes or any(not isinstance(h,str) or not re.fullmatch('[a-f0-9]{64}',h) for h in hashes):return unknown
        markers=record['markers'];fit=[p for p in markers if p['role']=='fit'];held=[p for p in markers if p['role']=='validation']
        if len({p['id'] for p in markers})!=len(markers):return unknown
        reg=estimate_surface_mapping([Correspondence(tuple(p['plane_mm']),tuple(p['image_px'])) for p in fit],
                                     [Correspondence(tuple(p['plane_mm']),tuple(p['image_px'])) for p in held])
        robot,error,support=_affine_link(record['robot_link'])
        vertices=_convex(robot_vertices_mm)
        if not _within_support(vertices,support):return {**unknown,'reason':'footprint_outside_measured_robot_support'}
        footprint=project(robot,vertices)
        if not _within_support(footprint,reg['support_plane_mm']):return {**unknown,'reason':'footprint_outside_marker_support'}
        result=containment_clearance(paper,footprint,reg['matrix'],frame_sha256=frame.sha256,
            registration_error_mm=reg['registration_error_mm'],reading_uncertainty_mm=record.get('reading_uncertainty_mm'),
            robot_allowance_mm=error+record['tool_repeatability_allowance_mm'],geometry_reviewed=True)
        result.update(verdict='verify',correction=None,signed_offsets=None,
                      robot_link_validation_error_mm=error,
                      measurement_sha256=hashes,record_sha256=hashlib.sha256(json.dumps(record,sort_keys=True,allow_nan=False).encode()).hexdigest())
        if (result['state']=='fail' and record.get('boundary_extractor_reviewed') is True
                and result['required_clearance_mm'] is not None):
            boundary=paper_boundary_from_mask(paper,reg['matrix'],result['reading_uncertainty_mm']+result['sampling_uncertainty_mm'])
            if boundary is not None:
                proposal=paper_translation(boundary,footprint,result['required_clearance_mm'],robot)
                result.update(signed_offsets=proposal,correction=proposal['correction'])
        return result
    except (ValueError,TypeError,KeyError,np.linalg.LinAlgError):return unknown
