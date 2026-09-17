# Room security prototype

A room-monitoring project using audio, a camera, PIR, radar and ultrasonic range. The aim is to check whether several readings point to the same unusual event before raising an alarm.

## Project status

This project combines a physical embedded system with a simulation and validation environment.

The physical setup currently includes an Arduino UNO R4 WiFi, an HP t640 thin client, a TP-Link router, and PIR, radar and ultrasonic sensors. Sensor circuits and individual sensor interfaces are being checked and integrated. Full end-to-end testing of the complete system is still in progress.

The simulation is used to develop and test the signal processing, camera processing, filtering, evidence fusion, failure handling and replay logic before and alongside physical testing. Simulation results are not physical-room measurements.

### Current validation status

| Area | Status |
|---|---|
| Python simulation | Executed |
| C/C++ embedded replay | Executed |
| Arduino UNO R4 WiFi firmware | Compiled; hardware integration in progress |
| Individual sensors and circuits | Testing in progress |
| HP t640 processing node | Available for integration |
| TP-Link local network | Available for integration |
| MATLAB implementation | Source included; runtime execution pending |
| Complete hardware integration | In progress |
| Full room validation | Not yet complete |

Results will be identified by their source:

- **SIMULATION** — synthetic signals or replay traces
- **HARDWARE_COMPONENT** — an individual sensor or circuit test
- **HARDWARE_INTEGRATION** — multiple physical components operating together
- **FIELD_TEST** — operation in the intended room or environment

## Background

The initial idea and room requirements were developed around 2022. The project was revisited and organized for GitHub in September 2026. The current public history records the upload and later development work; it does not represent the complete history of the original idea.

## Current implementation

The main simulation is Python. The continuous incident runner can use a C core for audio features, anomaly scoring and corroboration; Python handles recording, incident state and event handling. The Arduino firmware provides sensor filtering and fallback logic for the embedded path.

An unusual sound puts the system into YELLOW. The fusion code checks detections within a rolling four-second window. Audio alone cannot trigger RED; audio together with PIR and radar can. Camera activity and physical evidence are also considered in the fusion logic.

The continuous runner opens an investigation, retains five seconds of earlier evidence, collects eight seconds after the trigger and replays recorded grayscale frames. Each incident gets its own bounded evidence capture for debugging and replay.

## Continuous incident run

On Linux with Python dependencies, GCC and Make:

```text
make incident-build
python run_incidents.py --c-library build/libdetection.so
```

This runs network-loss, host-restart, PC-failure and thunder scenarios using a controlled local receiver. It is a validation workflow and does not replace physical testing.

## Simulation results

| Check | Result |
|---|---|
| Synthetic evaluation | 52 scenarios, repeated with 10 noise seeds |
| Intrusions | 160 detected and 30 missed out of 190 trials |
| Non-intrusions | 20 false alerts out of 330 trials |
| Public audio check | 30 evaluation clips; all 3 footstep clips missed by the broad background model |
| Quiet-room audio check | All 10 soft-footstep trials missed |
| C++ sensor/fallback replay | 12,480 ticks matched Python |

The trials repeat simple event templates. These results describe the simulation, not accuracy in an actual room. Known failures are retained in the experiment notes instead of being hidden.

## Run the simulation

From the project folder, using Python 3.12:

```text
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python scripts/fetch_real_audio.py
python run_simulation.py --seeds 10
python -m unittest discover -s tests -p "test_*.py" -v
```

On Linux/macOS, activate with `source .venv/bin/activate`. Use `--seeds 1` for a quicker run. The first audio download needs internet access. For C++ host tests, MATLAB instructions and the smaller audio experiment, see `docs/reproduction.md`.

## Next work

- Complete sensor and circuit integration.
- Connect the Arduino, thin client, router, camera and microphone.
- Validate acquisition timing and communication on the physical system.
- Test the detection pipeline using recordings from the actual room.
- Investigate quiet footsteps, warm-object false alarms and activity outside the room.
- Run the MATLAB implementation and document the result.
- Add and test the final notification path.

## Documentation

- `docs/architecture.md` — system design and fusion policy
- `docs/dsp_maths.md` — DSP calculations
- `docs/hardware.md` — hardware plan and wiring information
- `docs/hp_setup.md` — HP thin-client setup
- `docs/learning_and_validation.md` — development and validation plan
- `docs/experiment_report.md` — simulation results and known failures
- `docs/debugging_history.md` — debugging history and preserved run evidence
- `experiments/audio_room/` — focused quiet-room audio experiment

The audio tests use [ESC-50](https://github.com/karolpiczak/ESC-50). Licence and recording attributions are in `fixtures/esc50/LICENSE`.

## AI and tooling

AI tools were used as development assistants for selected code, documentation and test scaffolding. The author made the project decisions, reviewed the implementation and is responsible for the reported results.

## Scope

This is an engineering prototype under active physical development. It is not yet a production security installation and does not claim guaranteed detection, zero false alarms, completed field validation or real-world security performance.
