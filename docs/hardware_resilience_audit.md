# Hardware-resilience audit

This audit was added after the earlier synthetic scenario work because those results did not exercise the actual UNO R4 controller logic closely enough.

The tests here execute the same C++ `Core` used by `firmware/night_security/night_security.ino` on a host compiler. They model timing, sensor samples, dropouts and host-health messages. They are **not** an electrical simulation of the RA4M1, PIR, radar, ultrasonic module, USB hardware or power supply, and they are not physical-room validation.

## Problems found

### 1. Stale ultrasonic samples survived a long sampling gap

Before the fix, a gap above 250 ms reset `used_` but did not reset the circular-buffer cursor. A new 3.50 m sample after the gap could therefore report an old 0.50 m value.

The gap reset now clears both the valid-count and cursor.

### 2. One missed ultrasonic echo erased all range history

The old logic cleared the five-sample median and near-persistence state on every invalid echo. In a deterministic test with one missed echo every ten samples, continuous PIR + radar + a real 1 m target could fail to reach the local fallback alarm.

The revised logic marks every invalid echo as a range fault but tolerates up to two consecutive invalid echoes before clearing the range-persistence state. Three consecutive invalid readings make the range channel stale and clear it.

### 3. Transport heartbeat could hide a dead host pipeline

The old `HB` command both proved transport activity and suppressed autonomous fallback. A serial process could therefore continue sending `HB` even if audio, camera or fusion processing had stopped.

The protocol now separates:

- `HB`: transport/process activity only; it does **not** suppress fallback.
- `HEALTH`: the host acquisition/fusion pipeline is healthy and fresh.
- `UNHEALTHY`: explicitly mark the host pipeline unhealthy.

Only a recent `HEALTH` message suppresses local fallback.

The physical live adapter still has to implement a meaningful health check. Merely changing the command string is not a substitute for checking audio, video, board-stream freshness and fusion progress.

### 4. Serial packet loss was not externally visible

The old firmware incremented the sample sequence only after confirming USB buffer space. If a packet was skipped because the serial buffer was full, the host could not infer that a board sample had been lost.

The sequence now advances for every board sample. A skipped serial write therefore creates a sequence gap. The packet also includes a cumulative `serial_drops` counter.

### 5. Important board state was missing from the serial packet

The old packet did not expose the board's filtered ultrasonic `near` result or fallback-alarm provenance. The revised packet carries both, plus degraded state and serial-drop count.

### 6. Audio callback timing was unrealistically strict

The old stream reset its DSP state whenever two chunks differed from exact continuity by more than 1 microsecond. That is too strict for wall-clock callback timestamps on a normal PC.

The stream now allows 5 ms of timestamp jitter, records discontinuities, and still resets on larger gaps. Empty audio chunks are reported as invalid acquisition events instead of silently discarding buffered DSP state.

The physical acquisition layer should still derive timestamps from the audio sample clock where possible.

### 7. Camera recovery could create false motion

After a camera outage, the old code retained the last pre-outage frame. The first recovered frame could be compared against a stale image and reported as motion.

A sustained missing-camera condition now clears the comparison reference. A frame-size change is also treated as a health fault instead of entering the motion calculation.

## Deterministic stress simulation

`tests/hardware_stress.cpp` runs the actual embedded `Core` logic with synthetic hardware-like faults. It uses a fixed deterministic pseudo-random sequence so CI can repeat it.

The local run used 5,000 trials per condition, ten seconds per trial.

Representative results from the revised logic:

| Stress | Result |
|---|---:|
| 0% ultrasonic echo loss | 100% fallback detection within 10 s; mean ~1.50 s |
| 1% echo loss | 100%; mean ~1.51 s |
| 5% echo loss | 100%; mean ~1.54 s |
| 10% echo loss | 100%; mean ~1.59 s |
| 20% echo loss | 100%; mean ~1.77 s |
| 10% false-near range glitches while the real range is 3 m | 0% fallback alarms in the deterministic test |
| 20% false-near glitches | ~0.1% fallback alarms |
| 30% false-near glitches | ~2.66% fallback alarms |
| 1% of loop intervals stretched to 300 ms | 100% detection within 10 s |
| 5% stretched intervals | ~99.98% |
| 10% stretched intervals | ~96.14% |

These numbers describe **this synthetic stress pattern**, not expected field accuracy. The 300 ms test in particular is an artificial scheduler-stall experiment, not a measured UNO R4 timing distribution.

## Electrical work still not solved

The exact PIR, radar, ultrasonic, microphone, camera and alarm parts are not frozen. Until their part numbers are known, the project cannot honestly claim a complete electrical simulation.

In particular, a sensor powered from 5 V does not automatically produce a guaranteed UNO-R4-compatible logic HIGH. The actual output-high/output-low specifications must be checked before direct wiring. Level translation or buffering may be required.

Power-loss fallback also needs independent board power. If the UNO is powered only from the HP USB port, losing the HP can remove the controller that is supposed to provide local fallback.

## Remaining hardware validation

The next physical stage must measure:

1. sensor output voltage levels and idle states,
2. ultrasonic missed-echo rate and range distribution in the intended room,
3. PIR hold/retrigger timing,
4. radar behaviour with fans, curtains, stationary people and activity outside the room,
5. UNO loop timing and sample gaps under USB traffic,
6. USB reconnect and sequence-gap handling,
7. independent power behaviour,
8. watchdog recovery,
9. real audio callback timing and dropped buffers,
10. real camera frame rate, freezes, shape changes and reconnects.

Passing the host stress tests means the controller logic is better defended against these failures. It does not replace those measurements.
