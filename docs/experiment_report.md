# Simulation report - 17 September 2026

## Verdict

Proceed as a college ECE experiment. The simulation and embedded logic run, but the design is not ready for unattended security use. Keep the measured misses and false alarms visible. MATLAB execution and physical room validation remain outstanding.

## Actual execution

| Item | Result |
|---|---|
| Synthetic evaluation | 520 trials: 52 cases x 10 noise seeds |
| Intrusion trials detected | 160 / 190 |
| Missed intrusion trials | 30 / 190 |
| False alerts | 20 / 330 non-intrusion trials |
| Naive any-sensor false alerts | 170 / 330 |
| Latency among detections | Median 0.25 s; maximum 3.2 s in idealized simulation |
| Synthetic non-intrusion duration | 2.2 hours, fragmented 24-second trials |
| Real sound recordings | 40 clips: 6 train, 4 calibration, 30 evaluation from 25 original source IDs |
| Native regression suite | 12 Python regressions passed; original failures retained |
| Embedded host checks | Strict GCC warnings, ASan and UBSan passed; leak checking unavailable |
| Embedded cross-language replay | 12480 ticks, 0 mismatches |
| Arduino target | UNO R4 WiFi, official Renesas core 1.6.0; compile succeeded |
| Compiled firmware footprint | 53,724 bytes flash; 6,904 bytes global RAM |
| MATLAB | Source provided; NOT RUN |
| Hardware / HP throughput | NOT TESTED |
| Remote alert | Local simulated receiver only; no human contacted |

The repeated cases use the same event schedules and simplified sensor responses. Noise-seed repetition is not independent field validation. Do not advertise 84.2% real-world detection or 93.9% reliability from these counts. No room-level accuracy has been established.

## Unresolved system failures

| Case | Observed | Why |
|---|---|---|
| 31 Audio + PIR only | Missed intrusion; YELLOW | Below the deliberate corroboration requirement |
| 32 Audio + radar only | Missed intrusion; YELLOW | Same evidence tradeoff |
| 51 Silent far entrant outside camera, radar only | Missed intrusion; YELLOW | Insufficient observability |
| 38 Heated moving object | False RED | Camera and PIR can share one harmless cause |
| 42 Nearby outside activity | False RED | Poor placement lets outside activity affect audio, PIR and radar |

These five outcomes repeat across the ten seeds. We did not feed their ground-truth labels into the decision logic to force a pass. They require better boundary sensing, placement and room data, not cosmetic code changes.

## Real-audio challenge

