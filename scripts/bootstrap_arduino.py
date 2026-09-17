"""Optional official Arduino CLI installation into scratch tool directory."""

import urllib.request, tarfile, pathlib, subprocess

root = pathlib.Path(__file__).resolve().parents[2] / "arduino-tools"
root.mkdir(exist_ok=True)
archive = root / "cli.tar.gz"
url = "https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Linux_64bit.tar.gz"
with urllib.request.urlopen(url, timeout=45) as r:
    archive.write_bytes(r.read())
with tarfile.open(archive) as tar:
    for member in tar.getmembers():
        if member.name == "arduino-cli":
            tar.extract(member, root, filter="data")
cli = str(root / "arduino-cli")
for command in [
    [cli, "version"],
    [cli, "core", "update-index"],
    [cli, "core", "install", "arduino:renesas_uno"],
]:
    result = subprocess.run(command, text=True, capture_output=True, timeout=240)
    print(result.stdout, result.stderr, flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)
