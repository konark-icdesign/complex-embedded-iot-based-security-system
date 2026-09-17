# Validation record — 17 September 2026

The continuous incident checks ran on GitHub, not on the HP or physical sensors.

The later [detection-quality change](detection_quality.md) has its own comparison and recorded results. At commit `5bd05078df6b171632d88e8e7efde1f01fbf58a4`, 26 Python tests passed and all four continuous sessions still agreed between Python and C with the new room profile: [integration run 35250249408](https://github.com/konark-icdesign/complex-embedded-iot-based-security-system/actions/runs/35250249408). The table below records the earlier incident-workflow change.

Python/C integration and the Arduino target build passed at `bf0efac4fcc6e8a6d87d6298108e71cac9674438`: [run 35248260569](https://github.com/konark-icdesign/complex-embedded-iot-based-security-system/actions/runs/35248260569).

The MATLAB reference passed at `0ce080b1e9eabc30973e463ca1dde53b1ef16e39`: [run 35247858074](https://github.com/konark-icdesign/complex-embedded-iot-based-security-system/actions/runs/35247858074). The MATLAB source is unchanged in the later timestamp commit. Its job ran MATLAB R2026a Update 5; an [execution excerpt](../results/matlab/ci_execution_excerpt.txt) is retained in the repository.

| Check | Result |
|---|---|
| Python regressions | 24 passed |
| C and C++ | Strict warnings, AddressSanitizer and UndefinedBehaviorSanitizer passed |
| C audio features | 64 frames checked, largest difference from Python approximately 5.55e-15 |
| C corroboration | All 32 channel combinations matched Python |
| Two successive incidents | Two distinct evidence packages and two receiver records |
| Network outage and host restart | Active incident resumed, queued alerts delivered, lost acknowledgement retried |
| PC outage | Compiled Arduino core latched fallback while the host was unavailable; two separated incidents delivered |
| Thunder without physical movement | No RED alert |
| Continuous C/Python comparison | Identical incident decisions in all four sessions |
| Original embedded replay | 12,480 ticks, zero mismatches |
| UNO R4 WiFi target | Core 1.6.0, 53,852 bytes flash and 6,908 bytes global RAM |
| MATLAB reference | DSP features, scores/flags, baseline fit, lighting kernels and 52 fusion traces passed |

The C/Python sessions use the same raw simulated audio/images and the actual compiled Arduino logic. Their HTTP receiver runs on loopback inside the GitHub runner. This verifies the integration and retry protocol, not delivery to a real security team.

## Failures fixed during this change

- PC recovery initially failed the acceptance test: a second event overlapped the recovery recording, and the test demanded footage from a period with no PC acquisition. Coverage metadata now marks missing footage; a regression verifies overlap grouping; the separated-event test leaves a quiet interval.
- MATLAB's first execution failed because its sample-rate input loaded as an integer. Converting and validating that input fixed the numerical calculation; the integer-rate regression now passes.
- The final timestamp review separated the audio frame's acquisition time from the processing tick, so the recording window uses the actual audio trigger.

The failed and successful runs remain linked in [the workflow notes](incidents.md). No historical test results were changed to hide them.

## Still unfinished

Actual infrared/video and room-audio validation; quiet-footstep and shared-cause false-alarm work; weather context; physical camera/microphone/serial acquisition and clock mapping; remote endpoint authentication; sensor placement, power and HP performance tests. The C backend covers numerical detection, while Python still owns camera analysis and incident/I/O orchestration.

The old 520-trial results are a separate evaluation. Their 30 misses and 20 false alerts have not been fixed or replaced by the four new integration sessions.
