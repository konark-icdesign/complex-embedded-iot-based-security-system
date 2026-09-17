# Reproducing and interpreting this project

## Scope

One repository contains the whole offline security-system simulation: audio, camera, PIR/radar/range filtering, fusion, Arduino fallback logic and a durable local alert receiver. The quiet-room audio experiment is an additional module check using the same source code.

## Online route

Open `notebooks/run_project.ipynb` through the Colab link in the README. The notebook installs dependencies and runs the stages in order. It prints the Git revision being evaluated. Its code cells have been syntax-checked; Colab itself has not been exercised in this development environment.

## Local route

Use the commands in the README. Download the declared ESC-50 subset before the integrated run. The audio is downloaded separately to keep Git history small; its attribution and manifest are tracked. If files are missing, the real-audio result explicitly says NOT_RUN_INCOMPLETE_DATA. The synthetic scenarios can still run.

`python run_simulation.py --seeds 10` regenerates the 520 trial results, plots, MATLAB fixtures and example media. FFmpeg is optional for video export. `--seeds 1` generates a smaller demonstration, not the published 520-trial count.

The MATLAB reference consumes fixtures from the Python simulation and has not been run here. The Arduino board compilation log comes from the prior build of unchanged firmware. Current C++ host tests and the 12,480-tick replay are separate from that target build and from any physical validation.

## Evidence

- `results/integrated_run.log`: latest full synthetic execution.
- `results/integrated_regressions.log`: current Python regression checks.
- `results/integrated_embedded.log`: current native C++ logic checks.
- `results/integrated_replay.log`: current sanitized C++/Python replay.
- `results/summary.json`: aggregate trial counts and execution status.
- `results/scenario_results.csv` and `results/traces/`: inspect individual decisions.
- `results/real_audio_results.json`: public-recording proxy challenge.
- `experiments/audio_room/results/`: quiet-room synthetic sound checks.
- `results/arduino_compile_log.txt`: prior actual UNO R4 WiFi compilation.

A regression pass does not mean every intrusion was detected. Preserve the missed intrusions and false alarms when discussing results. No measured HP throughput, actual room accuracy, real notification transport or physical sensor validation is claimed.
