# System design

The planned setup is one room, one microphone and one camera, with PIR, radar and ultrasonic sensors connected to an Arduino. The PC handles audio, images and the main decision. USB serial is the planned local link.

The current implementation simulates these inputs. It does not acquire live room data.

## Responsibilities

| Part | Current job |
|---|---|
| Python on the host | Audio features, image changes, simulated sensor filtering, fusion and a local alert queue |
| Arduino C++ | Sensor filtering, watchdog, heartbeat timeout and a latched local alarm |
| MATLAB | Separate calculation and replay source, awaiting execution |

PIR, radar and range readings provide different kinds of evidence, but can share a harmless cause. None identifies a person. The camera detects image changes; it has no person detector or infrared-specific model.

## From sound to an alert

1. A persistent audio anomaly or an extreme valid transient becomes audio evidence.
2. Any recent evidence or sensor-health fault puts the central state into YELLOW.
3. The fusion rule combines recently accepted audio, camera and physical detections.
4. Qualifying evidence moves YELLOW to RED and creates an incident.

Sensors and camera processing run continuously. The requested deeper investigation of buffered infrared footage after an audio trigger remains to be implemented.

## Current fusion rule

Each channel retains its most recent accepted timestamp for four seconds.

| Symbol | Reading | Points |
|---|---|---:|
| A | Audio anomaly | 1.5 |
| V | Changed image area above 1.8% | 3 |
| P | PIR active for three samples | 2 |
| M | Radar active for three samples | 2 |
| U | Near range after median filtering and persistence | 2 |

RED needs at least five points and one of these combinations:

- Camera plus PIR, radar or near range.
- PIR, radar and near range together.
- Audio plus at least two of the three physical channels.

These points are weights, not probabilities. Audio plus PIR alone stays YELLOW. That avoids some weakly supported alerts, but misses the corresponding intrusion cases. Camera plus PIR can detect a quiet entrant and can also react to a warm moving object.

The four-second window is a provisional setting. In the impulse experiment, two seconds missed a third input delayed by 3.2 seconds; eight seconds combined unrelated inputs spread over seven seconds. See `results/impulse_timing_sensitivity.csv`.

## State clearing

GREEN means no recent evidence or reported fault. YELLOW means suspicion or degraded sensing. RED means the correlation rule was met.

RED lasts at least six seconds. After evidence expires and activity stays clear for three seconds, the state returns to GREEN, or YELLOW if a fault remains. A persistent camera fault must not keep two separate incidents joined forever.

The Arduino alarm is separately latched and requires its reset button. Clearing the central state does not automatically clear that latch.

## Timing and capture

The audio calculation uses 16 kHz samples, 2048-sample frames and a 1024-sample hop. Feature timestamps refer to completed frames. The integrated loop consumes them in 100 ms steps and uses the loop time for fusion. It therefore quantizes audio timing rather than preserving every exact frame timestamp in the fused trace.

Physical inputs are sampled at 10 Hz and camera frames at 5 Hz. The generated experiment uses a shared clock. `Fusion.update` supports capture timestamps with an age check, and `PacketGate` has separate freshness tests; a live acquisition service connecting these pieces and mapping device clocks has not been implemented.

For the selected capture trial, a five-second buffer holds completed audio chunks, available frames and sensor records. The first trigger preserves the preceding data and up to fifteen seconds afterwards. Continuous multi-incident storage, disk limits and write-failure recovery remain open tasks.

## Loss of the PC connection

After more than two seconds without a heartbeat, the Arduino fallback requires PIR, radar and near range together for ten 100 ms samples before latching the alarm. It needs independent power if the PC loses power. It cannot send an internet notification on its own in the current sketch.

A distant entrant outside ultrasonic coverage can be missed by this fallback. This needs a placement and coverage test before hardware deployment.

## Notification test

SQLite stores queued incidents and a local receiver table. Retries use the same incident ID, so the receiver displays one record after restart or a lost acknowledgement. No external notification provider is connected. The current IDs also need a production session/persistence strategy before use across real service restarts.
