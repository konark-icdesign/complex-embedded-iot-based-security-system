from collections import deque
from dataclasses import asdict
import numpy as np
from .dsp import features,FS,HOP
from .vision import Camera,room,render
from .fusion import Fusion,Sensors
from .scenarios import waveform,physical

class EvidenceBuffer:
    """Bounded 5 s prebuffer, 20 s event cap. Raw audio and frames are retained."""
    def __init__(self):
        self.history=deque(maxlen=51);self.saved=[];self.started=None;self.done=False
    def push(self,t,audio,frame,row,trigger):
        packet=(t,audio.copy(),None if frame is None else frame.copy(),row.copy())
        self.history.append(packet)
        if trigger and self.started is None:
            self.started=t;self.saved=list(self.history)
        elif self.started is not None and not self.done:
            self.saved.append(packet)
        if self.started is not None and t-self.started>=14.9:self.done=True

def run(case,model,seed=1000,config=None,capture=False):
    rng=np.random.default_rng(seed+100)
    x=waveform(case,seed)
    f=features(x);scores,flags=model.detect(f)
    camera=Camera(); sensors=Sensors();fusion=Fusion(config)
    base=room(seed); trace=[];ai=0;last_cam=dict(motion=False,health=False,naive=0.,fraction=0.)
    fallback=False;fallback_count=0;last_heartbeat=0.;buffer=EvidenceBuffer()
    frames=[]; times=[]
    naive_red=False;last_audio_time=-1e9;last_health_audio=False
    for k in range(240):
        t=round(k*.1,6)
        # Audio output is an event per completed window, not an unlimited sample hold.
        a=False
        while ai<len(f['t']) and f['t'][ai]<=t+1e-9:
            a=a or bool(flags[ai]);last_health_audio=not bool(f['valid'][ai]);ai+=1
        if a:last_audio_time=t
        audio_score=float(scores[max(0,ai-1)])
        if k%2==0:
            frame=render(base,t,rng,case.video,case.video_start)
            last_cam=camera.update(t,frame)
            if capture:frames.append(np.zeros_like(base,dtype=np.uint8) if frame is None else frame);times.append(t)
        else:frame=None
        p,m,d=physical(case,t,rng)
        pp,mm,uu,filtered,fault=sensors.update(p,m,d)
        online=not (case.server_outage and 6.<=t<19.)
        usb=not (case.usb_outage and 6.<=t<19.)
        if online and usb:last_heartbeat=t
        degraded=t-last_heartbeat>2.
        fallback_count=fallback_count+1 if (degraded and pp and mm and uu) else 0
        if fallback_count>=10:fallback=True
        # Missing sensor packet does not preserve the last physical reading forever.
        e=dict(A=a,V=last_cam['motion'] if k%2==0 else False,
               P=pp if usb else False,M=mm if usb else False,U=uu if usb else False)
        health=last_cam['health'] or last_health_audio or fault or not usb
        if online:
            state,score,entered,channels=fusion.update(t,e,health)
        else:state,score,entered,channels=-1,0.,False,[]
        # Deliberately bad reference design: any raw alarm input -> RED.
        naive_red=naive_red or a or last_cam['naive']>.018 or p or m or d<1.8
        row=dict(t=t,A=int(a),V=int(e['V']),P=int(e['P']),M=int(e['M']),U=int(e['U']),
                 health=int(health),state=state,score=score,audio_score=audio_score,
                 raw_distance=float(d),distance=float(filtered),motion_fraction=last_cam['fraction'],
                 naive_fraction=last_cam['naive'],fallback=int(fallback),server=int(online),
                 physical_p=int(pp),physical_m=int(mm),physical_u=int(uu))
        trace.append(row)
        if capture:
            chunk=x[max(0,k-1)*1600:k*1600]
            # Only samples already captured at t belong in the ring buffer.
            buffer.push(t,chunk,frame,row,state in (1,2))
    red_t=[v['t'] for v in trace if v['state']==2 or v['fallback']]
    t0=case.event_start
    out=dict(name=case.name,group=case.group,intrusion=case.intrusion,seed=seed,
             red=bool(red_t),central_red=bool(fusion.alerts),local_fallback=fallback,
             yellow=any(v['state']==1 for v in trace),final_state=trace[-1]['state'],
             latency=(round(red_t[0]-t0,3) if red_t else None),
             naive_red=bool(naive_red),alerts=len(fusion.alerts),note=case.note)
    if not case.intrusion and red_t:out['outcome']='FALSE_ALERT'
    elif case.intrusion and not red_t:out['outcome']='MISSED_INTRUSION'
    else:out['outcome']='DETECTED' if case.intrusion else 'NO_DANGER'
    extra=dict(audio=x,features=f,audio_scores=scores,events=fusion.alerts,
               frames=frames,frame_times=times,evidence=buffer.saved) if capture else {}
    return out,trace,extra
