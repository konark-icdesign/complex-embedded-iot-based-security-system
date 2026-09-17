# Quiet-room sensitivity experiment

The question is whether normal-room calibration can recover weak audio changes
without adding flags on the normal inputs tested here. This is an anomaly
detector, not a footstep recognizer. Labels enter the evaluator only.

Training uses synthetic normal sessions 11–14; calibration uses 101–104.
Development uses seeds 2000–2009. Four feature-floor fractions were compared:
0.1, 0.25, 0.5 and 1.0. All use median/MAD scaling and a threshold of 1.2 times
the maximum normal calibration score (minimum 1.0).

Development run 35249896689 found 9/10 soft-step hits for fraction 0.1,
2/10 for 0.25, and 0/10 for 0.5, 1.0 and the original baseline. None flagged
quiet, gain-ramp or fan-shift trials. Fraction 0.1 and margin 1.2 are frozen
before the first withheld run. No positive waveform enters model fitting.

Final evaluation uses seeds 8000–8019, carriers 85–130 Hz instead of 55–80 Hz,
and an extra non-integer harmonic. Each split varies cadence, damping, phase,
noise and overall gain. It remains the same simple family of damped impacts;
these are not independent recordings or a realistic room impulse response.
Each of 12 categories has 20 ten-second final trials. Normal quiet/gain trials
provide only 400 seconds of observation; zero flags cannot establish a daily
false-alarm rate.

Before running final evaluation, acceptance requires more soft-step hits than
the baseline, no flags on quiet/gain/fan/silence/clipped inputs, no loss on
ordinary footsteps/impacts, and no RED alarm from audio alone. The optional
PIR+radar coincidence replay is reported separately: benign audio accompanied
by those two sensors can still confirm an alarm. No sensor-placement fix is
claimed.

The development clipping fixture initially applied gain after saturation,
turning some examples into valid square waves. The corrected fixture holds
the input at the ADC rails. This was a test-input error, not a detector fix.

Previously inspected ESC-50 fold-5 clips are rerun only as a transfer diagnostic.
They do not select parameters, and are not called a fresh held-out evaluation.
The real-room question remains open until room recordings are available.

All program execution for this experiment takes place in GitHub Actions.
Full per-trial results and frozen parameters are stored in its artifact.
Python/C score and flag agreement is checked for every synthetic trial;
MATLAB independently replays the frozen final feature matrices.
