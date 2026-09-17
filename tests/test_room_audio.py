import unittest
import numpy as np

from src.dsp import add_event, background, features
from src.room_audio import fit_room, quiet_model
from src.streaming import AudioStream


class RoomAudio(unittest.TestCase):
    def test_sensitive_stream_matches_batch_across_restart(self):
        model = quiet_model()
        wave = add_event(background(8, 2400), "soft_steps", start=2, duration=4)
        expected = model.detect(features(wave))[1]
        stream = AudioStream(model)
        output = []
        for index in range(80):
            output.extend(stream.push(wave[index*1600:(index+1)*1600], (index+1)/10))
            if index == 32:
                state = stream.state()
                stream = AudioStream(model)
                stream.restore(state)
        np.testing.assert_array_equal(expected, [e["anomaly"] for e in output])

    def test_reject_incomplete_or_invalid_commissioning_data(self):
        normal = np.zeros((10, 9))
        for bad in (normal[:0], np.zeros((10, 8)), normal*np.nan):
            with self.assertRaises(ValueError):
                fit_room(bad, normal)
            with self.assertRaises(ValueError):
                fit_room(normal, bad)
        for fraction in (0, -1, 2, float("nan")):
            with self.assertRaises(ValueError):
                fit_room(normal, normal, fraction)
