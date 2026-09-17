# Architecture and corrections to the brief

## Practical scope

The first build monitors one fixed room, one camera and one microphone. Start with USB serial between PC and Arduino. This separates Internet failure from the local sensor/control link. Moving the local link to Wi-Fi introduces another failure mode without improving the first experiment.

The attached brief says HP t640. The latest message says t460. All sizing here assumes the previously stated **HP t640, Ryzen R1505G, 8 GB RAM, NVMe SSD**. Check the label or Windows System Information before choosing drivers. Nothing in the simulation depends on that PC brand.

| Component | Responsibility |
|---|---|
| PC | Audio FFT/features; baseline deviation; camera change/visibility; evidence history; causal timestamp correlation; incident state; durable alert queue |
| Arduino | Physical inputs; three-sample persistence; five-sample range median; hardware watchdog; local buzzer/LED; heartbeat fallback |
| Microphone | Anomaly sentinel; never proof of footsteps or a human |
| Camera | Local pixel change and visibility health; no person or face detector in this version |
| PIR | Warm moving-source evidence; no identity and weak stationary evidence |
| Radar OUT | Presence evidence; no identity, velocity, range gates or diagnostic heartbeat through this single GPIO |
| Ultrasonic | Confirmation of an object within 1.8 m, if a valid echo exists |
| Notification receiver | Local simulated human-security inbox; persistent unique incident IDs |

## What was corrected

| Brief assumption | Engineering correction |
|---|---|
| Four states, including DANGER ALERT | Three incident states; DANGER ALERT is an action generated on entry to RED |
| Ambiguous event can be RED investigation without DANGER | Ambiguity stays YELLOW. RED produces the alert by definition |
| Multiple independent sensors establish a genuine intrusion | Different sensor technologies can respond to a common harmless cause. No independence or probability claim is justified |
| Audio should reliably catch someone who avoids a camera | Useful hypothesis, not established. Real-audio tests show large transfer failures |
| Black image means tampering | Call it loss of visibility. Darkness, power loss, exposure and covering can look identical |
| A static picture means a frozen camera | Repeated identical frames are suspicious; a quiet scene or compressed stream can repeat frames legitimately |
| Rain report explains the sound | Context can select an approved baseline, but this prototype has no weather classifier or live weather integration |
| Exactly one network transmission | Retries can duplicate transport messages. Unique IDs and receiver de-duplication give one displayed alert in the tested model |
| Local alarm always works after PC failure | Only if the Arduino remains independently powered and its physical sensors see enough evidence |
| Adding sensors makes the experiment realistic | Simulated sensors still use simplified binary response traces, not thermal/radar/acoustic propagation models |

## Mathematical fusion policy

Each channel retains its most recent accepted acquisition timestamp for 4 seconds. A stale historical reading is not renewed merely because the loop runs again. A delayed external packet can be accepted only after clock conversion, sequence validation, and a 0.5-second age check. The end-to-end generated simulation uses one ideal shared clock; real device clock mapping is still required.

| Symbol | Evidence | Points |
|---|---|---:|
| A | Persistent audio anomaly or extreme valid transient | 1.5 |
| V | Local camera change above 1.8% of image | 3.0 |
| P | PIR active for 3 consecutive samples | 2.0 |
| M | Radar active for 3 consecutive samples | 2.0 |
| U | Valid near range after median and persistence | 2.0 |

RED requires at least 5 points **and** one of:

- V plus any one of P, M or U.
- All of P, M and U.
- A plus at least two of P, M and U.

Consequently A+P or A+M alone stays YELLOW. Those are measured missed detections in the deliberately weak-coverage intrusion cases. V+P can detect a silent entrant, but also produces the warm-object false alarm. This is an explicit tradeoff, not an unexplained failure hidden by the score.

Scores are arbitrary, inspectable engineering points. **5.5 points does not mean 55%, 87%, or any other probability.** Fault flags create YELLOW and add zero danger points. Camera motion and camera visibility loss are never counted as two independent sensing methods.

## State and incident handling

GREEN: no recent unusual evidence and no reported health problem.

YELLOW: anomalous evidence, incomplete correlation or degraded sensing. Capture a five-second prebuffer and subsequent evidence. No danger message is generated merely for YELLOW.

RED: the policy is satisfied after passing through YELLOW. Enqueue one incident. Hold RED for at least six seconds. After evidence expires and stays clear for three seconds, return to YELLOW if faults persist, or GREEN if health is normal. This distinction prevents a failed camera from merging every later intrusion into the original incident.

The Arduino buzzer is separately latched until its physical reset input is pressed. Central state cleanup does not remotely silence a latched alarm. This is deliberate and must be included in a bench demonstration.

## Timing

Audio: 16 kHz, 2048-sample frames, 1024-sample hop. Decisions are timestamped at frame end. Physical sampling: 10 Hz. Camera: 5 frames/s at 160x120 in the synthetic experiment. Target initial real camera processing: 320x240 at 5 frames/s after resizing.

The 4-second correlation window is a design setting, not a universally calibrated constant. The impulse timing experiment shows why a shorter window misses delayed confirmation and a longer window can combine unrelated events. Persistent sensor signals overlap even with a short window; their success alone does not validate delayed-event correlation.

## Buffers and retention

The reference run maintains a bounded five-second deque containing completed audio chunks, available camera frames and sensor records. The first event in a captured trial preserves that history and up to fifteen seconds after the trigger. Example WAV, MP4, frame timestamps and sensor CSV are included. Raw frames use low resolution; they are not evidence of a real room.

The simulation saves the first incident's bounded media capture per selected trial. A continuous deployment needs per-incident file rotation, disk quotas, error handling when storage fills, and retention rules. These are not claimed complete. Notification persistence uses SQLite; edge RAM does not survive an Arduino power cycle.

## Fallback and power

No PC heartbeat for over two seconds enables degraded operation. PIR, radar and near range must all remain valid/active for ten 100-ms samples before the local alarm latches. The PC can be offline, but the board must have a separate supported power source. USB-only power from a failed PC is not a reliable fallback supply. A complete loss of room power needs suitable backup power; that is outside this simulation.

The physical fallback is weaker than central processing. It can miss an entrant outside ultrasonic coverage and can false-alarm on a common cause affecting all inputs. It cannot send an Internet message on its own in the USB-first firmware.
