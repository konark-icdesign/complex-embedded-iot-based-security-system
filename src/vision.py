"""Classical image change and image-health checks, no person recognition."""

import numpy as np


def compensate(reference, current):
    a = np.asarray(reference, dtype=float).ravel()
    b = np.asarray(current, dtype=float).ravel()
    keep = (a > 5) & (a < 250) & (b > 5) & (b < 250)
    gain = 1.0
    offset = 0.0
    if keep.sum() < 100:
        return current.astype(float) - reference, gain, offset
    # Iteratively remove local changes when fitting global gain and offset.
    for _ in range(3):
        aa = a[keep]
        bb = b[keep]
        va = np.mean((aa - aa.mean()) ** 2)
        gain = np.clip(
            np.mean((aa - aa.mean()) * (bb - bb.mean())) / max(va, 1), 0.25, 4
        )
        offset = np.median(bb - gain * aa)
        residual = np.abs(b - (gain * a + offset))
        keep = (
            (residual <= np.quantile(residual, 0.85))
            & (a > 5)
            & (a < 250)
            & (b > 5)
            & (b < 250)
        )
        if keep.sum() < 100:
            break
    return (b - (gain * a + offset)).reshape(reference.shape), gain, offset


class Camera:
    def __init__(self):
        self.previous = None
        self.last_frame = None
        self.last_t = -1.0
        self.repeat_since = None

    def update(self, t, frame):
        if frame is None:
            missing = self.last_t < 0 or t - self.last_t > 0.6
            if missing:
                # Do not compare the first recovered frame with a stale image
                # from before a camera outage.
                self.previous = None
                self.last_frame = None
                self.repeat_since = None
            return dict(
                motion=False,
                fraction=0.0,
                naive=0.0,
                health=missing,
                reason="missing",
            )
        x = np.asarray(frame)
        if x.ndim != 2 or x.size == 0 or not np.isfinite(x).all():
            self.previous = None
            self.last_frame = None
            self.repeat_since = None
            self.last_t = t
            return dict(motion=False, fraction=0.0, naive=0.0, health=True,
                        reason="invalid_frame")
        if self.last_frame is not None and x.shape != self.last_frame.shape:
            self.previous = None
            self.last_frame = x.copy()
            self.repeat_since = None
            self.last_t = t
            return dict(motion=False, fraction=0.0, naive=0.0, health=True,
                        reason="frame_shape_changed")
        health = x.mean() < 4 or x.std() < 1 or np.mean(x >= 254) > 0.85
        reason = "visibility_lost" if health else "ok"
        if self.last_frame is not None and np.array_equal(x, self.last_frame):
            if self.repeat_since is None:
                self.repeat_since = t
            if t - self.repeat_since >= 1.0:
                health = True
                reason = "repeated_frames_suspected"
        else:
            self.repeat_since = None
        motion = False
        fraction = 0.0
        naive = 0.0
        if self.previous is not None and not health:
            res, _, _ = compensate(self.previous, x)
            fraction = float(np.mean(np.abs(res) > 12))
            naive = float(np.mean(np.abs(x.astype(float) - self.previous) > 12))
            motion = fraction > 0.018
        self.previous = x.astype(float) if not health else None
        self.last_frame = x.copy()
        self.last_t = t
        return dict(
            motion=motion,
            fraction=fraction,
            naive=naive,
            health=bool(health),
            reason=reason,
        )


def room(seed=1):
    r = np.random.default_rng(seed)
    yy, xx = np.mgrid[:120, :160]
    return (
        65 + 0.35 * xx + 0.18 * yy + 6 * np.sin(xx * 0.16) + r.normal(0, 4, (120, 160))
    )


def render(base, t, rng, mode="normal", start=8.0, end=14.0):
    f = base.copy()
    active = start <= t < end
    if mode == "disconnect" and t >= start:
        return None
    if mode == "drop" and start <= t < start + 0.2:
        return None
    if mode == "black" and t >= start:
        return np.zeros_like(base, dtype=np.uint8)
    if mode == "light_on" and t >= start:
        f += 65
    if mode == "light_off" and t >= start:
        f -= 48
    if mode == "saturation" and t >= start:
        f[:] = 255
    if mode == "nonuniform" and active:
        f[:, 80:] += 65
    if mode in ("person", "small", "curtain", "warm") and active:
        h, w = (50, 30) if mode == "person" else (16, 14)
        if mode == "warm":
            h, w = 50, 30
        col = 45 + int(14 * np.sin(4 * t))
        row = 35
        f[row : row + h, col : col + w] += 80
    if mode == "freeze" and t >= start:
        return base.astype(np.uint8)
    return np.clip(f + rng.normal(0, 0.8, f.shape), 0, 255).astype(np.uint8)
