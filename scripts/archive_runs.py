"""Preserve existing GitHub run evidence; never rerun or rewrite measurements."""

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import urllib.error
import urllib.request
import zipfile

REPO = "konark-icdesign/complex-embedded-iot-based-security-system"
ROOT = Path("evidence/github")
RUNS = (35246753919, 35247401298, 35247858074, 35248260569,
        35249896689, 35250249454, 35250249408)
ALLOWED = {".json", ".csv", ".txt", ".log", ".mat", ".png", ".svg"}
LIMIT = 8 * 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def get(path):
    url = f"https://api.github.com/repos/{REPO}/{path}"
    request = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
        "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=60) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        if error.code not in (301, 302, 303, 307, 308):
            raise RuntimeError(f"GitHub HTTP {error.code} for {path}") from None
        # Signed storage URL is used without forwarding the GitHub credential.
        target = error.headers["Location"]
        if not target.startswith("https://"):
            raise RuntimeError("Refused non-HTTPS download")
        with urllib.request.urlopen(target, timeout=120) as response:
            return response.read()


def listing(path, key):
    rows, page = [], 1
    while True:
        data = json.loads(get(f"{path}?per_page=100&page={page}"))[key]
        rows.extend(data)
        if len(data) < 100:
            return rows
        page += 1


def digest(data):
    return hashlib.sha256(data).hexdigest()


def scrub(data):
    text = data.decode("utf-8")
    text, n1 = re.subn(r"(?i)([?&](?:sig|signature|token|access_token|x-amz-signature)=)[^&\s\"<>]+",
                       r"\1[REDACTED]", text)
    text, n2 = re.subn(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b",
                       "[REDACTED]", text)
    return text.encode("utf-8"), n1+n2


def archive(run_id):
    directory = ROOT / str(run_id)
    if directory.exists():
        raise RuntimeError(f"Refusing to replace existing run archive: {run_id}")
    directory.mkdir(parents=True)
    records, gaps = [], []

    def save(relative, data, source, redact=False):
        original = digest(data)
        count = 0
        if redact:
            data, count = scrub(data)
        dest = directory / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        records.append({"path": relative, "bytes": len(data), "sha256": digest(data),
                        "source_sha256": original, "source": source, "redactions": count})

    metadata = json.loads(get(f"actions/runs/{run_id}"))
    if metadata["status"] != "completed":
        raise RuntimeError("Archive completed runs only")
    save("run.json", (json.dumps(metadata, indent=2)+"\n").encode(), metadata["url"])
    jobs = listing(f"actions/runs/{run_id}/jobs", "jobs")
    save("jobs.json", (json.dumps(jobs, indent=2)+"\n").encode(), f"actions/runs/{run_id}/jobs")
    for job in jobs:
        if job["status"] != "completed" or job["conclusion"] == "skipped":
            continue
        try:
            save(f"logs/{job['id']}.txt", get(f"actions/jobs/{job['id']}/logs"),
                 f"https://github.com/{REPO}/actions/runs/{run_id}/job/{job['id']}", redact=True)
        except (RuntimeError, urllib.error.URLError) as error:
            gaps.append({"job": job["id"], "reason": str(error)})
    artifacts = listing(f"actions/runs/{run_id}/artifacts", "artifacts")
    inventories = []
    for artifact in artifacts:
        inventory = {"metadata": artifact, "members": []}
        inventories.append(inventory)
        if artifact["expired"]:
            gaps.append({"artifact": artifact["id"], "reason": "expired before archive"})
            continue
        try:
            payload = get(f"actions/artifacts/{artifact['id']}/zip")
        except (RuntimeError, urllib.error.URLError) as error:
            gaps.append({"artifact": artifact["id"], "reason": str(error)})
            continue
        inventory["download_sha256"] = digest(payload)
        expected = artifact.get("digest")
        if expected and expected != "sha256:" + digest(payload):
            raise RuntimeError(f"Artifact digest mismatch: {artifact['id']}")
        with zipfile.ZipFile(io.BytesIO(payload)) as zipped:
            for member in zipped.infolist():
                if member.is_dir():
                    continue
                path = PurePosixPath(member.filename)
                info = {"path": member.filename, "bytes": member.file_size}
                inventory["members"].append(info)
                if path.is_absolute() or ".." in path.parts or "\\" in member.filename:
                    raise RuntimeError("Unsafe archive member")
                if path.suffix.lower() not in ALLOWED:
                    info["omitted"] = "media/database or unselected format; metadata retained"
                    continue
                if member.file_size > LIMIT:
                    info["omitted"] = "over 8 MiB; large reference inputs are reproducible from source"
                    continue
                data = zipped.read(member)
                relative = f"artifacts/{artifact['id']}/{member.filename}"
                save(relative, data, artifact["archive_download_url"]+"#"+member.filename)
                info["saved"] = relative
    save("artifacts.json", (json.dumps(inventories, indent=2)+"\n").encode(),
         f"actions/runs/{run_id}/artifacts")
    manifest = {"run_id": run_id, "head_sha": metadata["head_sha"],
                "conclusion": metadata["conclusion"], "source": metadata["html_url"],
                "archived_at": datetime.now(timezone.utc).isoformat(),
                "files": records, "unavailable": gaps,
                "scope": "Completed-job logs and selected artifact members; omissions in artifacts.json"}
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    print(f"ARCHIVED run={run_id} files={len(records)} unavailable={len(gaps)}", flush=True)
    return not gaps


