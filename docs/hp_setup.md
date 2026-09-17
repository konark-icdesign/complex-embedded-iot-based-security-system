# Software on your 8 GB HP

Assumption: HP t640 with Ryzen R1505G, 8 GB RAM, NVMe SSD and Windows 10 22H2. You typed t460 in the latest request; verify the model in `msinfo32` or on its label. Do not install model-specific drivers based on this assumption alone.

**Verdict: this is a reasonable machine for the small reference simulation and a modest single-camera prototype. Actual real-time performance is unmeasured.** The NVMe helps loading and writing; it does not replace CPU capacity or RAM.

| Software | Use | Install now? |
|---|---|---|
| MATLAB, if you already have a valid license | DSP experiments, plots, independent numerical replay | Yes if available; otherwise start with the executed free reference |
| Python 3.12, NumPy, SciPy, Matplotlib | Run the supplied tested simulation and inspect all results | Yes |
| Arduino IDE 2 | Compile/upload UNO R4 firmware and inspect serial data | Yes |
| Arduino UNO R4 Boards core 1.6.0 | Exact official core used in the recorded compilation | Through Boards Manager |
| A small editor, or MATLAB Editor | Read and change source | Use one you already have |
| FFmpeg | Optional MP4 export of simulated frames | Optional; missing it only omits newly generated MP4 |
| GCC/MinGW or WSL | Re-run native C++ sanitizer tests | Optional initially; Arduino IDE is enough to build the board target |
| MQTT broker | Later Wi-Fi architecture | Defer |
| Simulink / heavy neural-network stack | Not required by this implementation | Defer |

MathWorks lists **8 GB minimum and 16 GB recommended** for MATLAB R2026a, with Windows 10 22H2 supported and SSD storage recommended. Thus 8 GB meets the published memory minimum, not a promise of smooth large video workloads. Source: https://www.mathworks.com/support/requirements/matlab-system-requirements.html .

Keep 10-20 GB free as a practical working allowance for MATLAB, packages and recordings; this is a project allowance, not a measured installation size. The current release archive is much smaller. Close unnecessary browser tabs and run one numerical environment at a time. No RAM upgrade is needed just to try this reference. Measure first.

## Start on Windows

1. Extract the project ZIP into a simple folder such as `C:\ECE\night-security`.
2. Install Python from https://www.python.org/downloads/ . In a terminal opened in the project folder, run the README commands. If Windows uses `py` rather than `python`, use `py -3.12` for virtual-environment creation.
3. Run one seed first: `python run_simulation.py --seeds 1`. Open the generated charts and `scenario_results.csv`. Then use ten seeds for the recorded evaluation size.
4. If licensed MATLAB is installed, set this folder as Current Folder and run `addpath('matlab'); run_full_simulation`. This is the outstanding literal MATLAB check. Save its log.
5. Install Arduino IDE from https://www.arduino.cc/en/software . Install Arduino UNO R4 Boards, choose the correct board and open the sketch. First compile without wiring anything.
6. With only the board connected, upload and watch serial at 115200 baud. Verify warm-up and heartbeat behavior before attaching all sensors. Close Serial Monitor before MATLAB opens the same COM port.

## Conservative live targets

| Item | Initial target |
|---|---|
| Audio | Mono PCM, 16 kHz; 2048 samples/frame, 1024 hop |
| Camera acquisition | One USB camera; resize to 320x240 grayscale |
| Camera analysis | 5 frames/s, one ROI excluding windows/corridors if possible |
| Physical telemetry | 10 samples/s |
| Local transport | USB serial, 115200 baud |
| Event video | 5 frames/s; pre/post clips only |
| Neural person detection | Disabled in version 1 |
| Memory behavior | Bounded buffers; no full-night raw video arrays |

Ten seconds of 320x240, 8-bit grayscale at 5 fps uses about 3.84 MB before container overhead; RGB uses about 11.52 MB. Ten seconds of 16-bit mono audio at 16 kHz uses about 0.32 MB. MATLAB/Python, decode buffers and temporary arrays add much more than these payload sizes, but the design does not intrinsically need many gigabytes of ring buffers.

The delivered experiment rendered 160x120 synthetic video, so it does not benchmark 320x240 webcam acquisition or decoding. The measured execution time belongs to the hosted environment, not your HP. Do not copy it into a hardware-performance claim.

## Free route versus MATLAB route

Python is the verified numerical reference in this package. MATLAB is an independent, readable implementation waiting to be run. GNU Octave may run parts of it, but this package has not tested Octave and uses MATLAB table/I/O functions. Do not describe an Octave run as MATLAB execution. MATLAB Runtime alone does not provide the MATLAB editor/interpreter for arbitrary source scripts.
