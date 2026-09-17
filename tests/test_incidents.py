import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from src.dsp import Baseline, background, features
from src.incidents import IncidentJournal, pack_array
from src.streaming import AudioStream, RoomStream
from src.delivery import deliver
from src.vision import room
from scripts.test_receiver import receiver


class Incidents(unittest.TestCase):
    def packet(self, seq, flags=None):
        return {"seq": seq, "t": seq/10, "session": "test", "flags": flags or {},
                "frame": pack_array((room(10) + np.random.default_rng(seq).normal(0, .8, (120, 160))).astype(np.uint8), "u1"),
                "audio": pack_array(np.zeros(1600), "<f8")}

    def test_restart_two_distinct_incidents_and_http_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            j = IncidentJournal(Path(tmp)/"host")
            for seq in range(1, 401):
                flags = {"A": True, "P": True, "M": True} if (60 <= seq < 80 or 240 <= seq < 260) else {}
                j.step(self.packet(seq, flags))
                if seq == 65:
                    old_id = j.active["id"]
                    j.close()
                    j = IncidentJournal(Path(tmp)/"host")
                    self.assertEqual(j.active["id"], old_id)
            records = j.records()
            red = [r for r in records if r["state"] == "RED"]
            self.assertEqual(len(red), 2)
            self.assertEqual(len({r["id"] for r in red}), 2)
            with receiver(Path(tmp)/"receiver", lose_first_ack=True) as url:
                self.assertEqual(deliver(j, url, False), 0)
                deliver(j, url)
                j.close()
                j = IncidentJournal(Path(tmp)/"host")
                deliver(j, url)
                self.assertEqual(j.db.execute("SELECT count(*) FROM deliveries WHERE acked=1").fetchone()[0], 2)
            for r in red:
                saved = json.loads((Path(tmp)/"host"/"evidence"/r["id"]/"manifest.json").read_text())
                self.assertLess(saved["samples"][0]["t"], r["trigger"])
                self.assertGreater(saved["samples"][-1]["t"], r["confirmed_at"])
            j.close()

    def test_stale_duplicate_and_wrong_session_do_not_enter_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            j = IncidentJournal(tmp)
            self.assertTrue(j.step(self.packet(1))["accepted"])
            self.assertFalse(j.step(self.packet(1))["accepted"])
            self.assertFalse(j.step(self.packet(2), arrival=2)["accepted"])
            packet = self.packet(3)
            packet["session"] = "rebooted-clock"
            self.assertFalse(j.step(packet)["accepted"])
            self.assertEqual(len(j.history()), 1)
            j.close()

    def test_distant_evidence_does_not_fill_whole_recording_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            j = IncidentJournal(tmp)
            for seq in range(1, 151):
                flags = {"A": True} if seq == 50 else {"P": True, "M": True} if seq == 110 else {}
                j.step(self.packet(seq, flags))
            self.assertFalse(any(r["state"] == "RED" for r in j.records()))
            j.close()

    def test_streaming_matches_batch_and_resumes_without_fft_phase_shift(self):
        wave = background(3, 400)
        model = Baseline(np.zeros(9), np.ones(9), 3.5)
        batch = features(wave)
        stream = AudioStream(model)
        output = []
        for i in range(30):
            output.extend(stream.push(wave[i*1600:(i+1)*1600], (i+1)/10))
            if i == 14:
                saved = stream.state()
                stream = AudioStream(model)
                stream.restore(saved)
        np.testing.assert_allclose([r["t"] for r in output], batch["t"], atol=1e-12)
        np.testing.assert_allclose([r["score"] for r in output], model.score(batch["x"]), atol=1e-12)

    def test_model_change_rejected_on_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = RoomStream(tmp, Baseline(np.zeros(9), np.ones(9), 3.5))
            first.close()
            with self.assertRaises(ValueError):
                RoomStream(tmp, Baseline(np.ones(9), np.ones(9), 3.5))

    def test_missing_pc_footage_is_reported_and_overlapping_activity_grouped(self):
        with tempfile.TemporaryDirectory() as tmp:
            j = IncidentJournal(tmp)
            for seq in range(1, 80):
                j.step(self.packet(seq))
            # The PC returns after a long gap with a latched fallback report.
            first = self.packet(210)
            first["fallback"] = True
            j.step(first)
            for seq in range(211, 301):
                packet = self.packet(seq, {"A": True, "P": True, "M": True} if seq == 280 else {})
                packet["fallback"] = True
                j.step(packet)
            red = [r for r in j.records() if r["state"] == "RED"]
            self.assertEqual(len(red), 1)  # Overlap belongs to the open investigation.
            manifest = json.loads((Path(tmp)/"evidence"/red[0]["id"]/"manifest.json").read_text())
            self.assertTrue(manifest["coverage"]["prebuffer_incomplete"])
            self.assertEqual(manifest["coverage"]["available_start"], 21)
            j.close()


if __name__ == "__main__":
    unittest.main()
