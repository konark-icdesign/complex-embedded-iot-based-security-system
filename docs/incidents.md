# Continuous incident workflow

This adds a continuous simulation alongside the older 52 independent cases. It feeds raw synthetic audio and grayscale images into the detector and raw physical inputs into the compiled Arduino core. There is no scenario label inside the incident decision function.

`RoomStream` accepts completed audio chunks, optional timestamped frames and filtered board readings. `IncidentJournal` opens YELLOW, copies the prior five seconds, collects eight more seconds and saves each incident separately. Recent evidence must still satisfy the four-second corroboration rule. Multiple outputs from the camera remain one V channel.

The journal persists an active incident, sequence gate, frozen model identity and streaming FFT state. Reopening it continues the same acquisition clock and sample alignment. Stale, duplicate, future and wrong-session packets are rejected. Mapping a rebooted board's clock into that host clock remains work for the physical adapter.

RED immediately drives the local board ALARM command. HTTP delivery waits for the bounded recording to finish so the alert contains the evidence package. Thus remote delivery includes up to eight seconds of collection delay, plus outage/retry delay. The current implementation does not send an early remote notification followed by a video update.

Each closed incident has a UUID, manifest, timestamped DSP/sensor values and a compressed media archive. RED packages enter a SQLite outbox. The receiver validates the media hash, stores a receipt and acknowledges that exact incident ID. A failed acknowledgement retries the same immutable payload. The test receiver can commit an incident and deliberately return HTTP 503 to exercise this path.

Evidence is retained on disk. The rolling prebuffer is bounded, and each incident's media interval is bounded; total retained incident storage has no automatic deletion policy yet. Existing result directories are never silently cleared. A single active incident groups overlapping activity. Once closed, sustained activity remains part of that episode; three quiet seconds allow another incident.

An acquisition gap that exceeds an open incident's deadline closes it as interrupted. A latched board fallback reported after reconnection can open a separate incident. Its report timestamp is known; the original offline onset time is not recovered by the current board interface.

## Commands

```text
make incident-build
python -m pytest -q
python scripts/verify_c_core.py
python run_incidents.py --output results/incidents-python
python run_incidents.py --output results/incidents-c --c-library build/libdetection.so
python scripts/compare_incidents.py results/incidents-python results/incidents-c
```

The C backend implements the nine-feature numerical kernel, deviation score, persistence rule and corroboration score. Python retains baseline fitting, the incident state machine, camera processing, storage and HTTP. This is not an all-C application. The FFT runs on the host; it is not an audio workload for the UNO.

The board host driver runs the same `core.h` used by the sketch, including GREEN/YELLOW/ALARM commands, heartbeat failure and a physical-reset input. Simulated sessions begin pre-armed. Separate embedded tests cover warm-up; no physical GPIO timing is measured here.

## Acceptance sessions

| Session | Required result |
|---|---|
| Two incidents | Two distinct confirmed incidents, two evidence packages, two receiver records |
| Internet outage and host restart | Preserve the active incident and FFT state, queue evidence, retry a lost acknowledgement, deliver each incident once |
| PC failure | Arduino fallback sounds locally while the PC is unavailable; the host records its report after reconnection |
| Thunder alone | Investigate sound, preserve the record and close without RED |

GitHub Actions executes Python regressions, C/C++ warning and sanitizer checks, C numerical parity, these sessions with both numerical backends, and the original scenario/embedded replay. Artifacts contain the actual outputs. Validation status belongs to the corresponding workflow run, not to the existence of these files.

## Remaining scope

The baseline is trained on quiet synthetic backgrounds without the older traffic component. It is frozen for a session and cannot be silently changed on restart. It has not been calibrated on the user's microphone. Soft-footstep failures still require data and investigation.

The footage is synthetic grayscale, not validated infrared footage. Replaying it proves recording and timestamp plumbing, not real-night vision accuracy. Weather context, actual camera/serial acquisition, board-clock mapping, remote service authentication and physical verification remain unfinished. MATLAB execution is still pending.

The original `21_wifi_outage` now uses its outage flag to pause its local outbox. That older runner still has a different purpose: preserve the historical independent-scenario evaluation while the continuous runner checks integration.
