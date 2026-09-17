"""Run a continuous room simulation with an actual local HTTP test receiver."""

import argparse
import json
from pathlib import Path
import sqlite3
import subprocess

import numpy as np

from src.dsp import FS, Baseline, background, features, add_event
from src.vision import room, render
from src.streaming import RoomStream
from src.delivery import deliver
from src.native import NativeCore
from scripts.test_receiver import receiver


def quiet_baseline():
    def collect(seeds):
        return np.concatenate([features(background(8, s, traffic=False))["x"] for s in seeds])
    return Baseline.fit(collect([11, 12, 13, 14]), collect([101, 102]))


def run_session(directory, board_binary, backend=None, network_loss=False,
                pc_loss=False, restart=False, environment=False):
    directory = Path(directory)
    model = quiet_baseline()
    stream = RoomStream(directory / "host", model, backend)
    wave = background(42, 1000, traffic=False)
    for start in (8, 28):
        wave = add_event(wave, "thunder" if environment else "steps", start, 3, seed=45)
    board = subprocess.Popen([str(Path(board_binary).resolve())], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    state = "GREEN"
    trace = []
    max_pending = 0
    base = room(100)
    rng = np.random.default_rng(100)
    try:
        with receiver(directory / "receiver", lose_first_ack=network_loss) as endpoint:
            for seq in range(1, 421):
                t = round(seq / 10, 6)
                pc = not (pc_loss and 9 <= t < 21)
                internet = not (network_loss and 8 <= t < 24)
                active = not environment and (9 <= t < 12 or 29 <= t < 32)
                command = "ALARM" if state == "RED" else state
                # Physical reset is a simulated button press between the incidents.
                board.stdin.write(f"{seq*100} {int(active)} {int(active)} "
                                  f"{1.2 if active else 3.0} 1 {int(pc)} {int(seq == 240)} {command}\n")
                board.stdin.flush()
                values = board.stdout.readline().split()
                if len(values) != 8:
                    raise RuntimeError("board stream terminated: " + board.stderr.read())
                p, m, u, fault, degraded, alarm, yellow, fallback = map(int, values)
                if restart and seq == 105:
                    stream.close()
                    stream = RoomStream(directory / "host", model, backend)
                if pc:
                    start = 10 if t < 20 else 30
                    frame = (render(base, t, rng, "normal" if environment else "person",
                                    start=start, end=start+3) if seq % 2 else None)
                    result = stream.push(seq, t, wave[(seq-1)*1600:seq*1600], frame,
                                         {"P": p, "M": m, "U": u, "fault": fault},
                                         fallback=fallback)
                    state = result["state"]
                    if seq % 10 == 0:
                        deliver(stream.journal, endpoint, internet)
                pending = stream.journal.db.execute(
                    "SELECT count(*) FROM deliveries WHERE acked=0").fetchone()[0]
                max_pending = max(max_pending, pending)
                trace.append({"t": t, "pc": pc, "internet": internet, "state": state if pc else "OFFLINE",
                              "board_alarm": alarm, "board_yellow": yellow,
                              "fallback": fallback, "degraded": degraded, "pending": pending})
            deliver(stream.journal, endpoint)
            records = stream.journal.records()
            pending = stream.journal.db.execute(
                "SELECT count(*) FROM deliveries WHERE acked=0").fetchone()[0]
            attempts = stream.journal.db.execute("SELECT coalesce(sum(attempts),0) FROM deliveries").fetchone()[0]
        with sqlite3.connect(directory / "receiver" / "receiver.sqlite") as db:
            received = db.execute("SELECT id FROM receipts").fetchall()
        red = [r for r in records if r["state"] == "RED"]
        expected = 0 if environment else 2
        checks = {
            "expected_confirmed_incidents": len(red) == expected,
            "distinct_ids": len({r["id"] for r in records}) == len(records),
            "receiver_matches_red": {r[0] for r in received} == {r["id"] for r in red},
            "queue_drained": pending == 0,
            "all_closed": all(r["status"] == "closed" for r in records),
            "outage_queued": not network_loss or max_pending > 0,
            "retry_after_lost_ack": not network_loss or attempts > len(red),
            "local_fallback": not pc_loss or any(r["fallback"] and not r["pc"] for r in trace),
            "yellow_reaches_board": any(r["board_yellow"] for r in trace),
        }
        for record in red:
            manifest = json.loads((directory / "host" / "evidence" / record["id"] / "manifest.json").read_text())
            checks["media_" + record["id"]] = bool(manifest["media_keys"])
            checks["prebuffer_" + record["id"]] = manifest["samples"][0]["t"] < record["trigger"]
        result = {"checks": checks, "passed": all(checks.values()), "incidents": records,
                  "received": len(received), "attempts": attempts, "max_pending": max_pending,
                  "model": {"center": model.center.tolist(), "scale": model.scale.tolist(),
                            "threshold": model.threshold},
                  "scope": "synthetic raw audio/images, compiled C++ board, loopback HTTP; board pre-armed"}
        (directory / "trace.json").write_text(json.dumps(trace, indent=2))
        (directory / "summary.json").write_text(json.dumps(result, indent=2))
        return result
    finally:
        stream.close()
        board.stdin.close()
        try:
            board.wait(timeout=5)
        except subprocess.TimeoutExpired:
            board.kill()
            board.wait()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="results/incident-run")
    parser.add_argument("--board", default="build/board-stream")
    parser.add_argument("--c-library", default=None)
    args = parser.parse_args()
    root = Path(args.output)
    if root.exists() and any(root.iterdir()):
        parser.error("Use an empty output directory; existing evidence is not overwritten")
    root.mkdir(parents=True, exist_ok=True)
    native = None if args.c_library is None else NativeCore(args.c_library)
    results = {}
    for name, options in [("two_incidents", {}), ("outage_restart", {"network_loss": True, "restart": True}),
                          ("pc_failure", {"pc_loss": True}), ("thunder_only", {"environment": True})]:
        result = run_session(root / name, args.board, native, **options)
        results[name] = {"passed": result["passed"], "received": result["received"],
                         "failed_checks": [k for k, v in result["checks"].items() if not v]}
        print(name, json.dumps(results[name]), flush=True)
    (root / "summary.json").write_text(json.dumps(results, indent=2))
    if not all(r["passed"] for r in results.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
