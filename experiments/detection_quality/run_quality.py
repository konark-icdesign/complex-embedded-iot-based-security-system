"""Compare frozen audio models. All measurements are produced in GitHub Actions."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

import numpy as np
from scipy.io import savemat

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.dsp import FS, Baseline, add_event, background, features
from src.room_audio import fit_room, quiet_training
from src.native import NativeCore
from src.fusion import Fusion

START, END, SECONDS = 3.0, 7.0, 10.0


def walking(x, rng, level, heldout):
    """Varied damped impacts; surrogate footsteps, not an acoustic room model."""
    t = np.arange(len(x)) / FS
    event = np.zeros(len(x))
    cadence = rng.uniform(0.38, 0.85)
    for onset in np.arange(START, END-0.3, cadence):
        u = t-onset-rng.uniform(0, 0.04)
        env = np.exp(-np.maximum(u, 0)*rng.uniform(15, 35)) * (u >= 0) * (u < 0.35)
        # Final evaluation changes both carrier range and damping shape.
        frequency = rng.uniform(85, 130) if heldout else rng.uniform(55, 80)
        carrier = np.sin(2*np.pi*frequency*u)
        if heldout:
            carrier += 0.25*np.sin(2*np.pi*frequency*2.3*u)
        event += level*env*(0.075*carrier + 0.018*rng.normal(size=len(x)))
    return x+event


def trials(split):
    heldout = split == "heldout"
    # Source waveforms and seeds never overlap training/calibration/development.
    seeds = range(8000, 8020) if heldout else range(2000, 2010)
    kinds = ("quiet", "gain_ramp", "soft_steps", "very_soft_steps", "steps",
             "impact", "thunder", "click", "fan_shift", "wind", "silence", "clipping")
    for seed in seeds:
        for kind in kinds:
            rng = np.random.default_rng(seed)
            gain = rng.uniform(0.4, 2.2)
            x = background(SECONDS, seed)
            if kind == "gain_ramp":
                x *= np.linspace(0.4, 2.2, len(x))
            elif kind in ("soft_steps", "very_soft_steps", "steps"):
                level = {"soft_steps": 0.12, "very_soft_steps": 0.06, "steps": 1}[kind]
                x = walking(x, rng, level, heldout)
            elif kind in ("impact", "thunder", "click", "wind"):
                x = add_event(x, kind, START, END-START, seed)
            elif kind == "fan_shift":
                t = np.arange(len(x))/FS
                # Uncommissioned fan speed: an explicit domain-shift stress test.
                x += (t >= START)*0.003*np.sin(2*np.pi*155*t)
            elif kind == "silence":
                x[:] = 0
            elif kind == "clipping":
                x[:] = np.resize([-1., 1.], len(x))
            # Clipping is at the ADC rails, after gain. Scaling it down first
            # would instead test a valid full-band square wave.
            wave = x if kind == "clipping" else np.clip(x*gain, -1, 1)
            yield kind, seed, features(wave)


def evaluate(model, data, native=None):
    groups = defaultdict(list)
    for kind, seed, f in data:
        scores, flags = model.detect(f)
        if native is not None:
            c_scores, c_flags = native.model(model).detect(f)
            np.testing.assert_allclose(scores, c_scores, atol=1e-12, rtol=1e-12)
            np.testing.assert_array_equal(flags, c_flags)
        inside = (f["t"] >= START) & (f["t"] <= END)
        hits = np.flatnonzero(flags & inside)
        alone, coincident = Fusion(), Fusion()
        for t, flag, active in zip(f["t"], flags, inside):
            alone.update(t, {"A": flag})
            coincident.update(t, {"A": flag, "P": active, "M": active})
        groups[kind].append({"seed": seed, "flagged": bool(flags.any()),
                             "event_hit": bool(len(hits)),
                             "audio_only_red": bool(alone.alerts),
                             "coincident_pm_red": bool(coincident.alerts),
                             "latency": float(f["t"][hits[0]]-START) if len(hits) else None,
                             "outside_frames": int((flags & ~inside).sum()),
                             "valid_frames": int(f["valid"].sum()),
                             "peak_ratio": float(scores.max()/model.threshold)})
    return {k: {"trials": len(rows), "flagged": sum(r["flagged"] for r in rows),
                "event_hits": sum(r["event_hit"] for r in rows),
                "audio_only_red": sum(r["audio_only_red"] for r in rows),
                "coincident_pm_red": sum(r["coincident_pm_red"] for r in rows),
                "median_latency": float(np.median([r["latency"] for r in rows if r["latency"] is not None]))
                    if any(r["latency"] is not None for r in rows) else None,
                "rows": rows} for k, rows in groups.items()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=("development", "heldout"), default="development")
    parser.add_argument("--output", default="results/detection-quality")
    parser.add_argument("--c-library")
    args = parser.parse_args()
    training, calibration = quiet_training()
    models = {"baseline": Baseline.fit(training, calibration)}
    fractions = (0.1, 0.25, 0.5, 1.0) if args.split == "development" else (0.1,)
    models.update({f"room_{fraction}": fit_room(training, calibration, fraction) for fraction in fractions})
    data = list(trials(args.split))
    native = NativeCore(args.c_library) if args.c_library else None
    result = {"split": args.split, "scope": "synthetic audio anomaly checks; not intrusion accuracy",
              "models": {}, "results": {}}
    for name, model in models.items():
        result["models"][name] = {"center": model.center.tolist(), "scale": model.scale.tolist(),
                                   "threshold": model.threshold}
        result["results"][name] = evaluate(model, data, native)
        compact = {k: {a: b for a, b in v.items() if a != "rows"}
                   for k, v in result["results"][name].items()}
        print("QUALITY", name, json.dumps(compact), flush=True)
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=True)
    (root / (args.split+".json")).write_text(json.dumps(result, indent=2)+"\n")
    if args.split == "heldout":
        old, new = result["results"]["baseline"], result["results"]["room_0.1"]
        checks = {
            "soft_step_improvement": new["soft_steps"]["event_hits"] > old["soft_steps"]["event_hits"],
            "normal_and_fault_inputs_no_flags": all(new[k]["flagged"] == 0 for k in
                ("quiet", "gain_ramp", "fan_shift", "silence", "clipping")),
            "strong_events_preserved": all(new[k]["event_hits"] >= old[k]["event_hits"] for k in ("steps", "impact")),
            "audio_alone_never_red": all(v["audio_only_red"] == 0 for v in new.values()),
        }
        print("ACCEPTANCE", json.dumps(checks), flush=True)
        (root / "acceptance.json").write_text(json.dumps(checks, indent=2)+"\n")
        # Export independent clips separately: persistence must reset between clips.
        model = models["room_0.1"]
        savemat(root / "room_reference.mat", {"center": model.center, "scale": model.scale,
            "threshold": model.threshold, "x": np.stack([f["x"] for _, _, f in data]),
            "valid": np.stack([f["valid"] for _, _, f in data]),
            "scores": np.stack([model.detect(f)[0] for _, _, f in data]),
            "flags": np.stack([model.detect(f)[1] for _, _, f in data])})
        if not all(checks.values()):
            raise SystemExit("Candidate failed the predeclared acceptance checks")


if __name__ == "__main__":
    main()
