"""Stage 1: quiet-room audio experiment. All waveforms are synthetic."""
from pathlib import Path
import csv,json
import numpy as np
from audio.dsp import FS,features,background,add_event,Baseline

ROOT=Path(__file__).resolve().parent

def run():
    # Only dry PC/hum/noise backgrounds, no traffic or rain in this baseline.
    train=np.concatenate([features(background(12,s,gain=g))['x']
                          for s,g in [(11,.5),(12,1),(13,2),(14,1.4)]])
    calibration=np.concatenate([features(background(12,s,gain=g))['x']
                                for s,g in [(101,.7),(102,1.7)]])
    model=Baseline.fit(train,calibration)
    rows=[]
    for seed in range(1000,1010):
        normal=background(16,seed)
        variants={'pc_background':normal,
                  'lower_constant_gain':normal*.25,
                  'higher_constant_gain':normal*3,
                  'thunder_like':add_event(normal,'thunder',start=6,seed=seed),
                  'footstep_like':add_event(normal,'steps',start=6,seed=seed),
                  'soft_footstep_like':add_event(normal,'soft_steps',start=6,seed=seed),
                  'impact_like':add_event(normal,'impact',start=6,seed=seed)}
        for name,wave in variants.items():
            f=features(wave);scores,flags=model.detect(f)
            # Anomaly is evaluated after injection. Pre-event flags are reported separately.
            post=f['t']>=6.; hits=np.flatnonzero(flags&post)
            rows.append(dict(case=name,seed=seed,unusual_sound=bool(len(hits)),
                             pre_event_flags=int(np.sum(flags&~post)),
                             first_detection_s=float(f['t'][hits[0]]) if len(hits) else None,
                             peak_score=float(scores[post].max()),
                             invalid_windows=int(np.sum(~f['valid'])),danger_alert=False))
    out=ROOT/'results';out.mkdir(exist_ok=True)
    with (out/'audio_trials.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    summary={name:dict(trials=10,flagged=sum(r['unusual_sound'] for r in rows if r['case']==name),
                       pre_event_flags=sum(r['pre_event_flags'] for r in rows if r['case']==name))
             for name in variants}
    result=dict(scope='synthetic quiet-room audio only',sample_rate=FS,threshold=model.threshold,
                training_seeds=[11,12,13,14],calibration_seeds=[101,102],test_seeds=list(range(1000,1010)),
                results=summary,real_room_recordings=False,matlab_executed=False,
                note='Noise seeds repeat event templates. This is not real-world detection accuracy.')
    (out/'summary.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    return model,result

if __name__=='__main__':run()
