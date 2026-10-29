"""Read-only local Ross evidence. Flags/logs are not physical calibration proof."""
from dataclasses import asdict
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import time
import urllib.request
from generation.wording import private_write,NoRedirect
from readiness.checks import Frame

DEFAULT_ROOT=Path.home()/'projects/robot-ross-mac'


def file_evidence(path,limit=65536,tail=False):
    """Stable bounded snapshot; retain hashes, never arbitrary file contents in output."""
    path=Path(path)
    try:
        if path.is_symlink():return {'available':False,'reason':'symlink_rejected'},None
        before=path.stat()
        with path.open('rb') as stream:
            if tail:stream.seek(max(0,before.st_size-limit))
            elif before.st_size>limit:return {'available':False,'reason':'file_size_limit'},None
            raw=stream.read(limit+1)
        after=path.stat()
        fields=('st_dev','st_ino','st_size','st_mtime_ns')
        if len(raw)>limit or any(getattr(before,k)!=getattr(after,k) for k in fields):
            return {'available':False,'reason':'file_changed_during_read'},None
        return {'available':True,'sha256':hashlib.sha256(raw).hexdigest(),'mtime_ns':after.st_mtime_ns,
                'inode':after.st_ino,'device':after.st_dev,'size':after.st_size,'tail_only':tail},raw
    except FileNotFoundError:return {'available':False,'reason':'missing'},None
    except OSError:return {'available':False,'reason':'unreadable'},None


def process_evidence(root):
    """Inspect known local robot scripts only; never expose unrelated commands."""
    try:
        result=subprocess.run(['/bin/ps','-axo','pid=,ppid=,stat=,lstart=,command='],capture_output=True,timeout=3,text=True)
        if result.returncode:return {'available':False,'processes':[]}
        rows=[]
        for line in result.stdout.splitlines():
            parts=line.strip().split(None,8)
            if len(parts)!=9:continue
            pid,ppid,state=parts[:3];started=' '.join(parts[3:8]);command=parts[8]
            try:tokens=shlex.split(command)
            except ValueError:continue
            if not tokens or not Path(tokens[0]).name.lower().startswith('python') or '-c' in tokens or '-m' in tokens:continue
            # Only the executed Python script, never a filename in later user arguments.
            script_tokens=[t for t in tokens[1:] if not t.startswith('-')]
            if not script_tokens:continue
            matches=[]
            for token in script_tokens[:1]:
                if not token.endswith('.py') or Path(token).name not in {'control_center.py','bob_ross.py','huenit_draw.py','huenit_svg.py','huenit_write.py'}:
                    continue
                script=Path(token)
                if not script.is_absolute():
                    # Resolve relative Python script names against the process's
                    # actual cwd, never our own cwd or a matching basename.
                    cwd=subprocess.run(['/usr/sbin/lsof','-a','-p',pid,'-d','cwd','-Fn'],capture_output=True,text=True,timeout=2)
                    names=[line[1:] for line in cwd.stdout.splitlines() if line.startswith('n/')]
                    if len(names)!=1:continue
                    script=Path(names[0])/script
                resolved=script.resolve()
                if resolved.is_relative_to(root):matches.append(str(resolved))
            if matches:rows.append({'pid':int(pid),'ppid':int(ppid),'state':state,'script':Path(matches[0]).name,
                                    'zombie':state.startswith('Z'),'started_local':started,
                                    'identity_sha256':hashlib.sha256((pid+'|'+started+'|'+matches[0]).encode()).hexdigest()})
        return {'available':True,'processes':rows}
    except (OSError,subprocess.TimeoutExpired):return {'available':False,'processes':[]}


def capture(*,root=DEFAULT_ROOT,output_dir=None):
    """No serial connection, job execution, calibration reset, lock deletion or repair."""
    root=Path(root).resolve();started=time.time()
    paths={'calibration':root/'skills/huenit/calibration.json',
           'ready_flag':Path(tempfile.gettempdir())/'huenit_ready.flag',
           'job_lock':Path(tempfile.gettempdir())/'robot_ross_running.lock',
           'calibration_log':root/'skills/huenit/huenit_draw.log'}
    files={};values={}
    for key,path in paths.items():
        files[key],values[key]=file_evidence(path,tail=key=='calibration_log')
    calibration=None
    try:
        raw=json.loads(values['calibration'])
        keys=('z_up','tilt_slope','tilt_slope_x')
        if all(type(raw.get(k)) in (int,float) and math.isfinite(raw[k]) for k in keys):
            calibration={k:raw[k] for k in keys}
    except (ValueError,TypeError):pass
    status={'available':False};status_raw=None
    try:
        with urllib.request.build_opener(NoRedirect()).open('http://127.0.0.1:7870/api/status',timeout=3) as response:
            status_raw=response.read(65537)
        if len(status_raw)>65536:raise ValueError('status_size')
        data=json.loads(status_raw)
        status={'available':True,'arm_port':data.get('arm_port'),'calibration':data.get('calibration'),
                'job_running':data.get('job_running'),'showcase_running':data.get('showcase_running'),
                'last_job_status':data.get('last_job',{}).get('status') if isinstance(data.get('last_job'),dict) else None,
                'response_sha256':hashlib.sha256(status_raw).hexdigest()}
    except Exception:status_raw=None
    log=(values['calibration_log'] or b'').decode('utf-8',errors='replace')
    events=re.findall(r'CALIBRATION (START|SAVED|END|ABORTED)',log)
    snapshot={'schema':'ross-controller-evidence-v1','observed_at':time.time(),'capture_started_at':started,
              'source':'local read-only controller API and files','root_sha256':hashlib.sha256(str(root).encode()).hexdigest(),
              'files':files,'calibration_parameters':calibration,'status':status,
              'processes':process_evidence(root),'calibration_events_tail':events[-20:],
              'physical_calibration_verified':False,'controller_session_verified':False}
    if output_dir:
        folder=Path(output_dir);folder.mkdir(parents=True,exist_ok=False,mode=0o700)
        for name,raw in values.items():
            if raw is not None:private_write(folder/(name+'.raw'),raw)
        if status_raw is not None:private_write(folder/'status-response.json',status_raw)
        private_write(folder/'snapshot.json',json.dumps(snapshot,sort_keys=True,allow_nan=False).encode())
    return snapshot


