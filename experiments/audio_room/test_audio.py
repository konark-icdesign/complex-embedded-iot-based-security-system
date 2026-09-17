import unittest
import numpy as np
from audio.dsp import features, background, Baseline


class AudioChecks(unittest.TestCase):
    def test_gain_invariance(self):
        x = background(2, 88)
        np.testing.assert_allclose(features(x)["x"], features(3 * x)["x"], atol=1e-10)

    def test_silence_and_clipping_are_invalid(self):
        self.assertFalse(features(np.zeros(4096))["valid"].any())
        self.assertFalse(features(np.tile([-1.0, 1.0], 2048))["valid"].any())

    def test_decision_timestamps_use_frame_end(self):
        self.assertEqual(features(background(1, 88))["t"][0], 2048 / 16000)

    def test_invalid_window_cannot_inherit_anomaly(self):
        model = Baseline(np.zeros(9), np.ones(9), threshold=0.5)
        _, flags = model.detect(
            {"x": np.ones((3, 9)), "valid": np.array([True, True, False])}
        )
        self.assertTrue(flags[1])
        self.assertFalse(flags[2])


if __name__ == "__main__":
    unittest.main()
