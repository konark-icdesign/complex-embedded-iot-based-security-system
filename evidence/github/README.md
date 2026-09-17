# Preserved GitHub run evidence

These snapshots are committed repository files, independent of Actions artifact
retention. Their source runs were executed on 17 September 2026. Archival time
is recorded separately in each manifest.

| Run | Why retained |
|---|---|
| [35246753919](35246753919/) | Original PC-recovery acceptance failure |
| [35247401298](35247401298/) | Original MATLAB integer-input failure |
| [35247858074](35247858074/) | First successful MATLAB verification after its fix |
| [35248260569](35248260569/) | Verified continuous pipeline and acquisition-time correction |
| [35249896689](35249896689/) | Development comparison, including the faulty clipping fixture |
| [35250249454](35250249454/) | Frozen quality evaluation, public-audio diagnostic and MATLAB parity |
| [35250249408](35250249408/) | New profile's connected integration and board checks |

Each directory contains:

- `run.json` and `jobs.json`: original GitHub metadata and step conclusions.
- `logs/<job-id>.txt`: completed-job logs, including failure output.
- `artifacts/<artifact-id>/`: selected original files extracted from downloaded ZIPs.
- `artifacts.json`: artifact metadata, ZIP checksum and inventory of saved/omitted members.
- `manifest.json`: source commit, run URL, archival time, file lengths and SHA-256 checksums.

JSON/CSV/TXT/LOG/MAT/PNG/SVG members up to 8 MiB are retained. Large raw media,
SQLite databases and oversized reference inputs are excluded with explicit
inventory reasons. Downloaded ZIP digests are checked against GitHub metadata
when supplied. Selected artifact bytes are preserved without rewriting.

GitHub already masks workflow secrets. The archiver additionally redacts token
patterns and signed-URL access parameters from log copies. Each file's manifest
records the original downloaded-byte checksum, stored-byte checksum and number
of these additional redactions. Logs are not described as byte-identical where
redactions occurred. This is not a security audit of arbitrary logs.

Verify the stored files offline:

```text
python scripts/archive_runs.py --verify
```

The archiver refuses to overwrite a run directory. Missing downloads fail its
check and are listed in the manifest. Future runs must be deliberately selected
and archived before their retention period expires; this snapshot does not
automatically preserve every future CI run.

See [debugging history](../../docs/debugging_history.md) for symptoms, fixes,
remaining limitations and the older logs already committed under `results/`.
