import argparse
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.dsp import features, background, add_event, Baseline
from src.incidents import corroborate
from src.native import NativeCore


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--library", default="build/libdetection.so")
    args = parser.parse_args()
    core = NativeCore(args.library)
    wave = add_event(background(4, 123), "steps", 1, 2, 55)
    sample_frames = [wave[i:i+2048] for i in range(0, len(wave)-2048, 1024)]
    sample_frames += [np.zeros(2048), np.ones(2048), np.tile([-1., 1.], 1024)]
    error = 0.0
    for frame in sample_frames:
        reference, actual = features(frame), core.features(frame)
        np.testing.assert_allclose(actual["x"], reference["x"], atol=1e-9, rtol=1e-8)
        np.testing.assert_array_equal(actual["valid"], reference["valid"])
        error = max(error, float(np.max(np.abs(actual["x"]-reference["x"]))))
    baseline = Baseline(np.zeros(9), np.ones(9), 3.5)
    fixture = {"x": np.full((4, 9), 10.), "valid": np.array([True, True, False, True])}
    p_score, p_flag = baseline.detect(fixture)
    c_score, c_flag = core.model(baseline).detect(fixture)
    np.testing.assert_allclose(c_score, p_score)
    np.testing.assert_array_equal(c_flag, p_flag)
    for mask in range(32):
        channels = {k for i, k in enumerate("AVPMU") if mask & (1 << i)}
        assert core.confirm(channels) == corroborate(channels)
    print(json.dumps({"frames": len(sample_frames), "max_feature_error": error,
                      "fusion_masks": 32, "invalid_window_parity": True}, indent=2))


if __name__ == "__main__":
    main()
