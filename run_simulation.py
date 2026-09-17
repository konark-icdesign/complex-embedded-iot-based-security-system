"""Reproduce all figures, synthetic trials, fixtures and the audio challenge."""
from pathlib import Path
import argparse,csv,json,time,sys,platform,hashlib,subprocess,shutil
from dataclasses import asdict
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.io import savemat,wavfile
from src.dsp import train_synthetic,features,background,FS,FEATURES
from src.scenarios import cases
from src.simulation import run
from src.fusion import Outbox,Config,Fusion
from src.real_audio import evaluate
from src.vision import room,compensate

ROOT=Path(__file__).resolve().parent
RESULTS=ROOT/'results'

def write_csv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def metrics(rows):
    positives=[r for r in rows if r['intrusion']];negatives=[r for r in rows if not r['intrusion']]
    lat=[r['latency'] for r in positives if r['red']]
    return dict(trials=len(rows),intrusion_trials=len(positives),nonintrusion_trials=len(negatives),
                detected=sum(r['red'] for r in positives),missed=sum(not r['red'] for r in positives),
                false_alerts=sum(r['red'] for r in negatives),
                naive_false_alerts=sum(r['naive_red'] for r in negatives),
                median_latency=float(np.median(lat)) if lat else None,
                max_latency=max(lat) if lat else None,
                nonintrusion_simulated_hours=len(negatives)*24/3600,
                note='Scenario-weighted synthetic trials; not a real security accuracy or false-alarms/hour estimate.')

def network_demo(events):
    p=RESULTS/'notification_demo.sqlite'
    if p.exists():p.unlink()
    o=Outbox(p)
    event=dict(events[0]);event['id']='room1-session-demo-'+event['id']
    o.enqueue(event);o.pump(False)
    queued=o.pending();o.close()
    o=Outbox(p);o.pump(True,lose_ack=True);attempts=o.attempts;o.close()
    o=Outbox(p);o.pump(True);o.pump(True)
    result=dict(queued_during_outage=queued,unique_receiver_alerts=o.count(),remaining=o.pending(),
                restart_test=True,lost_ack_test=True,transport_attempts=attempts+o.attempts,
                delivery='Local SQLite receiver only; no person was contacted')
    o.close();return result

