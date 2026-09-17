# Development tasks

## Review the current design

Start with three traces: `01_quiet`, `23_walk_in` and `38_warm_moving_object`. Follow the audio, camera and sensor flags into the fusion score and state. These give a quiet case, a detection and a false alarm.

Then check the individual calculations:

- Audio frame length, hop time and FFT bin spacing.
- Constant-gain behaviour of RMS and normalized features.
- Median filtering with one bad echo and with several bad echoes.
- Correlation-window behaviour with delayed and unrelated inputs.
- Heartbeat timeout, alarm latch and timer rollover in the Arduino core.

Record any changes with the input used, the result before and after, and why the change was made. This is planned review work, not a claim that it has already been completed.

## Problems to investigate

**Soft footsteps:** the small synthetic footsteps were missed. The separate broad rain/engine background model also missed three public footstep clips. The score shows that they were accepted as background; the experiment does not establish one physical cause. Inspect per-feature deviations and vary signal-to-background ratio before changing thresholds.

**Warm moving objects:** camera motion and PIR can share this cause. The current rule cannot distinguish it from some human movements.

**Outside activity:** case 42 models audio, PIR and radar responding beyond the intended room boundary. A lower threshold cannot fix a misplaced sensing boundary.

**Coverage:** audio with just one physical channel does not meet the present RED rule. A silent entrant seen only by radar is also missed. Changing those rules needs corresponding non-intrusion tests.

A door contact, constrained radar range or a camera region of interest are options to investigate. None has been added to the detector yet.

## Implementation work

The continuous incident runner and C numerical core are implemented on the incident-workflow branch; use the Incident pipeline workflow to check their current validation status. Python remains the numerical reference. See `docs/incidents.md` for the investigation, recording, restart and HTTP delivery interfaces.

Run the MATLAB code and record differences. After that, the hardware work includes live acquisition, device-clock mapping, reconnect handling, sensor placement, independent board power and real notification transport.

## Later room tests

Use recordings from separate sessions for training, calibration and evaluation. Do not split overlapping windows from one recording between those sets. Freeze the model before the final evaluation.

Collect empty-room periods using the intended PC, microphone position and gain. Include conditions that actually affect that room: light changes, fan noise, corridor activity and weather if audible. Use consenting volunteers for normal entry, quiet entry, distant movement and stationary presence.

Record ground-truth event times separately from detector outputs. Report missed events, false alerts per empty-room hour, delay, YELLOW duration and sensor uptime. Include the number of separate recordings and sessions, not just the number of overlapping windows.
