# Understand it, then decide whether to build it

## Current verdict

Proceed as a college DSP/embedded experiment with explicit limitations. Do not present this version as a reliable unattended security product. The best next work is room-specific calibration and a small physical bench, not adding a large neural network or publishing a perfect-looking demo.

The point of the source, seeds, failures and recordings is that another person can reproduce the measurements and question the assumptions. No wording can substitute for understanding the code. Do not claim physical testing, original field data or literal MATLAB execution that has not happened.

## A manageable learning sequence

| Session | Do yourself | Evidence you should produce |
|---|---|---|
| 1 | Run one seed; inspect 01_quiet, 23_walk_in and 38_warm_moving_object | Explain one success and one false alarm |
| 2 | Read `dsp.py`; calculate frame length, hop and FFT bin spacing by hand | A short page showing the calculations |
| 3 | Multiply a waveform by 0.5 and 3; compare RMS and normalized features | Plot and explain why one changes and the other does not |
| 4 | Inspect FFT of hum, noise and a transient | Describe what the plot shows without calling it human identification |
| 5 | Work the five-number median example; modify one echo into three bad echoes | Demonstrate the filter's limits |
| 6 | Change correlation span and inspect impulse timing results | Explain missed late evidence and accidental coincidences |
| 7 | Trace the C++ heartbeat, millis rollover and alarm latch | Show which variable changes at each transition |
| 8 | Run MATLAB code and save its actual execution log | Record any mismatch honestly and fix it |
| 9 | Bring up the Arduino with one sensor | Real timestamps and measurements, labelled as a bench test |
| 10 | Collect empty-room and volunteer walk-in data | A small labelled dataset with untouched evaluation recordings |

These are work sessions, not a claim that ten days is enough regardless of your starting knowledge. If substitution, fractions or C syntax slow you down, reduce a session to one calculation or function and explain it aloud before continuing.

## Questions a reviewer can reasonably ask

**Why not just increase the number of sensors?** Because shared causes, poor placement and missing coverage remain. The tested heated object triggers a camera and PIR together. More correlated readings do not create a mathematical proof of a person.

**Why were footsteps missed in the real clips?** A broad background model accepted their feature shapes. The chosen ESC-50 clips also differ from an indoor installation; inspect their source attributions. This is a domain-transfer stress test, not proof of indoor accuracy. The only honest next step is room data collected with the intended microphone.

**Where is the AI?** There is no deep model in version 1. Robust statistics and explicit rules are sufficient for an instructive prototype. Adding a classifier is justified only if held-out room data shows a useful improvement.

**What does RED prove?** That the stated rule was satisfied by current accepted evidence. It does not prove identity, intent or criminal activity. The notification should say 'correlated unusual activity'.

**Why do simulated detections look so quick?** Inputs have idealized event timing and simple filters. The 0.25-second median excludes realistic acquisition, device hold times, camera decoding, scheduling and network delays. Measure those on the HP before making a latency claim.

**Is a rectangle a tested person detector?** No. It tests local image-change mathematics. Calling it a person detector would misrepresent the experiment.

## Room-data protocol before any security claim

Keep training, tuning and final evaluation on different recordings/nights. Splitting overlapping windows from one recording across those sets causes leakage. Freeze the model before evaluating the held-out set.

Collect ordinary empty-room periods with the actual PC fan, microphone position and gain. Record dry and rainy sessions if rain materially changes this room. Include light changes, distant corridors, safe object/door sounds, curtains/fans and occasional normal activity. The suggested 1-2 weeks is an opportunity to encounter different conditions, not a guarantee of adequate coverage.

Use consenting volunteers for normal entry, quiet entry, far-range activity, partial camera obstruction and stationary presence. Log ground-truth event start separately from detector logs. Do not train the baseline on those abnormal trials.

Measure event recall, missed-event reasons, false alerts per empty-room hour, YELLOW burden, alert latency distribution and sensor uptime. Report the number of nights, sessions and distinct event recordings. The delivered balanced scenario counts cannot estimate real field precision because the real occurrence rate is unknown.

Predefine a modest demonstration acceptance criterion. For example, report results across at least three separate nights and twenty walk-ins before discussing improvements. These numbers organize a college experiment; they do not certify security reliability. If misses remain, state them instead of lowering thresholds after seeing the final evaluation.

## Concrete changes justified by the failures

1. Aim the sensors at an actual restricted boundary. Reduce radar range/gates if the chosen UART-configurable module supports it; mask corridor/window regions in the camera. Measure the effect on outside activity.
2. For a single-door room, a magnetic door contact is a sensible optional next sensor. It measures the boundary directly. It still cannot tell whether an opening was authorized, and must be simulated and bench-tested before being counted.
3. Keep the microphone as a trigger and evidence recorder until room data establishes its detection limits. Do not make it a required channel for every RED; the quiet-entry test needs physical/visual paths.
4. Use suitable IR illumination/night camera if visual evidence is needed in true darkness. An ordinary webcam cannot extract missing light from mathematics alone.
5. Only after those measurements, consider a lightweight person detector as another measured input. Retain camera-free fallback and document its blind spots.

## Work remaining outside this simulation

- Run the supplied MATLAB implementation and resolve any real discrepancies.
- Connect the actual microphone, camera and serial inputs into a continuous service; benchmark dropped frames, timing and memory on the HP.
- Add bounded session-aware device clock mapping and reconnect handling to live acquisition.
- Implement a real notification transport and receiver with stable unique incident IDs; this package only exercises a local receiver.
- Decide disk retention and handle full disks and process interruption during evidence writing.
- Check wiring, sensor warm-up, field of view, power independence and buzzer behavior.
- Obtain room-specific data and repeat the held-out evaluation.

The GitHub repository keeps all modules, repeatable experiments and known failures together.