def figures(primary,traces,demo,models):
    plt.rcParams.update({'figure.dpi':140,'axes.spines.top':False,'axes.spines.right':False,'font.size':9})
    c=traces['27_blocks_camera'];t=np.array([r['t'] for r in c])
    fig,axes=plt.subplots(4,1,figsize=(10,8),sharex=True,layout='constrained')
    axes[0].plot(t,[r['audio_score'] for r in c],color='#247c97');axes[0].axhline(models['dry'].threshold,c='tomato',ls='--');axes[0].set_ylabel('Audio deviation')
    for i,k in enumerate(['P','M','U']):axes[1].step(t,np.array([r[k] for r in c])*.7+i,where='post',label=k)
    axes[1].set_yticks([.35,1.35,2.35],['PIR','Radar','Near']);axes[1].set_ylim(-.2,3)
    axes[2].plot(t,[r['score'] for r in c],c='#555');axes[2].axhline(5,c='tomato',ls='--');axes[2].set_ylabel('Fusion points')
    axes[3].step(t,[r['state'] for r in c],where='post',c='#a63b40');axes[3].set_yticks([0,1,2],['GREEN','YELLOW','RED']);axes[3].set_xlabel('Simulation time (s)')
    for ax in axes:ax.axvspan(8,14,color='#eec96f',alpha=.16);ax.grid(alpha=.15)
    fig.suptitle('Camera blocked: audio + physical evidence\nSynthetic signal experiment; shaded interval is event truth',fontweight='bold')
    fig.savefig(RESULTS/'camera_blocked_timeline.png');plt.close(fig)
    # A transparent outcome chart keeps known failures visible.
    m=metrics(primary);labels=['Detected intrusion','Missed intrusion','False alert','No danger on non-intrusion']
    vals=[m['detected'],m['missed'],m['false_alerts'],m['nonintrusion_trials']-m['false_alerts']]
    fig,ax=plt.subplots(figsize=(9,3.4),layout='constrained');bars=ax.barh(labels,vals,color=['#287e7e','#bd4548','#d28b31','#588352']);ax.invert_yaxis()
    for bar,v in zip(bars,vals):ax.text(v+.2,bar.get_y()+bar.get_height()/2,str(v),va='center')
    ax.set_xlim(0,max(vals)+4);ax.set_xlabel('Number of 24-second scenarios');ax.set_title('52 scenario checks — failures retained',loc='left',fontweight='bold');fig.savefig(RESULTS/'scenario_outcomes.png');plt.close(fig)
    # Motion and sonar failure demonstrations.
    b=room(); local=b.copy();local[30:80,40:70]+=60
    motion=[]
    for n,x in [('Quiet',b),('Whole image +60',b+60),('Local 7.8% change',local)]:
        r,_,_=compensate(b,x);motion.append(dict(case=n,naive=100*float(np.mean(abs(x-b)>12)),corrected=100*float(np.mean(abs(r)>12))))
    write_csv(RESULTS/'lighting_measurements.csv',motion)
    fig,ax=plt.subplots(figsize=(8,3.5),layout='constrained');ix=np.arange(3)
    ax.bar(ix-.17,[r['naive'] for r in motion],.34,label='Naive subtraction',color='#c46a4b');ax.bar(ix+.17,[r['corrected'] for r in motion],.34,label='Global gain/offset corrected',color='#317b87');ax.set_xticks(ix,[r['case'] for r in motion]);ax.set_ylabel('Changed image area (%)');ax.legend();fig.savefig(RESULTS/'lighting_test.png');plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,3.2),layout='constrained');c=traces['14_bad_echo']
    ax.plot([r['t'] for r in c],[r['raw_distance'] for r in c],label='Raw echo');ax.plot([r['t'] for r in c],[r['distance'] for r in c],label='Causal five-sample median');ax.set_xlim(7,10);ax.set_ylabel('Distance (m)');ax.set_xlabel('Time (s)');ax.legend();fig.savefig(RESULTS/'ultrasonic_test.png');plt.close(fig)
    x=demo['audio'];fig,ax=plt.subplots(figsize=(9,3.2),layout='constrained')
    ax.specgram(x,NFFT=2048,Fs=FS,noverlap=1024,cmap='magma',vmin=-110,vmax=-40);ax.set_ylim(0,4000);ax.set_xlabel('Time (s)');ax.set_ylabel('Frequency (Hz)');ax.set_title('Synthetic footsteps — STFT, not a sound classifier',loc='left');fig.savefig(RESULTS/'spectrogram.png');plt.close(fig)

