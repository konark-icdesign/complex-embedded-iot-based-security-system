# Quiet-room detection change

The original detector missed weak synthetic footsteps. Its minimum feature
scales were wide compared with the variation in the quiet-room generator.
The new room profile uses smaller minimum scales, measured median/MAD spread,
and a threshold above the largest normal calibration score. It keeps the same
nine features and two-of-three-window rule. Python and C use identical frozen
parameters; no event labels are used to calculate them.

Four candidates were compared on development inputs. The selected profile was
then frozen before running different seeds and footstep waveforms. The exact
split, choices and acceptance checks are in the [protocol](../experiments/detection_quality/protocol.md).

## Measured result

[GitHub run 35250249454](https://github.com/konark-icdesign/complex-embedded-iot-based-security-system/actions/runs/35250249454)
executed commit `5bd05078df6b171632d88e8e7efde1f01fbf58a4`.
The [recorded summary](../results/detection-quality/recorded_summary.json) preserves
the aggregate output; [the committed run archive](../evidence/github/35250249454/) contains the per-trial results, frozen model parameters, MATLAB replay input and job logs copied from the original workflow.
Python/C scores and flags agreed across the tested synthetic inputs. MATLAB
R2026a replayed all 240 final clips with identical flags and a largest score
difference of 1.78e-15. The connected pipeline also passed 26 Python tests,
C/C++ sanitizer checks and all four incident sessions with both backends;
the UNO R4 WiFi sketch compiled successfully.

| Withheld synthetic inputs | Original scoring calibration | Room calibration |
|---|---:|---:|
| Soft footsteps detected | 0/20 | 20/20 |
| Very soft footsteps detected | 0/20 | 1/20 |
| Ordinary footsteps detected | 20/20 | 20/20 |
| Impacts detected | 20/20 | 20/20 |
| Quiet/gain-change/fan-shift clips flagged | 0/60 | 0/60 |
| Silence/clipped-input anomaly flags | 0/40 | 0/40 |
| RED from audio alone, across all categories | 0/240 | 0/240 |

Median first-detection delay for the new soft-step cases was 0.616 seconds.
The development cases were harder for this model: 9/10 soft-step hits with a
1.992-second median delay. These are event-level counts, not frame accuracy.
Both model formulas receive the same normal training/calibration data for this
comparison. This is a new evaluation, not a revised version of the old 520 trials.

Silence and clipping remain invalid audio, so suppressing their anomaly flags
does not mean the microphone is healthy. The incident pipeline still receives
the audio-health flag. Only 400 seconds of quiet/gain-changing normal audio and
200 seconds of the specified fan change were tested. Longer recordings and
different equipment may behave differently.

## What this does not fix

Both quiet-trained models flagged all 30 previously inspected ESC-50 clips,
including all six rain/engine background proxies. Detecting their three
footstep clips therefore demonstrates no useful discrimination. The historical
real-background model, which missed all three, is a different model; this change
does not fix that result. Actual room recordings are still needed for calibration
and a separate recording-session evaluation.

Thunder, wind and clicks still open investigations. None causes RED alone.
However, each causes RED in all 20 test replays when concurrent PIR and radar
are deliberately supplied. That is an unresolved false-alarm route when those
sensor readings have a benign shared cause. More audio sensitivity cannot
establish where those sensors detected movement.

The current warm-object and person simulations can produce the same camera/PIR
observations. Renaming one scenario or weakening its labels would not solve
that ambiguity. Camera interpretation and sensor placement need separate work.

## Using the change

`run_incidents.py` now defaults to `--audio-profile room`. The profile is frozen
for an incident journal; use a new output directory when changing it.
`--audio-profile legacy` retains the previous continuous-runner calibration.
The original `run_simulation.py` and its historical results retain their models.

```text
make incident-build
python experiments/detection_quality/run_quality.py --split development --c-library build/libdetection.so
python experiments/detection_quality/run_quality.py --split heldout --c-library build/libdetection.so
python scripts/fetch_real_audio.py
python experiments/detection_quality/real_diagnostic.py
```

The **Detection quality** workflow runs those commands and MATLAB replay.
Its synthetic acceptance checks fail the job on a regression; the public-audio
diagnostic is reported without pretending that the transfer problem passes.
Calibration still runs in Python; the C backend runs features and detection.
