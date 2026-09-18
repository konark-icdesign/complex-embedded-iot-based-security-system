# Remaining system resilience simulation

This simulation was added after the earlier scenario, DSP and incident-workflow tests. It targets cases that still needed system-level stress testing: benign multi-sensor activity, missing/degraded sensors, local operation during a network/host outage, and buffered event delivery after connectivity returns.

It is a **synthetic software simulation only**. It does not validate the real UNO R4, microphone, camera, radar, ultrasonic sensor, room acoustics, Wi-Fi link, or HP t640 deployment.

## Run

```text
python scripts/system_resilience_sim.py
```

The run is deterministic with seed `20260919` and uses 12,000 trials.

## Model

Each trial generates normalized scores for audio, radar, ultrasonic, PIR and camera. The fusion stage uses fixed weights:

```text
audio       0.20
radar       0.24
ultrasonic  0.18
PIR         0.14
camera      0.24
```

Missing sensors are excluded and the remaining weights are renormalized. Multiple strong modalities receive a small agreement bonus. The state thresholds in this standalone stress model are:

```text
GREEN   fusion < 0.35
YELLOW  0.35 <= fusion < 0.68
RED     fusion >= 0.68
```

Authorized-entry trials are prevented from escalating to RED in this model because they represent a valid local authorization context.

## Result from the recorded run

| Metric | Result |
|---|---:|
| Threat detection recall | 99.09% |
| RED precision | 100.00% |
| Overall false-positive rate | 0.00% |
| Benign multi-sensor RED rate | 0.00% |
| Outage intrusion locally detected | 99.11% |
| Sensor-fault cases avoiding RED | 100.00% |
| Median buffered-event delivery | 95.9 s |
| 95th percentile buffered-event delivery | 175.9 s |

State distribution:

| Scenario | GREEN | YELLOW | RED |
|---|---:|---:|---:|
| authorized | 0.00% | 100.00% | 0.00% |
| benign | 62.85% | 37.15% | 0.00% |
| intrusion | 0.00% | 0.92% | 99.08% |
| normal | 100.00% | 0.00% | 0.00% |
| outage intrusion | 0.00% | 0.89% | 99.11% |
| sensor fault | 98.92% | 1.08% | 0.00% |

For outage trials, the local decision path remains active. Events are modeled as buffered locally and retried every five seconds after a simulated outage lasting 10 to 180 seconds.

## Interpretation

The state machine behaves as intended under these assumptions: benign activity does not reach RED, sensor failures do not create RED alerts, and intrusion decisions remain local when the network/host path is unavailable.

The 100% RED precision is **not a real-world accuracy claim**. It mainly shows that the current synthetic benign and intrusion distributions are still too cleanly separated. Real rooms will have more overlap from fans, doors, traffic, lighting changes, radar multipath, sensor mounting, pets and ordinary human activity.

The next useful stress test is therefore an adversarial/noisy synthetic set with deliberately overlapping benign and intrusion distributions, followed by physical room data.
