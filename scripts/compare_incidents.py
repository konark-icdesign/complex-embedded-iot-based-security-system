import json
from pathlib import Path
import sys


def decisions(root):
    result = {}
    for path in sorted(Path(root).glob("*/summary.json")):
        data = json.loads(path.read_text())
        result[path.parent.name] = [
            {k: r[k] for k in ("trigger", "deadline", "state", "confirmed_at", "channels", "score", "reason")}
            for r in data["incidents"]]
    if not result:
        raise ValueError("No incident results found")
    return result


if __name__ == "__main__":
    first, second = decisions(sys.argv[1]), decisions(sys.argv[2])
    if first != second:
        print(json.dumps({"python": first, "c": second}, indent=2))
        raise SystemExit("Incident decision mismatch")
    print(f"PASS identical incident decisions in {len(first)} continuous sessions")
