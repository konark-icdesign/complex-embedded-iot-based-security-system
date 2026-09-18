import unittest
import numpy as np

from src.dsp import FS, add_event, background, features
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

    def test_callback_timestamp_jitter_does_not_destroy_stream_state(self):
        model = quiet_model()
        stream = AudioStream(model)
        rng = np.random.default_rng(20260919)
        chunk = np.zeros(1024)
        last_captured = 0.0
        for index in range(100):
            captured = (index + 1) * len(chunk) / FS + rng.normal(0, 0.0005)
            stream.push(chunk, captured)
            last_captured = captured
        self.assertEqual(stream.discontinuities, 0)

        # A real 20 ms acquisition gap is well above the 5 ms callback-jitter allowance.
        stream.push(chunk, last_captured + len(chunk) / FS + 0.020)
        self.assertEqual(stream.discontinuities, 1)

    def test_empty_audio_chunk_is_reported_unhealthy_without_silent_state_loss(self):
        model = quiet_model()
        stream = AudioStream(model)
        stream.push(np.zeros(1600), 0.1)
        pending = stream.pending.copy()
        events = stream.push(np.array([]), 0.2)
        np.testing.assert_array_equal(stream.pending, pending)
        self.assertEqual(len(events), 1)
        self.assertFalse(events[0]["valid"])
        self.assertEqual(events[0]["reason"], "empty_audio_chunk")

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
