# Night security project

The idea is to monitor a quiet room using sound, a camera and a few sensors. If something unusual happens, the system should compare the evidence before raising an alarm.

This repository is an early simulation of that idea. There is working code and recorded test output, but several parts of the intended system are missing.

## How this version was made

The project requirements came from the repository owner. AI was used heavily to write the simulation, firmware draft, tests and documentation. The numerical runs and compiler checks recorded here were carried out in the hosted development environment with AI assistance.

This version was uploaded on 17 September 2026. There is no earlier development history established by the files here. The upload should not be presented as evidence of an older, completed college project.

The amount of documentation grew faster than the implementation. Some code is quite compressed and needs cleanup. The notes and test results are useful working material, but they do not mean the project has been built, tested in a room or fully reviewed by its owner.

## What currently works

Python generates the test inputs and runs the audio, camera and sensor calculations. The fusion code combines detections from the last four seconds.

An unusual sound can put the system into YELLOW. It checks camera motion, PIR, radar and ultrasonic evidence alongside it. Audio alone cannot produce RED. For example, audio plus PIR plus radar can meet the current alarm rule.

The camera and sensors are checked continuously. There is no separate audio-triggered investigation that goes back through infrared footage yet. The camera input is generated grayscale imagery; infrared-camera behaviour has not been validated.

Arduino C++ code handles sensor filtering and a local fallback alarm. It has been compiled for the UNO R4 WiFi and its logic has been tested on a computer. It has not been tested on a physical board. The full detection pipeline is still Python, not C.

## Results so far

The full run contains 52 scripted scenarios repeated with 10 noise seeds.

| Check | Recorded result |
|---|---|
| Simulated intrusion trials | 160 detected, 30 missed, out of 190 |
| Simulated non-intrusion trials | 20 false alerts out of 330 |
| Alarm on any single input, for comparison | 170 false alerts on those same 330 trials |
| Public audio recordings | 40 clips: 6 training, 4 calibration, 30 evaluation |
| Footsteps in the public-audio check | All 3 evaluation clips missed by the broad background model |
| Quiet-room audio experiment | All 10 soft-footstep trials missed |
| C++ sensor filtering and fallback replay | Matched Python on 12,480 ticks |
| MATLAB | Source written; not run |
| Physical hardware and HP performance | Not tested |

The repeated trials share event templates. These counts describe the generated tests, not accuracy in a real room. The C++ comparison covers sensor filtering and fallback logic, not the whole detection pipeline.

Some failures have clear causes. Audio with only PIR or only radar does not meet the current alarm rule. A warm moving object can activate both the camera and PIR. Sensors responding to activity outside the room can also produce a false alarm. Lowering the threshold would change which errors occur; it would not resolve all of these problems.

Details are in [the experiment report](docs/experiment_report.md), [individual scenario results](results/scenario_results.csv) and [the latest run log](results/integrated_run.log).

## What still needs work

- Implement and test the core detection calculations in C.
- Add the intended audio-triggered review of buffered, timestamped evidence.
- Investigate soft-footstep misses and the observed false alarms.
- Run the MATLAB code and check its outputs.
- Connect a real microphone, camera and Arduino, including clock synchronization.
- Test infrared imaging and sensor placement in the actual room.
- Implement real remote notifications. The current receiver is a local SQLite simulation.
- Review the code and assumptions module by module before making stronger claims.

## Run the simulation

Use Python 3.12 and a virtual environment. On Windows, from the project folder:

```text
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python scripts/fetch_real_audio.py
python run_simulation.py --seeds 10
python -m unittest discover -s tests -p "test_*.py" -v
```

On Linux or macOS, activate the environment with `source .venv/bin/activate`.

The download step fetches the public audio subset. A quick run can use `--seeds 1`; that runs 52 trials instead of 520. Rerunning overwrites derived results. If the recordings are missing, the real-audio check reports that it was not run. Synthetic results are still separate from that check.

The [online notebook](https://colab.research.google.com/github/konark-icdesign/complex-embedded-iot-based-security-system/blob/main/notebooks/run_project.ipynb) runs the same stages. Its code was syntax-checked, but the notebook has not been executed on Colab.

For the smaller audio experiment:

```text
cd experiments/audio_room
python run_audio.py
python -m unittest test_audio -v
```

It uses the shared DSP code, with synthetic PC-like background noise and disturbances. No recording of the intended room has been supplied.

From the repository root, with GCC and Make installed:

```text
make embedded
make sanitize
python scripts/verify_embedded_replay.py
```

The recorded hosted sanitizer run needed leak checking disabled because of the environment's process tracing. AddressSanitizer and UndefinedBehaviorSanitizer still ran. That exception is described in the logs; it is not required on every machine.

For MATLAB, first generate the fixtures with the Python simulation, then run:

```matlab
addpath('matlab');
run_full_simulation
```

This is a command for a future MATLAB run, not a record of one already completed.

For the Arduino build, open `firmware/night_security/night_security.ino` in Arduino IDE 2 and select UNO R4 WiFi. The recorded build used the official Renesas UNO core 1.6.0. See [hardware notes](docs/hardware.md) before attempting wiring.

## Where to look

- [Architecture](docs/architecture.md) and [DSP calculations](docs/dsp_maths.md)
- [HP software setup](docs/hp_setup.md)
- [Reproduction notes](docs/reproduction.md)
- [Learning and validation notes](docs/learning_and_validation.md)
- [Sources](docs/sources.md)

The longer documents were prepared with AI assistance too. They describe the current experiment and proposed hardware work; they are not records of physical experiments.

## Dataset and licence

The audio challenge uses [ESC-50](https://github.com/karolpiczak/ESC-50), by K. J. Piczak. Its licence and recording attributions are retained in [fixtures/esc50/LICENSE](fixtures/esc50/LICENSE), with source URLs and hashes in the manifest. Audio files are downloaded separately.

No project-wide licence has been selected for the original code. The ESC-50 licence applies to that external dataset, not automatically to this whole repository.
