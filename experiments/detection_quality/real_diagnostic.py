"""Previously inspected ESC-50 clips are a transfer diagnostic, not a new test set."""

import json
from pathlib import Path
import sys
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.dsp import Baseline, features
from src.room_audio import quiet_model, quiet_training
from src.real_audio import load_audio


def main():
    root = Path("fixtures/esc50")
    manifest = json.loads((root / "manifest.json").read_text())
    models = {"baseline_quiet": Baseline.fit(*quiet_training()), "room_quiet": quiet_model()}
    result = {}
    for name, model in models.items():
        categories = defaultdict(lambda: {"clips": 0, "flagged": 0})
        for row in manifest:
            if row["fold"] != "5":
                continue
            f = features(load_audio(root / "audio" / row["filename"]))
            values = categories[row["category"]]
            values["clips"] += 1
            values["flagged"] += int(model.detect(f)[1].any())
        result[name] = dict(categories)
        print("REAL_TRANSFER", name, json.dumps(result[name]), flush=True)
    out = Path("results/detection-quality")
    out.mkdir(parents=True, exist_ok=True)
    (out / "real_transfer.json").write_text(json.dumps(result, indent=2)+"\n")


if __name__ == "__main__":
    main()
