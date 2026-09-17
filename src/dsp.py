"""Small, causal audio detector. Scores are deviations, never probabilities."""
from dataclasses import dataclass
import numpy as np
from scipy.signal import lfilter

FS = 16000
N = 2048
HOP = 1024
FEATURES = ('band_0_250', 'band_250_1000', 'band_1000_4000',
            'band_4000_8000', 'centroid_normalized', 'flatness', 'zcr',
            'log_crest', 'subframe_energy_variation')
FLOORS = np.array([.025, .025, .025, .025, .02, .08, .025, .10, .10])

def features(audio, fs=FS):
    x = np.asarray(audio, dtype=float)
    if x.ndim != 1 or len(x) < N or not np.isfinite(x).all():
        raise ValueError('Need finite mono audio with at least 2048 samples')
    frames = np.lib.stride_tricks.sliding_window_view(x, N)[::HOP].copy()
    clipped = np.mean(np.abs(frames) >= .999, axis=1) > .01
    frames -= frames.mean(axis=1, keepdims=True)
    rms = np.sqrt(np.mean(frames**2, axis=1))
    valid = (rms > 1e-7) & ~clipped
    # Symmetric Hann, explicitly defined to match the MATLAB implementation.
    win = .5 - .5*np.cos(2*np.pi*np.arange(N)/(N-1))
    power = np.abs(np.fft.rfft(frames*win, axis=1))**2
    power[:, 1:-1] *= 2
    p = power / np.maximum(power.sum(axis=1, keepdims=True), 1e-30)
    freq = np.fft.rfftfreq(N, 1/fs)
    bands = [p[:, (freq >= lo) & (freq < hi)].sum(axis=1)
             for lo, hi in [(0,250),(250,1000),(1000,4000),(4000,fs/2+1)]]
    centroid = (p * freq).sum(axis=1)/(fs/2)
    flatness = np.exp(np.mean(np.log(np.maximum(p,1e-30)),axis=1))*p.shape[1]
    zcr = np.mean(frames[:,1:]*frames[:,:-1] < 0, axis=1)
    crest = np.log(np.maximum(np.max(np.abs(frames),axis=1)/np.maximum(rms,1e-15),1))
    sub = np.sqrt(np.mean(frames.reshape(-1,8,N//8)**2,axis=2))
    variation = np.std(sub,axis=1)/np.maximum(np.mean(sub,axis=1),1e-15)
    feat = np.column_stack(bands+[centroid,flatness,zcr,crest,variation])
    # End timestamps: a decision cannot use samples not yet acquired.
    times = (np.arange(len(frames))*HOP+N)/fs
    return dict(t=times, x=feat, rms=rms,
                dbfs=20*np.log10(np.maximum(rms,1e-15)), valid=valid)

@dataclass
class Baseline:
    center: np.ndarray
    scale: np.ndarray
    threshold: float = 3.5

    @classmethod
    def fit(cls, training, calibration):
        center=np.median(training,axis=0)
        scale=np.maximum(1.4826*np.median(np.abs(training-center),axis=0),FLOORS)
        model=cls(center,scale)
        model.threshold=max(3.5,float(np.quantile(model.score(calibration),.995)*1.2))
        return model

    def score(self, x):
        z=(np.asarray(x)-self.center)/self.scale
        return np.sqrt(np.mean(np.minimum(z*z,400),axis=-1))

    def detect(self, f):
        scores=self.score(f['x'])
        raw=(scores>self.threshold)&f['valid']
        # Two of three trailing windows; no look-ahead.
        persist=np.convolve(raw.astype(int),np.ones(3,dtype=int),'full')[:len(raw)]>=2
        extreme=(scores>2*self.threshold)&(f['x'][:,7]>np.log(8))&f['valid']
        return scores,(persist|extreme)&f['valid']

def background(seconds, seed, mode='dry', gain=1.0, traffic=False):
    r=np.random.default_rng(seed)
    t=np.arange(round(seconds*FS))/FS
    phase=r.uniform(0,2*np.pi)
    low=lfilter([.12],[1,-.88],r.normal(size=len(t)))
    x=.003*r.normal(size=len(t))+.007*low
    x+=.005*np.sin(2*np.pi*100*t+phase)+.002*np.sin(2*np.pi*240*t+.3)
    x*=1+.08*np.sin(2*np.pi*.31*t)
    if traffic:
        x+=.006*lfilter([.04],[1,-.96],r.normal(size=len(t)))
    if mode=='rain':
        white=r.normal(size=len(t))
        x+=.02*lfilter([1,-.7],[1],white)*(1+.15*np.sin(2*np.pi*.7*t))
    return x*gain

def add_event(x, kind, start=8.0, duration=5.0, seed=0, amplitude=1.0):
    """Synthetic surrogates, not validated acoustic models of real footsteps."""
    y=x.copy(); r=np.random.default_rng(seed)
    i=int(start*FS); length=min(int(duration*FS),len(y)-i)
    if length<=0 or kind=='none': return y
    t=np.arange(length)/FS; e=np.zeros(length)
    if kind in ('steps','soft_steps'):
        for k in np.arange(.0,duration,.58):
            u=t-k; env=np.exp(-np.maximum(u,0)*22)*(u>=0)*(u<.35)
            e+=env*(.075*np.sin(2*np.pi*72*u)+.018*r.normal(size=length))
        if kind=='soft_steps': e*=.12
    elif kind in ('impact','glass','thunder'):
        f=55 if kind=='thunder' else 1100
        decay=1.8 if kind=='thunder' else 8
        noise=r.normal(size=length)
        if kind=='thunder': noise=lfilter([.1],[1,-.9],noise)
        e=.22*np.exp(-decay*t)*(.6*noise+.4*np.sin(2*np.pi*f*t))
    elif kind=='wind':
        e=.08*lfilter([.025],[1,-.975],r.normal(size=length))*(1+np.sin(2*np.pi*.6*t))
    elif kind=='speech':
        e=.02*(np.sin(2*np.pi*170*t)+.5*np.sin(2*np.pi*340*t))*(.5+.5*np.sin(2*np.pi*4*t))
    elif kind=='click':
        e[:min(8,length)]=.7
    else: raise ValueError(kind)
    y[i:i+length]+=amplitude*e
    return np.clip(y,-1,1)

def train_synthetic():
    models={}; raw={}
    for mode in ('dry','rain'):
        train=np.concatenate([features(background(12,s,mode,g,traffic=True))['x']
                              for s,g in [(11,.5),(12,1),(13,2),(14,1.4)]])
        cal=np.concatenate([features(background(12,s,mode,g,traffic=True))['x']
                            for s,g in [(101,.7),(102,1.7)]])
        models[mode]=Baseline.fit(train,cal)
        raw[mode]=(train,cal)
    return models,raw
