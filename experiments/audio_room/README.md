# Quiet-room audio experiment

Focused check within the integrated security project: test an audio anomaly detector for a quiet room with steady PC noise.

This is a simulation-only work in progress. No recordings of the installation room have been supplied. The room is assumed mostly sound-insulated, based on the intended setup; its acoustics and noise floor have not been measured.

## Current experiment

- Normal background: synthetic low-level noise and tonal hum representing a PC/background source. This is a test signal, not a measured fan model.
- Disturbances: thunder-like rumble, footstep-like pulses, softer pulses and an impact-like transient.
- Gain checks: repeat the normal signal at 0.25x and 3x constant gain, without clipping.
- Output: normal or unusual sound. Invalid silence/clipping is reported separately. There is no danger decision, sound classifier or automatic weather recognition at this stage.

Thunder can reasonably trigger an investigation because it changes the room sound. Audio alone cannot prove whether the cause is weather or an entrant. It must not generate a danger alert on its own.

## Run

Use a Python virtual environment, then:

```text
python -m pip install -r ../../requirements.txt
python run_audio.py
python -m unittest test_audio -v
```

Results are written to `results/audio_trials.csv` and `results/summary.json`. Read the measured misses as well as the successful detections. Training, calibration and test noise seeds are separate, but the generated events share simple templates.

## Method

16 kHz mono audio; 2048-sample frames; 1024-sample hop. Remove DC, apply a Hann window and compute normalized FFT power. Features are four band-power fractions, spectral centroid, spectral flatness, zero-crossing rate, log crest factor and within-frame energy variation. A frozen median/MAD baseline measures standardized deviation. Two of three abnormal trailing windows are required, except for an extreme transient. These overlapping frames are persistence, not independent sensors.

Constant-gain normalization does not solve clipping, time-varying automatic gain, changes in fan spectrum or microphone placement. No automatic baseline retraining is used.

## Relationship to the whole project

The earlier whole-system experiment exposed false alarms from common causes and audio transfer problems on real recordings. This smaller stage isolates the audio calculation. Narrowing the assumed room background does not erase the earlier real-audio failures or establish field accuracy.

Next audio investigation: vary background spectrum and event-to-background ratio. Camera, physical sensors, fusion, notifications and MATLAB source are included at the repository root. This experiment imports the root DSP implementation; it is not a separate project. MATLAB execution and physical measurements remain outstanding.