def assess(frame:Frame,snapshot,binding=None,*,now=None):
    """Server-reviewed binding required; default amber. RED proposal is docs only."""
    now=time.time() if now is None else now
    reasons=[];files=snapshot['files'];status=snapshot['status'];processes=snapshot['processes']
    if not all(isinstance(t,(int,float)) and not isinstance(t,bool) and math.isfinite(t)
               for t in (now,snapshot.get('observed_at'),snapshot.get('capture_started_at'),frame.captured_at)):
        reasons.append('state_clock_invalid')
    elif not 0<=now-snapshot['observed_at']<=5 or not 0<=now-snapshot['capture_started_at']<=5 or not 0<=now-frame.captured_at<=5:
        reasons.append('state_or_frame_stale')
    if not files['job_lock']['available'] and files['job_lock'].get('reason')!='missing':
        reasons.append('job_lock_evidence_unavailable')
    if files['job_lock']['available']:
        workers=[p for p in processes['processes'] if p['script']!='control_center.py']
        if (processes['available'] and not workers and status.get('available')
                and status.get('job_running') is False and status.get('showcase_running') is False):
            reasons.append('possible_stale_job_lock_requires_operator_review')
        else:reasons.append('job_lock_present')
    if any(p['zombie'] for p in processes['processes']):reasons.append('zombie_robot_process_observed')
    if status.get('job_running') is True or status.get('showcase_running') is True:reasons.append('robot_job_active')
    if not status.get('available'):reasons.append('controller_status_unavailable')
    cal=status.get('calibration')
    if not isinstance(cal,dict) or cal.get('calibrated') is not True or cal.get('session_ready') is not True:
        reasons.append('controller_calibration_not_ready')
    if any(type(status.get(k)) is not bool for k in ('job_running','showcase_running')):
        reasons.append('controller_job_state_unresolved')
    if not files['ready_flag']['available'] or snapshot['calibration_parameters'] is None:
        reasons.append('calibration_flag_or_parameters_missing')
    if snapshot['calibration_events_tail'] and snapshot['calibration_events_tail'][-1] in ('START','ABORTED'):
        reasons.append('calibration_not_recorded_complete')
    controllers=[p for p in processes['processes'] if p['script']=='control_center.py' and not p['zombie']]
    controller_id=controllers[0]['identity_sha256'] if processes['available'] and len(controllers)==1 else None
    expected={'controller_process_sha256':controller_id,'arm_port':status.get('arm_port'),'calibration_sha256':files['calibration'].get('sha256'),
              'ready_flag_sha256':files['ready_flag'].get('sha256'),
              'ready_flag_mtime_ns':files['ready_flag'].get('mtime_ns'),
              'root_sha256':snapshot['root_sha256'],'tool':frame.tool,'surface_pose':frame.surface_pose,
              'controller_session':frame.controller_session}
    if (not isinstance(binding,dict) or binding.get('reviewed') is not True or not frame.controller_session
            or any(value is None or value=='' or binding.get(key)!=value for key,value in expected.items())):
        reasons.append('tool_surface_session_binding_unverified')
    # Even a complete file binding establishes controller state only, not pen contact.
    return {'verdict':'verify','step':None,'score':0.0,'state':'fail' if any(r in reasons for r in
            ('robot_job_active','job_lock_present','zombie_robot_process_observed','possible_stale_job_lock_requires_operator_review'))
            else 'unknown' if reasons else 'pass',
            'reasons':reasons,'correction':'',
            'frame_sha256':frame.sha256,'observed_at':snapshot['observed_at'],
            'snapshot_sha256':hashlib.sha256(json.dumps(snapshot,sort_keys=True,allow_nan=False).encode()).hexdigest(),
            'physical_calibration_verified':False,'automatic_recovery_performed':False}


def publish_once(*,robot_id,snapshot):
    """Mac-side explicit push to authenticated CPU RPC; no loop or GPU."""
    from providers.client import rpc
    return rpc('put_controller_snapshot',{'robot_id':robot_id,'snapshot':snapshot})


def fetch_published(robot_id):
    """Cloud service fetches a Mac snapshot, never reads container /tmp as Ross."""
    from providers.client import rpc
    return rpc('get_controller_snapshot',{'robot_id':robot_id})
