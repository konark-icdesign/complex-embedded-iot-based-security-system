"""Incremental audio processing and acquisition-time packet ingestion."""

from collections import deque
import json
import numpy as np

from .dsp import features, FS, N, HOP
from .incidents import IncidentJournal, pack_array


class AudioStream:
    DEFAULT_CONTINUITY_TOLERANCE = 0.005

    def __init__(self, model, feature_fn=features, continuity_tolerance=None):
        self.model = model
        self.feature_fn = feature_fn
        self.pending = np.empty(0)
        self.features = deque(maxlen=3)
        self.valid = deque(maxlen=3)
        self.end = None
        self.frame_end = None
        self.discontinuities = 0
        self.continuity_tolerance = (
            self.DEFAULT_CONTINUITY_TOLERANCE
            if continuity_tolerance is None
            else float(continuity_tolerance)
        )
        if not np.isfinite(self.continuity_tolerance) or self.continuity_tolerance < 0:
            raise ValueError("continuity tolerance must be finite and non-negative")

    def push(self, samples, captured):
        samples = np.asarray(samples, dtype=float)
        if samples.ndim != 1 or not np.isfinite(samples).all():
            raise ValueError("audio must be finite mono samples")
        if len(samples) == 0:
            # Do not silently destroy buffered DSP state. Mark the acquisition
            # as unhealthy; the next real chunk will decide whether a gap occurred.
            return [{"t": float(captured), "score": 0.0, "anomaly": False,
                     "valid": False, "reason": "empty_audio_chunk"}]
        start = captured - len(samples) / FS
        if self.end is None or abs(start - self.end) > self.continuity_tolerance:
            if self.end is not None:
                self.discontinuities += 1
            self.pending = np.empty(0)
            self.features.clear()
            self.valid.clear()
            self.frame_end = start + N / FS
        self.end = captured
        self.pending = np.concatenate((self.pending, samples))
        events = []
        while len(self.pending) >= N:
            f = self.feature_fn(self.pending[:N])
            self.features.append(f["x"][0])
            self.valid.append(bool(f["valid"][0]))
            scores, flags = self.model.detect({"x": np.asarray(self.features),
                                               "valid": np.asarray(self.valid)})
            events.append({"t": self.frame_end, "score": float(scores[-1]),
                           "anomaly": bool(flags[-1]), "valid": self.valid[-1]})
            self.pending = self.pending[HOP:]
            self.frame_end += HOP / FS
        return events

    def state(self):
        return {"pending": self.pending.tolist(), "features": [x.tolist() for x in self.features],
                "valid": list(self.valid), "end": self.end, "frame_end": self.frame_end,
                "discontinuities": self.discontinuities}

    def restore(self, state):
        self.pending = np.asarray(state["pending"])
        self.features = deque((np.asarray(x) for x in state["features"]), maxlen=3)
        self.valid = deque(state["valid"], maxlen=3)
        self.end, self.frame_end = state["end"], state["frame_end"]
        self.discontinuities = int(state.get("discontinuities", 0))


class RoomStream:
    def __init__(self, directory, model, backend=None):
        self.journal = IncidentJournal(directory)
        self.audio = AudioStream(model if backend is None else backend.model(model),
                                 features if backend is None else backend.features)
        if backend is not None:
            self.journal.decider = backend.confirm
        identity = json.dumps([model.center.tolist(), model.scale.tolist(), model.threshold])
        previous = self.journal._meta("model", identity)
        if previous != identity:
            self.journal.close()
            raise ValueError("A resumed journal must use its original frozen baseline")
        with self.journal.db:
            self.journal._put_meta("model", identity)
        saved = self.journal._meta("stream_state", None)
        if saved is not None:
            self.audio.restore(saved)

    def push(self, seq, captured, audio, frame, physical, session="replay", arrival=None,
             fallback=False):
        arrival = captured if arrival is None else arrival
        if not self.journal.accepts(seq, captured, arrival, session):
            return {"accepted": False, "state": self.journal.state}
        events = self.audio.push(audio, captured)
        flags = {k: bool(physical.get(k, False)) for k in "PMU"}
        flags["A"] = any(e["anomaly"] for e in events)
        packet = {"seq": seq, "t": captured, "session": session,
                  "audio": pack_array(audio, "<f8"),
                  "frame": None if frame is None else pack_array(frame, "u1"),
                  "audio_events": events, "flags": flags,
                  "stream_state": self.audio.state(),
                  "health": bool(physical.get("fault", False)) or any(not e["valid"] for e in events),
                  "fallback": bool(fallback)}
        return self.journal.step(packet, arrival)

    def close(self):
        self.journal.close()
