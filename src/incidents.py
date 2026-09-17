"""Timestamped investigations and durable evidence for a single room stream."""

import base64
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import uuid

import numpy as np

from .fusion import Fusion, PacketGate
from .vision import Camera


def pack_array(value, dtype):
    array = np.asarray(value, dtype=dtype)
    return {"shape": list(array.shape), "dtype": array.dtype.str,
            "data": base64.b64encode(array.tobytes()).decode("ascii")}


def unpack_array(value):
    return np.frombuffer(base64.b64decode(value["data"]),
                         dtype=value["dtype"]).reshape(value["shape"]).copy()


def corroborate(channels):
    channels = set(channels)
    score = sum(Fusion.weights.get(k, 0) for k in channels)
    physical = len(channels & {"P", "M", "U"})
    rule = ("V" in channels and physical >= 1) or physical >= 3
    rule = rule or ("A" in channels and physical >= 2)
    return score, bool(rule and score >= 5)


class IncidentJournal:
    PRE = 5.0
    POST = 8.0
    SPAN = 4.0
    QUIET = 3.0

    def __init__(self, directory):
        self.root = Path(directory)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / "journal.sqlite")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS history(stamp REAL PRIMARY KEY, payload TEXT);
            CREATE TABLE IF NOT EXISTS incidents(id TEXT PRIMARY KEY, payload TEXT);
            CREATE TABLE IF NOT EXISTS evidence(
                incident TEXT, stamp REAL, payload TEXT, PRIMARY KEY(incident,stamp));
            CREATE TABLE IF NOT EXISTS deliveries(
                id TEXT PRIMARY KEY, payload TEXT, acked INTEGER DEFAULT 0,
                attempts INTEGER DEFAULT 0, error TEXT);
        """)
        self.active = self._meta("active", None)
        self.last_arrival = self._meta("arrival", -1.0)
        self.last_stamp = self._meta("stamp", -1.0)
        self.last_activity = self._meta("activity", -1e9)
        self.blocked = self._meta("blocked", False)
        self.fallback_seen = self._meta("fallback_seen", False)
        self.gate = PacketGate()
        self.gate.seq = self._meta("sequence", -1)
        self.session = self._meta("session", None)
        self.decider = corroborate
        self.camera = Camera()
        for packet in self.history():
            if packet.get("frame") is not None:
                self.camera.update(packet["t"], unpack_array(packet["frame"]))
        self.recover_packages()

    def _meta(self, key, default):
        row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return default if row is None else json.loads(row[0])

    def _put_meta(self, key, value):
        self.db.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (key, json.dumps(value)))

    def history(self):
        return [json.loads(r[0]) for r in self.db.execute(
            "SELECT payload FROM history ORDER BY stamp")]

    def records(self):
        return [json.loads(r[0]) for r in self.db.execute(
            "SELECT payload FROM incidents ORDER BY rowid")]

    def packets(self, identity):
        return [json.loads(r[0]) for r in self.db.execute(
            "SELECT payload FROM evidence WHERE incident=? ORDER BY stamp", (identity,))]

    def accepts(self, seq, captured, arrival, session):
        return (all(math.isfinite(v) for v in (captured, arrival))
                and arrival >= self.last_arrival and captured > self.last_stamp
                and seq > self.gate.seq and 0 <= arrival - captured <= 0.5
                and (self.session is None or session == self.session))

    def step(self, packet, arrival=None):
        """Packet timestamps use one host acquisition clock, in seconds.

        A new clock/session requires a separate journal. Restarting this journal
        resumes its clock and sequence; a rebooted device needs clock mapping.
        """
        packet = dict(packet)
        stream_state = packet.pop("stream_state", None)
        t = float(packet["t"])
        arrival = t if arrival is None else float(arrival)
        seq, session = int(packet["seq"]), packet["session"]
        if not self.accepts(seq, t, arrival, session):
            return {"accepted": False, "state": self.state, "id": None}
        assert self.gate.accept(seq, t, arrival)
        self.session = session
        # Camera evidence is computed from images, never trusted from a label.
        frame = packet.get("frame")
        view = self.camera.update(t, None if frame is None else unpack_array(frame))
        flags = {k: bool(packet.get("flags", {}).get(k, False)) for k in "APMU"}
        flags["V"] = bool(view["motion"])
        packet["flags"] = flags
        packet["detections"] = ([{"channel": "A", "t": e["t"]}
                                  for e in packet.get("audio_events", []) if e["anomaly"]]
                                 + [{"channel": k, "t": t} for k in "VPMU" if flags[k]])
        if flags["A"] and not packet.get("audio_events"):
            packet["detections"].append({"channel": "A", "t": t})
        packet["camera"] = view
        packet["health"] = bool(packet.get("health", False) or view["health"])
        fallback = bool(packet.get("fallback", False))
        new_fallback = fallback and not self.fallback_seen
        self.fallback_seen = fallback
        suspicious = any(flags.values()) or packet["health"] or new_fallback
        quiet_before = t - self.last_activity >= self.QUIET
        if quiet_before:
            self.blocked = False
        if suspicious:
            self.last_activity = t
        opened = False
        closed = None
        interrupted = None
        with self.db:
            if self.active is not None and t > self.active["deadline"] + 0.5:
                interrupted = dict(self.active, status="closed", closed_at=t,
                                   reason="acquisition interrupted before investigation completed",
                                   review=self.review(self.packets(self.active["id"])))
                self.db.execute("INSERT OR REPLACE INTO incidents VALUES(?,?)",
                                (interrupted["id"], json.dumps(interrupted)))
                self.active = None
                self.blocked = False
            payload = json.dumps(packet, allow_nan=False)
            self.db.execute("INSERT INTO history VALUES(?,?)", (t, payload))
            if self.active is None and suspicious and (not self.blocked or new_fallback):
                self.active = {"id": str(uuid.uuid4()), "trigger": t,
                               "deadline": t + self.POST, "state": "YELLOW",
                               "status": "open", "confirmed_at": None,
                               "channels": [], "score": 0.0, "reason": "collecting evidence",
                               "fallback": False, "audio_trigger": t if flags["A"] else None}
                opened = True
                self.db.execute("INSERT INTO evidence SELECT ?,stamp,payload FROM history "
                                "WHERE stamp>=?", (self.active["id"], t - self.PRE))
            if self.active is not None:
                a = self.active
                if t <= a["deadline"] + 1e-8:
                    self.db.execute("INSERT OR IGNORE INTO evidence VALUES(?,?,?)",
                                    (a["id"], t, payload))
                if flags["A"] and a["audio_trigger"] is None:
                    a["audio_trigger"] = t
                a["fallback"] = a["fallback"] or new_fallback
                rows = self.packets(a["id"])
                # Retain the longer clip but require a four-second evidence cluster.
                channels = sorted({d["channel"] for r in rows for d in r["detections"]
                                   if 0 <= t - d["t"] <= self.SPAN})
                score, confirmed = self.decider(channels)
                if not opened and (confirmed or a["fallback"]) and a["state"] != "RED":
                    a.update(state="RED", confirmed_at=t, channels=channels, score=score,
                             reason="board fallback alarm" if a["fallback"]
                             else "corroborated activity within four seconds")
                if t >= a["deadline"]:
                    if a["state"] != "RED":
                        a["reason"] = ("equipment fault without corroborated activity"
                                       if any(r["health"] for r in rows)
                                       else "insufficient corroborating evidence")
                    a["status"] = "closed"
                    a["closed_at"] = t
                    a["review"] = self.review(rows)
                    closed = dict(a)
                self.db.execute("INSERT OR REPLACE INTO incidents VALUES(?,?)",
                                (a["id"], json.dumps(a)))
                if closed:
                    self.active = None
                    self.blocked = True
            self.last_stamp, self.last_arrival = t, arrival
            if stream_state is not None:
                self._put_meta("stream_state", stream_state)
            for key, value in {"active": self.active, "stamp": t, "arrival": arrival,
                               "sequence": seq, "session": session,
                               "activity": self.last_activity, "blocked": self.blocked,
                               "fallback_seen": self.fallback_seen}.items():
                self._put_meta(key, value)
            self.db.execute("DELETE FROM history WHERE stamp<?", (t - self.PRE,))
        if closed:
            self._package(closed)
        if interrupted:
            self._package(interrupted)
        return {"accepted": True, "state": self.state,
                "id": self.active["id"] if self.active else None, "closed": closed}

    @property
    def state(self):
        return "GREEN" if self.active is None else self.active["state"]

    @staticmethod
    def review(rows):
        camera = Camera()
        changes, faults = [], []
        for row in rows:
            frame = row.get("frame")
            result = camera.update(row["t"], None if frame is None else unpack_array(frame))
            if result["motion"]:
                changes.append(row["t"])
            if result["health"]:
                faults.append(row["t"])
        return {"method": "classical grayscale frame replay; no person/thermal classifier",
                "motion_times": changes, "fault_times": faults}

    def _package(self, record):
        rows = self.packets(record["id"])
        directory = self.root / "evidence" / record["id"]
        directory.mkdir(parents=True, exist_ok=True)
        arrays = {}
        for i, row in enumerate(rows):
            for kind in ("audio", "frame"):
                if row.get(kind) is not None:
                    arrays[f"{kind}_{i}"] = unpack_array(row[kind])
        raw = directory / "media.npz"
        temporary = directory / "media.tmp.npz"
        np.savez_compressed(temporary, **arrays)
        temporary.replace(raw)
        digest = hashlib.sha256(raw.read_bytes()).hexdigest()
        manifest = dict(record, media_sha256=digest, sample_rate=16000,
                        samples=[{k: v for k, v in row.items() if k not in ("audio", "frame")}
                                 for row in rows],
                        media_keys=list(arrays), camera_type="grayscale; IR interpretation unvalidated")
        target = directory / "manifest.json"
        temporary = directory / "manifest.tmp"
        temporary.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        temporary.replace(target)
        if record["state"] == "RED":
            # Immutable body: lost acknowledgements retry identical evidence bytes.
            payload = json.dumps({"id": record["id"], "manifest": manifest,
                                  "media_base64": base64.b64encode(raw.read_bytes()).decode("ascii")},
                                 sort_keys=True)
            with self.db:
                self.db.execute("INSERT OR IGNORE INTO deliveries(id,payload) VALUES(?,?)",
                                (record["id"], payload))

    def recover_packages(self):
        for record in self.records():
            if record["status"] != "closed":
                continue
            path = self.root / "evidence" / record["id"] / "manifest.json"
            queued = self.db.execute("SELECT 1 FROM deliveries WHERE id=?",
                                     (record["id"],)).fetchone()
            if not path.exists() or (record["state"] == "RED" and not queued):
                self._package(record)

    def close(self):
        self.db.close()
