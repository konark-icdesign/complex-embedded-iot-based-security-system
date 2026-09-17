# Debugging history and evidence

This is an index of the documented engineering problems. It distinguishes failed
tests, findings from code inspection, modelling limitations and tooling issues.
The evidence is from the original runs; archiving it does not rerun experiments.

## Earlier simulation

| Problem | Change or current status | Original evidence |
|---|---|---|
| Qualifying inputs jumped directly from GREEN to RED | Added the required YELLOW transition; regression passed | [First failing test](../results/first_regression_run.txt), [final tests](../results/final_regression_run.txt) |
| Evidence buffer included the next 100 ms of audio | Code inspection found look-ahead; changed to completed samples only | [Recorded development finding](experiment_report.md#fixes-recorded-during-development); no separate failing run claimed |
| Persistent camera fault kept RED active and suppressed another incident | Separated activity timing from health timing | [Failure](../results/second_regression_failure.txt), [final tests](../results/final_regression_run.txt) |
| LeakSanitizer could not start under the earlier hosted tracer | Disabled leak detection for that environment only; ASan/UBSan remained enabled | [Sanitizer log](../results/embedded_sanitizer_log.txt), [reproduction](reproduction.md) |
| Vendor-core compiler warnings | Retained warnings; project host code uses warnings as errors | [Original board compile log](../results/arduino_compile_log.txt) |
| Three intrusion cases missed, two benign cases raised RED | Coverage/placement/corroboration limitations remain | [Full scenario report](experiment_report.md), [trial results](../results/monte_carlo_results.csv) |

## Continuous incidents and MATLAB

| Problem | Fix and verification | Archived run |
|---|---|---|
| PC-recovery acceptance failed: overlapping events grouped and missing outage footage demanded by the test | Added explicit coverage/gap metadata and overlap regression; separated the two-incident acceptance events | [Original failure 35246753919](../evidence/github/35246753919/), [verified implementation 35248260569](../evidence/github/35248260569/) |
| MATLAB rejected arithmetic on an integer-loaded sample rate | Convert and validate the sample rate; retain integer-input regression | [Original failure 35247401298](../evidence/github/35247401298/), [first success 35247858074](../evidence/github/35247858074/) |
| Processing tick was used instead of the audio frame's acquisition time | Separate trigger timestamp from processing/open time; anchor recording to the acquired frame | [Verified timestamp change 35248260569](../evidence/github/35248260569/), [explanation](incidents.md) |
| Host restart, network outage and lost HTTP acknowledgement could interrupt an investigation or duplicate delivery | Persistent incident/FFT state and an idempotent queue/receiver were implemented and tested | [Verification 35248260569](../evidence/github/35248260569/); these are tested failure modes, not a claim that every one first failed in development |

## Detection quality

| Finding | Result/status | Archived evidence |
|---|---|---|
| Wide feature tolerances missed soft synthetic steps | Compared four floor settings on development data; froze the selected profile before final evaluation | [Development 35249896689](../evidence/github/35249896689/), [protocol](../experiments/detection_quality/protocol.md) |
| Clipping test applied gain after saturation | Some inputs became valid square waves. Corrected the fixture to hold ADC rails; detector code did not change for this issue | [Original development output](../evidence/github/35249896689/), [corrected evaluation](../evidence/github/35250249454/) |
| New room profile | Soft-step hits 0/20 → 20/20, background/gain/fan flags 0/60 → 0/60 | [Original final evaluation 35250249454](../evidence/github/35250249454/) |
| Very soft steps | Still missed 19/20 | Same final evaluation; failure retained |
| Public-audio transfer | Both quiet-trained models flagged all 30 clips, including six normal proxies | Same archive: `real_transfer.json`; not a successful generalization result |
| Benign sound coincides with PIR and radar | Thunder/wind/clicks can still trigger RED; sound alone does not | Same archive: per-trial coincidence results |
| Warm-object/person ambiguity | Current simulated camera/PIR observations can match; unresolved | [Quality discussion](detection_quality.md#what-this-does-not-fix) |
| New profile integration and numerical agreement | Python/C incident decisions agree; MATLAB checks 240 final clips; 26 Python tests pass | [Audio/MATLAB 35250249454](../evidence/github/35250249454/), [integration/board 35250249408](../evidence/github/35250249408/) |

## Documentation and retrieval corrections

The historical report's outstanding-work paragraph, the HP setup table and the
report generator still described MATLAB as unexecuted or unverified after it
passed on GitHub. Those current-status statements were corrected; the original
historical run's own MATLAB status remains labelled historical. The development
task list now distinguishes improved synthetic soft steps from unresolved very
soft steps and real recordings.

An earlier attempt to download an artifact through a connector-provided file
URL returned HTTP 403. It was an evidence-retrieval issue, not a failed security
simulation. The archive job instead downloads the existing artifacts inside
GitHub Actions using its repository token. No original experiment is rerun to
replace missing evidence.

The first archive commit exposed another tooling issue: the repository's
`c-parity.json` ignore rule excluded five copied C parity summaries. The files
had passed the working-directory checksum check but were absent from the remote
Git tree. Recovery downloads the exact original artifact members and verifies
their recorded hashes. The archive workflow now explicitly stages its directory
and checks every manifested file against the Git index before committing.

## Archive contents and limits

Start at [the archive index](../evidence/github/README.md). Each selected run has
original run/job metadata, completed-job logs, selected artifact files and a
checksum manifest. Failed runs keep their failure conclusion. Artifact member
inventories record every saved or intentionally omitted file. Download failures
are recorded as unavailable and cause the archive check to fail.

This preserves the important available debugging evidence in Git history. It
is not a transcript of every edit or thought. Large raw media/database files
and reference inputs over 8 MiB are not copied; their names and sizes are listed.
The small final audio replay MAT file is included. No hardware experiments,
unobserved failures, dates or old commits have been invented.

When another substantive change is validated, archive its original run before
Actions retention expires and add its observed problem/fix/result here. Merely
linking an expiring artifact is not a permanent archive.