def repair_missing():
    """Recover omitted Git files from their original artifact, never regenerate."""
    recovered = 0
    for manifest_path in sorted(ROOT.glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text())
        for row in manifest["files"]:
            relative = PurePosixPath(row["path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise RuntimeError("Unsafe manifest path")
            dest = manifest_path.parent / relative
            if dest.exists():
                continue
            match = re.fullmatch(re.escape(f"https://api.github.com/repos/{REPO}/")
                                 + r"(actions/artifacts/\d+/zip)#(.+)", row["source"])
            if not match:
                raise RuntimeError(f"Missing non-artifact file needs explicit recovery: {dest}")
            with zipfile.ZipFile(io.BytesIO(get(match[1]))) as zipped:
                data = zipped.read(match[2])
            if digest(data) != row["sha256"] or len(data) != row["bytes"]:
                raise RuntimeError(f"Recovered bytes differ from manifest: {dest}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            recovered += 1
    print(f"ARCHIVE_RECOVERED files={recovered}", flush=True)


def verify(tracked=False):
    count = size = 0
    indexed = set(subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")) if tracked else None
    manifests = sorted(ROOT.glob("*/manifest.json"))
    if {int(p.parent.name) for p in manifests} != set(RUNS):
        raise RuntimeError("Expected exactly the seven selected run archives")
    for path in manifests:
        manifest = json.loads(path.read_text())
        if manifest["unavailable"]:
            raise RuntimeError(f"Unresolved download gaps in {path}")
        expected = {"manifest.json"}
        for row in manifest["files"]:
            relative = PurePosixPath(row["path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise RuntimeError("Unsafe manifest path")
            data = (path.parent / row["path"]).read_bytes()
            if len(data) != row["bytes"] or digest(data) != row["sha256"]:
                raise RuntimeError(f"Corrupt archived file: {row['path']}")
            expected.add(row["path"])
            count += 1
            size += len(data)
        actual = {str(p.relative_to(path.parent)) for p in path.parent.rglob("*") if p.is_file()}
        if actual != expected:
            raise RuntimeError(f"Archive contains unindexed files: {path}")
        if tracked and any(str(path.parent / p) not in indexed for p in expected):
            raise RuntimeError(f"Archive files missing from Git index: {path}")
    print(f"ARCHIVE_VERIFIED runs={len(manifests)} files={count} bytes={size} git_tracked={tracked}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--tracked", action="store_true")
    parser.add_argument("--repair-missing", action="store_true")
    args = parser.parse_args()
    if args.repair_missing:
        repair_missing()
        verify(args.tracked)
        return
    if args.verify:
        verify(args.tracked)
        return
    complete = [archive(run_id) for run_id in RUNS]
    if not all(complete):
        raise SystemExit("Archive contains retrieval gaps; inspect manifests")
    verify()


if __name__ == "__main__":
    main()
