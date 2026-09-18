"""Evidence fusion, sensor filters and a local notification queue."""

from collections import deque
from dataclasses import dataclass
import json
import sqlite3
import math
import uuid


@dataclass
class Config:
    span: float = 4.0
    red_score: float = 5.0
    clear_seconds: float = 3.0
    red_hold: float = 6.0


class Sensors:
    def __init__(self):
        self.distance = deque(maxlen=5)
        self.p = 0
        self.m = 0
        self.u = 0
        self.invalid_range = 0

    def update(self, p, m, d, valid=True):
        self.p = min(self.p + 1, 3) if p and valid else 0
        self.m = min(self.m + 1, 3) if m and valid else 0
        range_fault = not valid or not math.isfinite(d) or not 0.02 <= d <= 4.0
        if range_fault:
            self.invalid_range = min(self.invalid_range + 1, 3)
            if self.invalid_range >= 3:
                self.distance.clear()
                self.u = 0
            return self.p >= 3, self.m >= 3, self.u >= 3, float("nan"), True
        self.invalid_range = 0
        self.distance.append(d)
        median = sorted(self.distance)[len(self.distance) // 2]
        near = len(self.distance) == 5 and median < 1.8
        self.u = min(self.u + 1, 3) if near else 0
        return self.p >= 3, self.m >= 3, self.u >= 3, median, False


class Fusion:
    # Camera faults add no points; camera motion is one evidence channel.
    weights = dict(A=1.5, V=3.0, P=2.0, M=2.0, U=2.0)

    def __init__(self, config=None):
        self.c = config or Config()
        self.last = {k: -1e9 for k in self.weights}
        self.state = 0
        self.changed = 0.0
        self.last_yellow = -1e9
        self.last_activity = -1e9
        self.alerts = []
        self.last_t = -1.0
        self.active_id = None

    def update(self, t, evidence, health=False, captured=None):
        if t < self.last_t:
            raise ValueError("Events must be processed in monotonic acquisition order")
        self.last_t = t
        for k in self.last:
            stamp = t if captured is None else captured.get(k, t)
            if evidence.get(k, False) and 0 <= t - stamp <= 0.5:
                self.last[k] = max(self.last[k], stamp)
        present = {k for k, v in self.last.items() if t - v <= self.c.span}
        score = sum(self.weights[k] for k in present)
        # Audio+PIR alone is not enough: two noises/detections can coincide.
        rule = (
            ("V" in present and bool(present & {"P", "M", "U"}))
            or len(present & {"P", "M", "U"}) >= 3
            or ("A" in present and len(present & {"P", "M", "U"}) >= 2)
        )
        confirmed = rule and score >= self.c.red_score
        suspicious = bool(present) or health
        if present:
            self.last_activity = t
        if suspicious:
            self.last_yellow = t
        entered = False
        if confirmed:
            if self.state == 0:
                self.state = 1
                self.changed = t
            elif self.state != 2:
                self.state = 2
                self.changed = t
                entered = True
                self.active_id = str(uuid.uuid4())
                self.alerts.append(
                    dict(
                        id=self.active_id,
                        t=t,
                        score=score,
                        channels=sorted(present),
                        conclusion="correlated unusual activity",
                    )
                )
        elif self.state == 2:
            if (
                t - self.changed >= self.c.red_hold
                and t - self.last_activity >= self.c.clear_seconds
            ):
                self.state = 1 if health else 0
                self.changed = t
        elif suspicious:
            if self.state != 1:
                self.state = 1
                self.changed = t
        elif t - self.last_yellow >= self.c.clear_seconds:
            self.state = 0
        return self.state, score, entered, sorted(present)


class Outbox:
    """SQLite queue with a local mock receiver.

    Retries reuse the event ID, which is unique in the receiver table.
    """

    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript(
            "CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY,payload TEXT,acked INTEGER DEFAULT 0);"
            "CREATE TABLE IF NOT EXISTS receiver(id TEXT PRIMARY KEY,payload TEXT);"
        )
        self.attempts = 0

    def enqueue(self, event):
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO outbox(id,payload) VALUES(?,?)",
                (event["id"], json.dumps(event, sort_keys=True)),
            )

    def pump(self, online, lose_ack=False):
        if not online:
            return
        for key, payload in self.db.execute(
            "SELECT id,payload FROM outbox WHERE acked=0"
        ).fetchall():
            self.attempts += 1
            with self.db:
                self.db.execute(
                    "INSERT OR IGNORE INTO receiver VALUES(?,?)", (key, payload)
                )
                if not lose_ack:
                    self.db.execute("UPDATE outbox SET acked=1 WHERE id=?", (key,))

    def count(self):
        return self.db.execute("SELECT count(*) FROM receiver").fetchone()[0]

    def pending(self):
        return self.db.execute("SELECT count(*) FROM outbox WHERE acked=0").fetchone()[
            0
        ]

    def close(self):
        self.db.close()


class PacketGate:
    """Reject stale, duplicated, future or delayed observations; arrival is not capture time."""

    def __init__(self):
        self.seq = -1

    def accept(self, seq, captured, arrival):
        if seq <= self.seq or not 0 <= arrival - captured <= 0.5:
            return False
        self.seq = seq
        return True
