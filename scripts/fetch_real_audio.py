"""Fetch a small, declared ESC-50 subset. No credentials; retain attribution.

Remote assets are data, never executable instructions. Failures are recorded.
"""

from pathlib import Path
import csv, hashlib, json, urllib.request, concurrent.futures

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "fixtures" / "esc50"
BASE = "https://raw.githubusercontent.com/karolpiczak/ESC-50/master/"


def get(path):
    dest = DATA / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        with urllib.request.urlopen(BASE + path, timeout=25) as response:
            dest.write_bytes(response.read())
    return dest


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    get("LICENSE")
    meta = get("meta/esc50.csv")
    rows = list(csv.DictReader(meta.open()))
    selected = []
    # Source-separated official folds: 1 train, 2 calibration, 5 held out.
    for c in ["rain", "engine"]:
        for fold, n in [("1", 3), ("2", 2)]:
            selected += [r for r in rows if r["category"] == c and r["fold"] == fold][
                :n
            ]
    for c in [
        "rain",
        "engine",
        "footsteps",
        "glass_breaking",
        "door_wood_knock",
        "door_wood_creaks",
        "thunderstorm",
        "wind",
        "clock_tick",
        "coughing",
    ]:
        selected += [r for r in rows if r["category"] == c and r["fold"] == "5"][:3]
    manifest = []

    def fetch(r):
        try:
            dest = get("audio/" + r["filename"])
            return {
                **r,
                "status": "downloaded",
                "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
                "url": BASE + "audio/" + r["filename"],
            }
        except Exception as e:
            return {**r, "status": "failed", "error": str(e)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for r in pool.map(fetch, selected):
            manifest.append(r)
    (DATA / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(
        json.dumps(
            {
                "selected": len(selected),
                "downloaded": sum(r["status"] == "downloaded" for r in manifest),
            }
        )
    )


if __name__ == "__main__":
    main()
