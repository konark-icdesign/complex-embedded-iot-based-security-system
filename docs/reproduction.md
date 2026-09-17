# Running the checks

The README gives the Python setup and full simulation command. `requirements-tested.txt` records the numerical package versions used in the earlier run.

## Smaller audio experiment

After installing the root requirements:

```text
cd experiments/audio_room
python run_audio.py
python -m unittest test_audio -v
```

This imports the root DSP implementation. Its results are separate from the 52-scenario system test.

## C++ host checks

From the repository root, with GCC and Make installed:

```text
make embedded
make sanitize
python scripts/verify_embedded_replay.py
```

In the recorded hosted environment, LeakSanitizer was unable to operate under process tracing. That run used `ASAN_OPTIONS=detect_leaks=0` for `make sanitize` and `--no-leak-check` for the replay script. AddressSanitizer and UndefinedBehaviorSanitizer remained enabled. Use normal leak checking where supported.

The replay compares physical sensor filters and fallback behaviour, not the entire Python detector. The Arduino target compilation is recorded separately in `results/arduino_compile_log.txt`.

## MATLAB and board

First run the Python simulation to generate `fixtures/matlab_reference.mat` and the traces. In MATLAB:

```matlab
addpath('matlab');
run_full_simulation
```

The GitHub MATLAB reference job runs this function in MATLAB R2026a and saves its execution log and parity outputs. It checks the original kernels and fusion traces, not a complete live MATLAB service. See `validation.md` for the recorded run.

Open `firmware/night_security/night_security.ino` in Arduino IDE 2. Select UNO R4 WiFi; the recorded compilation used Renesas UNO core 1.6.0. Physical tests are still pending.

## Outputs

| File | Contents |
|---|---|
| `results/summary.json` | Aggregate synthetic results and execution information |
| `results/scenario_results.csv` | One row for each of the 52 scenarios |
| `results/monte_carlo_results.csv` | All noise-seed repetitions |
| `results/traces/` | Individual sensor and state histories |
| `results/real_audio_results.json` | Public-recording evaluation |
| `results/integrated_regressions.log` | Python regression run |
| `results/integrated_embedded.log` | Native C++ logic checks |
| `results/integrated_replay.log` | C++/Python replay |
| `experiments/audio_room/results/` | Quiet-room audio experiment |

Reruns replace derived outputs. The first ESC-50 download needs internet access. Missing audio files are reported as `NOT_RUN_INCOMPLETE_DATA`; they must not be confused with an executed real-audio check. FFmpeg is optional for MP4 output.

Historical GitHub evidence is separate: `evidence/github/` contains committed snapshots of selected original runs. `python scripts/archive_runs.py --verify` checks their file lengths and SHA-256 hashes without network access or a simulation rerun. See [debugging history](debugging_history.md) for the index and explicit archive omissions.

The notebook in `notebooks/` runs the same steps and prints the Git revision. Hosted Colab execution is still unverified.

The continuous incident and C-core commands are in [incidents.md](incidents.md). They use new output directories and do not replace the historical scenario results.

For a PDF export, install `requirements-report.txt` and run `python scripts/build_report.py`. This also regenerates the experiment notes; the underlying measurements come from the saved result files.
