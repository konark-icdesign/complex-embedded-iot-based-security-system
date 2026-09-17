"""Small held-out ESC-50 domain-shift check; not room-level validation."""
from pathlib import Path
import json,math
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly
from .dsp import features,Baseline,FS

def load_audio(path):
    fs,x=wavfile.read(path)
    if np.issubdtype(x.dtype,np.integer):
        x=x.astype(float)/max(abs(np.iinfo(x.dtype).min),np.iinfo(x.dtype).max)
    else:x=x.astype(float)
    if x.ndim>1:x=x.mean(axis=1)
    g=math.gcd(fs,FS)
    if fs!=FS:x=resample_poly(x,FS//g,fs//g)
    return x

def evaluate(root,synthetic_models):
    directory=Path(root)/'fixtures'/'esc50'
    if not (directory/'manifest.json').exists():return dict(status='NOT_RUN_NO_DATA')
    manifest=json.loads((directory/'manifest.json').read_text())
    data={r['filename']:features(load_audio(directory/'audio'/r['filename']))
          for r in manifest if r['status']=='downloaded'}
    models={}
    for category in ('rain','engine'):
        def collect(fold):
            return np.concatenate([data[r['filename']]['x'][data[r['filename']]['valid']]
                                   for r in manifest if r['category']==category and r['fold']==fold and r['filename'] in data])
        models[category]=Baseline.fit(collect('1'),collect('2'))
    results=[]
    for r in manifest:
        if r['fold']!='5' or r['filename'] not in data:continue
        f=data[r['filename']]
        # A generous baseline: accept either approved normal proxy. This broadens
        # normal coverage but can also hide footsteps; that tradeoff is measured.
        ratios=np.stack([m.score(f['x'])/m.threshold for m in models.values()])
        raw=(ratios.min(axis=0)>1)&f['valid']
        flags=np.convolve(raw.astype(int),np.ones(3,dtype=int),'full')[:len(raw)]>=2
        syn=np.stack([m.score(f['x'])/m.threshold for m in synthetic_models.values()])
        synraw=(syn.min(axis=0)>1)&f['valid']
        synflags=np.convolve(synraw.astype(int),np.ones(3,dtype=int),'full')[:len(raw)]>=2
        normal=r['category'] in ('rain','engine')
        results.append(dict(filename=r['filename'],category=r['category'],fold=5,
                            declared_normal_proxy=normal,anomaly=bool(flags.any()),
                            anomalous_window_fraction=float(flags.mean()),
                            synthetic_model_anomaly=bool(synflags.any()),
                            first_anomaly=float(f['t'][np.flatnonzero(flags)[0]]) if flags.any() else None))
    return dict(status='EXECUTED',training_clips=6,calibration_clips=4,test_clips=len(results),
                thresholds={k:v.threshold for k,v in models.items()},
                note='Fold-5 clips; no tuning on them. Engine is a background proxy, not a measured PC fan.',rows=results)
