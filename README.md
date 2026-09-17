# Room security prototype

A room-monitoring project using audio, a camera, PIR, radar and ultrasonic range. The aim is to check whether several readings point to the same unusual event before raising an alarm.

## Background

I first had the idea around 2022. The room setup and project requirements came from me. In September 2026, I revisited it and used substantial AI assistance to develop the current simulation, draft code, tests and documentation. The recorded simulation and compiler runs were carried out in the hosted development environment.

The GitHub history records the September 2026 simulation and upload. Hardware testing is still pending.

## Current version

The original scenario simulation is Python. The continuous incident runner can use a C core for audio features, anomaly scoring and corroboration; Python handles recording, incident state and HTTP delivery. Arduino C++ handles sensor filtering and the fallback alarm. The MATLAB reference now has its own GitHub execution job. See the [validation record](docs/validation.md).

An unusual sound puts the system into YELLOW. The fusion code checks detections within a rolling four-second window. Audio alone cannot trigger RED; audio together with PIR and radar can. Camera and sensor inputs run continuously, so earlier movement can contribute too.

The continuous runner opens an investigation, retains five seconds of earlier evidence, collects eight seconds after the trigger and replays the recorded grayscale frames. Each incident gets its own evidence package. This is classical image-change analysis, not infrared interpretation or person recognition. No infrared camera has been tested.

## Continuous incident run

On Linux with Python dependencies, GCC and Make:

```text
make incident-build
python run_incidents.py --c-library build/libdetection.so
```

This runs two incidents, network loss with a host restart, PC failure, and thunder without physical motion. It uses the compiled Arduino core and a loopback HTTP evidence receiver. An existing output directory is preserved; choose a new one with `--output` when rerunning. See [incident workflow](docs/incidents.md) for the interfaces and limitations. GitHub's **Incident pipeline** workflow runs these checks and retains the evidence as artifacts.

## Detection quality update

The continuous runner now uses a room-calibrated audio profile. On a new withheld synthetic set, soft-footstep detections improved from 0/20 to 20/20, with no flags on 60 quiet/gain-change/fan-change trials. Very soft footsteps remained mostly missed (1/20 detected), and the public-recording transfer test remains poor. These are simulation results. See the [comparison, failures and reproduction commands](docs/detection_quality.md).

Use `--audio-profile legacy` to compare the previous continuous-runner calibration. Changing profiles requires a new output directory.

## Earlier recorded results

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
- Review the continuous incident traces and the C/Python numerical comparison.
- Validate audio on actual room recordings; investigate very quiet footsteps, warm-object false alarms and responses to activity outside the room.
- Connect and test the actual devices, including the acquisition and clock adapters.
- Connect a selected remote notification service. The continuous runner currently uses HTTP to a controlled local receiver; the older scenario runner retains its SQLite receiver demonstration.

## Notes

[System design](docs/architecture.md) · [DSP calculations](docs/dsp_maths.md) · [Hardware plan](docs/hardware.md) · [HP setup](docs/hp_setup.md) · [Development tasks](docs/learning_and_validation.md) · [Sources](docs/sources.md)

The audio tests use [ESC-50](https://github.com/karolpiczak/ESC-50). Its licence and recording attributions are in `fixtures/esc50/LICENSE`; the WAV files are downloaded separately. No project-wide licence has been selected for the original code.