Source: [ESC-50, official dataset](https://github.com/karolpiczak/ESC-50). Six rain/engine clips in fold 1 trained a separate proxy model; four fold-2 clips calibrated it. Thirty fold-5 clips evaluated both that model and the frozen synthetic model. No evaluation clip trained either model. Three clips per category are a small stress check, not a validated benchmark. The 30 clips come from 25 original source IDs.

The proxy treats either approved rain or engine background as normal. It deliberately tests a broader baseline than one real room; this is separate from the context-selected synthetic dry/rain models. The minimum-distance choice can hide suspicious sounds. Engine recordings are not recordings of your PC fan.

| Class | Tested | Proxy model flagged | Synthetic model flagged |
|---|---:|---:|---:|
| rain | 3 | 0 | 3 |
| engine | 3 | 0 | 3 |
| footsteps | 3 | 0 | 3 |
| glass_breaking | 3 | 3 | 3 |
| door_wood_knock | 3 | 1 | 3 |
| door_wood_creaks | 3 | 0 | 3 |
| thunderstorm | 3 | 0 | 3 |
| wind | 3 | 0 | 3 |
| clock_tick | 3 | 3 | 3 |
| coughing | 3 | 3 | 3 |

All six held-out background proxy clips were accepted by the broad model, but all three footsteps were missed. Their source titles describe wood, carpet, and dirt/rocks footsteps. The synthetic model flagged all 30 clips, including every held-out normal proxy. This is strong evidence that attractive synthetic plots do not establish transfer to a real microphone/room. Audio remains an anomaly trigger, not a validated footstep classifier.

## Reproduced mechanisms

- Clean global brightness increase: naive changed area 100%; compensated changed area 0%.
- Local 50x30 change in a 160x120 image: 7.8125% changed area remains after compensation.
- One 0.35 m echo among roughly 3 m echoes: rejected by the causal five-sample median.
- Sustained 1.2 m target: accepted after median and persistence; typical synthetic delay 0.4 s.
- Camera obstruction: central RED can still use audio and physical evidence; obstruction alone stays a health/YELLOW condition.
- PC/USB failure with independently powered board and all three physical inputs: local fallback activates in the model.
- Internet outage, process restart and lost acknowledgment: persistent queue yields one unique local receiver alert after retry. This is not proof of external provider exactly-once delivery.

## Actual debug history

1. Regression `test_green_visits_yellow_before_red` failed: simultaneous qualifying evidence moved directly from GREEN to RED. The transition was fixed; the first failing log is retained.
2. Code inspection found that the evidence ring copied the next 100 ms audio chunk. It was changed to retain only samples already completed at the current timestamp. No claim is made that this inspection was an instrumented failing test.
3. Regression `test_persistent_camera_fault_does_not_merge_separate_incidents` failed: a persistent fault held RED indefinitely and suppressed a later distinct event. Activity-clear timing was separated from health timing; a cleared incident now returns to YELLOW when faults remain.
4. The first sanitizer invocation could not start LeakSanitizer under the hosted process tracer. The rerun disabled leak detection only; address and undefined-behavior checks remained enabled. The board build also contains warnings from the official vendor core. They were retained, not disguised as a warning-free core build.

## Correlation-window sensitivity

With isolated audio, PIR and radar event impulses, a 2-second window missed a 3.2-second delayed third input. Four seconds accepted it. Eight seconds accepted a constructed set of unrelated inputs 7 seconds apart. See `impulse_timing_sensitivity.csv`. Four seconds is a documented prototype compromise, not universal calibration. The companion sustained-sensor sweep shows little difference because sustained signals overlap.

## All primary scenarios

| Scenario | Ground truth | Outcome | First alert delay (s) |
|---|---|---|---:|
| 01_quiet | non-intrusion | NO_DANGER | - |
| 02_fan | non-intrusion | NO_DANGER | - |
| 03_traffic | non-intrusion | NO_DANGER | - |
| 04_sensor_noise | non-intrusion | NO_DANGER | - |
| 05_gain | non-intrusion | NO_DANGER | - |
| 06_camera_noise | non-intrusion | NO_DANGER | - |
| 07_light_on | non-intrusion | NO_DANGER | - |
| 08_light_off | non-intrusion | NO_DANGER | - |
| 09_rain | non-intrusion | NO_DANGER | - |
| 10_thunder | non-intrusion | NO_DANGER | - |
| 11_wind | non-intrusion | NO_DANGER | - |
| 12_door_slam | non-intrusion | NO_DANGER | - |
| 13_object_falls | non-intrusion | NO_DANGER | - |
| 14_bad_echo | non-intrusion | NO_DANGER | - |
| 15_pir_glitch | non-intrusion | NO_DANGER | - |
| 16_radar_glitch | non-intrusion | NO_DANGER | - |
| 17_mic_transient | non-intrusion | NO_DANGER | - |
| 18_frame_drop | non-intrusion | NO_DANGER | - |
| 19_camera_disconnect | non-intrusion | NO_DANGER | - |
| 20_camera_covered | non-intrusion | NO_DANGER | - |
| 21_wifi_outage | intrusion | DETECTED | 0.2 |
| 22_server_offline | intrusion | DETECTED | 1.3 |
| 23_walk_in | intrusion | DETECTED | 0.2 |
| 24_quiet_entry | intrusion | DETECTED | 0.2 |
| 25_early_steps | intrusion | DETECTED | 0.3 |
| 26_avoids_camera | intrusion | DETECTED | 0.3 |
| 27_blocks_camera | intrusion | DETECTED | 0.2 |
| 28_stops_moving | intrusion | DETECTED | 0.2 |
| 29_near | intrusion | DETECTED | 0.4 |
| 30_far | intrusion | DETECTED | 0.2 |
| 31_audio_pir_only | intrusion | MISSED_INTRUSION | - |
| 32_audio_radar_only | intrusion | MISSED_INTRUSION | - |
| 33_camera_pir | intrusion | DETECTED | 0.2 |
| 34_camera_ultrasonic | intrusion | DETECTED | 0.4 |
| 35_camera_unavailable | intrusion | DETECTED | 0.4 |
| 36_delayed_camera | intrusion | DETECTED | 3.2 |
| 37_curtain | non-intrusion | NO_DANGER | - |
| 38_warm_moving_object | non-intrusion | FALSE_ALERT | 0.2 |
| 39_small_animal | non-intrusion | NO_DANGER | - |
| 40_strong_thunder | non-intrusion | NO_DANGER | - |
| 41_rain_impacts | non-intrusion | NO_DANGER | - |
| 42_outside_door | non-intrusion | FALSE_ALERT | 0.3 |
| 43_us_timeout | non-intrusion | NO_DANGER | - |
| 44_silent_mic | non-intrusion | NO_DANGER | - |
| 45_clipped_mic | non-intrusion | NO_DANGER | - |
| 46_frozen_camera | non-intrusion | NO_DANGER | - |
| 47_nonuniform_light | non-intrusion | NO_DANGER | - |
| 48_saturated_camera | non-intrusion | NO_DANGER | - |
| 49_usb_lost_intrusion | intrusion | DETECTED | 1.3 |
| 50_rain_intrusion | intrusion | DETECTED | 0.2 |
| 51_blind_silent_far | intrusion | MISSED_INTRUSION | - |
| 52_stuck_radar | non-intrusion | NO_DANGER | - |

## Outstanding work and files

The ZIP contains Python and MATLAB source, the UNO R4 sketch, exact selected audio files with attribution, baseline fixtures, complete CSV/JSON traces, original failure logs, final test logs, a sample synthetic WAV/MP4 and guides. `docs/hp_setup.md` gives software choices for the 8 GB HP; `docs/dsp_maths.md` explains the mathematics; `docs/learning_and_validation.md` lists practical learning and field-validation steps.

Still required: literal MATLAB execution; continuous physical acquisition and clock mapping; actual microphone/camera/sensor measurements; HP workload benchmarking; real notification transport; power/disk-failure handling; and frozen-model evaluation on held-out room recordings. This project is published on GitHub; no external security alert was sent.

Official references for software and board facts are in `docs/sources.md`. Simulation facts are derived from `results/summary.json`, `scenario_results.csv`, `real_audio_results.csv`, `embedded_replay.json` and the compile/test logs.
