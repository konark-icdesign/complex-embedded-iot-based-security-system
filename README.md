# Room security prototype

I started thinking about this project around 2022 and returned to it in September 2026. The idea is to monitor a room using sound, a camera and motion sensors, then check whether their readings point to the same event.

The setup includes an Arduino UNO R4 WiFi, an HP t640, a TP-Link router, PIR, radar and ultrasonic sensors. Hardware integration is in progress. The results recorded here come from simulation and software tests; full testing in the room is still pending.

## How it works

An unusual sound puts the system into YELLOW and opens an investigation. It checks camera and sensor activity within a four-second window. Sound alone cannot cause RED. Sound with PIR and radar can, although that combination can also produce false alarms.

The recorder keeps five seconds before the trigger and eight seconds after it. Each incident has its own timestamps and evidence files.

Python runs the simulation, camera processing, recording and delivery. A C implementation handles audio features, anomaly scoring and corroboration. Arduino C++ handles sensor filtering and a local fallback alarm if the PC stops responding. MATLAB provides a separate numerical check.

The camera tests currently use generated grayscale images. Infrared detection and person recognition have not been validated.

## Where it stands

The Python tests, C/C++ checks and MATLAB reference have run on GitHub. The UNO R4 WiFi firmware compiles. Continuous sessions test successive incidents, a network outage, a host restart, PC failure and thunder without movement. Alerts go to a local HTTP test receiver for now.

The earlier simulation covered 52 scenarios with ten noise seeds each:

| Outcome | Trials |
|---|---:|
| Intrusions detected | 160/190 |
| Intrusions missed | 30/190 |
| False alerts on non-intrusions | 20/330 |

A later audio experiment changed the quiet-room calibration. On a separate synthetic set, soft-step detections improved from 0/20 to 20/20. Very soft steps were still mostly missed: only 1/20 was detected. There were no flags in the 60 tested quiet, gain-change and fan-change clips.

Real recordings remain a problem. The earlier broad background model missed all three public footstep clips. Both quiet-trained models flagged all 30 public clips, including the normal background examples. Better synthetic results have not solved that.

The [original results](docs/experiment_report.md), [audio comparison](docs/detection_quality.md) and [validation record](docs/validation.md) contain the details. These measurements do not establish accuracy in a real room.

## Running it

Use Python 3.12. From the project folder on Windows:

```text
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python scripts/fetch_real_audio.py
python run_simulation.py --seeds 1
python -m unittest discover -s tests -p "test_*.py" -v
```

On Linux or macOS, activate with `source .venv/bin/activate`. Use `--seeds 10` for the longer scenario run. The audio download needs internet access.

For the continuous simulation with the C backend, use Linux with GCC and Make:

```text
make incident-build
python run_incidents.py --c-library build/libdetection.so
```

The continuous runner uses the newer room profile by default. Add `--audio-profile legacy` to compare the previous calibration. Choose a fresh output directory with `--output` when rerunning; existing incident evidence is preserved.

More commands are in [reproduction](docs/reproduction.md) and [the incident workflow](docs/incidents.md).

## What is left

The next hardware work is to connect the board, PC, camera and microphone, then check acquisition timing and communication. Room recordings are needed to calibrate and evaluate the detector using separate recording sessions.

Very quiet footsteps, warm moving objects and activity outside the room still need work. A real notification endpoint also needs to be connected and tested.

Results should distinguish simulation, individual component tests, combined hardware tests and tests in the intended room.

## Notes and records

The [debugging history](docs/debugging_history.md) records the problems found, fixes and remaining failures. Important original run outputs are committed in [the evidence archive](evidence/github/), including checksums and source run IDs.

- [System design](docs/architecture.md)
- [DSP calculations](docs/dsp_maths.md)
- [Hardware and wiring](docs/hardware.md)
- [HP t640 setup](docs/hp_setup.md)
- [Learning and validation tasks](docs/learning_and_validation.md)

I used AI assistance for implementation, debugging and documentation. The linked logs record the tests that were actually run.

Public audio comes from [ESC-50](https://github.com/karolpiczak/ESC-50); its licence and recording attributions are kept in `fixtures/esc50/LICENSE`. No project-wide licence has been selected for the original code.
