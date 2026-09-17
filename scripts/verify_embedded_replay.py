from pathlib import Path
import csv
import subprocess
import sys
import json
import tempfile
import os
import argparse
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.scenarios import cases, physical


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-leak-check",
        action="store_true",
        help="Only for runtimes where LeakSanitizer cannot operate",
    )
    args = parser.parse_args()
    vectors = []
    expected = []
    for case in cases():
        rows = list(
            csv.DictReader((ROOT / "results" / "traces" / f"{case.name}.csv").open())
        )
        for row in rows:
            t = float(row["t"])
            p, m, _ = physical(case, t, np.random.default_rng(1))
            heartbeat = not ((case.server_outage or case.usb_outage) and 6 <= t < 19)
            vectors.append(
                f"{case.name},{round(t*1000)},{int(p)},{int(m)},{row['raw_distance']},{int(heartbeat)}"
            )
            expected.append(
                [
                    case.name,
                    str(round(t * 1000)),
                    row["physical_p"],
                    row["physical_m"],
                    row["physical_u"],
                    row["fallback"],
                ]
            )
    with tempfile.TemporaryDirectory() as d:
        binary = str(Path(d) / "replay")
        cmd = [
            "g++",
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-Wpedantic",
            "-fsanitize=address,undefined",
            "-fno-omit-frame-pointer",
            str(ROOT / "tests" / "embedded_replay.cpp"),
            "-o",
            binary,
        ]
        subprocess.run(cmd, check=True)
        env = os.environ.copy()
        if args.no_leak_check:
            env["ASAN_OPTIONS"] = "detect_leaks=0"
        run = subprocess.run(
            [binary],
            input="\n".join(vectors) + "\n",
            text=True,
            capture_output=True,
            env=env,
            check=True,
        )
    actual = [line.split(",") for line in run.stdout.strip().splitlines()]
    mismatch = [dict(expected=e, actual=a) for e, a in zip(expected, actual) if e != a]
    result = dict(
        input_ticks=len(expected),
        output_ticks=len(actual),
        mismatches=len(mismatch),
        examples=mismatch[:10],
        sanitizer="AddressSanitizer + UndefinedBehaviorSanitizer",
        leak_check_disabled=args.no_leak_check,
    )
    (ROOT / "results" / "embedded_replay.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    if mismatch or len(expected) != len(actual):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
