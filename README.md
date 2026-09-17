# Room security prototype

A room-monitoring project using audio, a camera, PIR, radar and ultrasonic range. The aim is to check whether several readings point to the same unusual event before raising an alarm.

## Background

I first had the idea around 2022. The room setup and project requirements came from me. In September 2026, I revisited it and used substantial AI assistance to develop the current simulation, draft code, tests and documentation. The recorded simulation and compiler runs were carried out in the hosted development environment.

The GitHub history records the September 2026 simulation and upload. Hardware testing is still pending.

## Current version

The main simulation is Python. Arduino C++ handles sensor filtering and the fallback alarm. MATLAB source is included, but has not been run. The full detection pipeline has not been implemented in C yet.

An unusual sound puts the system into YELLOW. The fusion code checks detections within a rolling four-second window. Audio alone cannot trigger RED; audio together with PIR and radar can. Camera and sensor inputs run continuously, so earlier movement can contribute too.

The separate audio-triggered review of buffered infrared footage is still missing. The simulated camera uses grayscale images and detects image changes. No infrared camera has been tested.

## Recorded results

| Check | Result |
|---|---|
| Synthetic evaluation | 52 scenarios, repeated with 10 noise seeds |
| Intrusions | 160 detected and 30 missed out of 190 trials |
| Non-intrusions | 20 false alerts out of 330 trials |
| Public audio check | 30 evaluation clips; all 3 footstep clips missed by the broad background model |
| Quiet-room audio check | All 10 soft-footstep trials missed |
| C++ sensor/fallback replay | 12,480 ticks matched Python |
| UNO R4 WiFi sketch | Compiled; no physical board test |

The trials repeat simple event templates. These results describe the simulation, not accuracy in an actual room. The [experiment notes](docs/experiment_report.md) explain the failures and link to the logs.

## Run it

From the project folder, using Python 3.12:

```text
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python scripts/fetch_real_audio.py
python run_simulation.py --seeds 10
python -m unittest discover -s tests -p "test_*.py" -v
```

On Linux/macOS, activate with `source .venv/bin/activate`. Use `--seeds 1` for a quicker 52-scenario run. The first audio download needs internet access. Rerunning replaces the generated results.

There is also a [Colab notebook](https://colab.research.google.com/github/konark-icdesign/complex-embedded-iot-based-security-system/blob/main/notebooks/run_project.ipynb). Its cells were syntax-checked, but it has not been executed on Colab.

For C++ host tests, MATLAB instructions and the smaller audio experiment, see [running the checks](docs/reproduction.md).

## Next work

- Review the DSP and fusion code module by module.
- Implement the C detection core and the intended audio-triggered investigation.
- Investigate quiet footsteps, warm-object false alarms and responses to activity outside the room.
- Run MATLAB, then connect and test the actual devices.
- Add real remote notifications. The current receiver is a local SQLite simulation.

## Notes

[System design](docs/architecture.md) · [DSP calculations](docs/dsp_maths.md) · [Hardware plan](docs/hardware.md) · [HP setup](docs/hp_setup.md) · [Development tasks](docs/learning_and_validation.md) · [Sources](docs/sources.md)

The audio tests use [ESC-50](https://github.com/karolpiczak/ESC-50). Its licence and recording attributions are in `fixtures/esc50/LICENSE`; the WAV files are downloaded separately. No project-wide licence has been selected for the original code.