def save_fixture(demo,models):
    data=dict(audio=demo['audio'],fs=FS,expected_features=demo['features']['x'],
              expected_times=demo['features']['t'],frames=np.stack(demo['frames'],axis=2),
              frame_times=demo['frame_times'])
    for mode in ['dry','rain']:
        data['train_'+mode]=np.column_stack([background(12,s,mode,g,traffic=True) for s,g in [(11,.5),(12,1),(13,2),(14,1.4)]])
        data['cal_'+mode]=np.column_stack([background(12,s,mode,g,traffic=True) for s,g in [(101,.7),(102,1.7)]])
        data['center_'+mode]=models[mode].center;data['scale_'+mode]=models[mode].scale;data['threshold_'+mode]=models[mode].threshold
    savemat(ROOT/'fixtures'/'matlab_reference.mat',data,do_compression=True)
    # Preserve only completed samples from the actual ring-buffer capture.
    packets=demo['evidence'];audio=np.concatenate([p[1] for p in packets])
    wavfile.write(RESULTS/'event_audio.wav',FS,(np.clip(audio,-1,1)*32767).astype(np.int16))
    write_csv(RESULTS/'event_sensor_history.csv',[p[3] for p in packets])
    frames=[p[2] for p in packets if p[2] is not None]
    if frames:
        np.savez_compressed(RESULTS/'event_frames.npz',frames=np.stack(frames),timestamps=[p[0] for p in packets if p[2] is not None])
        if shutil.which('ffmpeg'):
            command=['ffmpeg','-y','-f','rawvideo','-pix_fmt','gray','-s','160x120','-r','5','-i','pipe:0','-an','-c:v','libx264','-pix_fmt','yuv420p',str(RESULTS/'event_video.mp4')]
            subprocess.run(command,input=np.stack(frames).astype('uint8').tobytes(),capture_output=True,check=True)
    (RESULTS/'event_evidence.json').write_text(json.dumps(dict(start=packets[0][0]-.1,end=packets[-1][0],events=demo['events'],
                                        note='All media synthetic. Audio window starts one 100ms chunk before first packet timestamp.'),indent=2))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seeds',type=int,default=10);args=ap.parse_args()
    if args.seeds<1:raise SystemExit('--seeds must be positive')
    RESULTS.mkdir(exist_ok=True);(RESULTS/'traces').mkdir(exist_ok=True)
    begin=time.perf_counter();models,_=train_synthetic()
    rows=[];traces={};primary=[];demo=None
    for seed_index in range(args.seeds):
        for case in cases():
            capture=seed_index==0 and case.name=='23_walk_in'
            result,trace,extra=run(case,models[case.context],seed=1000+seed_index, capture=capture)
            rows.append(result)
            if seed_index==0:
                primary.append(result);traces[case.name]=trace
                write_csv(RESULTS/'traces'/f'{case.name}.csv',trace)
            if capture:demo=extra
        print(f'Completed seed {seed_index+1}/{args.seeds}',flush=True)
    write_csv(RESULTS/'scenario_results.csv',primary);write_csv(RESULTS/'monte_carlo_results.csv',rows)
    real=evaluate(ROOT,models);(RESULTS/'real_audio_results.json').write_text(json.dumps(real,indent=2))
    if real.get('rows'):write_csv(RESULTS/'real_audio_results.csv',real['rows'])
    save_fixture(demo,models);figures(primary,traces,demo,models)
    # Window sweep uses the same held-out signals: sensitivity analysis, not a second accuracy claim.
    sweep=[]
    for span in [.5,2.,4.,8.]:
        for name in ['36_delayed_camera','38_warm_moving_object','42_outside_door']:
            c=next(c for c in cases() if c.name==name)
            r,_,_=run(c,models[c.context],config=Config(span=span));sweep.append(dict(span=span,scenario=name,red=r['red'],latency=r['latency']))
    write_csv(RESULTS/'window_sensitivity.csv',sweep)
    timing=[]
    for span in [.5,2.,4.,8.]:
        for delay in [1.,3.2,5.,7.]:
            fusion=Fusion(Config(span=span))
            fusion.update(8.,dict(A=True));fusion.update(8.5,dict(P=True))
            fusion.update(8.+delay,dict(M=True))
            timing.append(dict(span=span,last_channel_delay=delay,red=fusion.state==2,
                               truth='same event; impulse channels'))
        fusion=Fusion(Config(span=span))
        fusion.update(8.,dict(A=True));fusion.update(12.5,dict(P=True));fusion.update(15.,dict(M=True))
        timing.append(dict(span=span,last_channel_delay=7.,red=fusion.state==2,
                           truth='unrelated events; constructed accidental coincidence'))
    write_csv(RESULTS/'impulse_timing_sensitivity.csv',timing)
    summary=dict(primary=metrics(primary),monte_carlo=metrics(rows),network=network_demo(demo['events']),
                 audio_models={k:dict(center=v.center.tolist(),scale=v.scale.tolist(),threshold=v.threshold) for k,v in models.items()},
                 real_audio_status=real['status'],wall_seconds=round(time.perf_counter()-begin,3),
                 python=sys.version,numpy=np.__version__,platform=platform.platform(),
                 seed_policy='11-14 training; 101-102 calibration; 1000 onward evaluation; same case with independent noise seeds',
                 matlab_execution='NOT_RUN; runtime not installed',physical_hardware='NOT_TESTED')
    (RESULTS/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary['primary'],indent=2));print('Reference simulation completed. Known failures are NOT test passes.')

if __name__=='__main__':main()
