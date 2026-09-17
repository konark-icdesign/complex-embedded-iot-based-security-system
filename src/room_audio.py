"""Room-specific calibration; detection uses the existing Python/C feature core."""

import numpy as np

from .dsp import Baseline, FLOORS, background, features


def fit_room(training, calibration, floor_fraction=0.1, margin=1.2):
    """Fit on approved normal sessions only. Freeze before evaluating events.

    Unlike the general baseline, sensitivity follows the measured room variation.
    The maximum normal calibration score sets the threshold, with headroom.
    A new room/microphone needs its own normal recordings and validation.
    """
    arrays = [np.asarray(a, dtype=float) for a in (training, calibration)]
    if any(a.ndim != 2 or a.shape[1] != len(FLOORS) or len(a) < 3
           or not np.isfinite(a).all() for a in arrays):
        raise ValueError("Need finite training and calibration feature matrices")
    if not 0 < floor_fraction <= 1 or not np.isfinite(margin) or margin < 1:
        raise ValueError("Invalid calibration limits")
    training, calibration = arrays
    center = np.median(training, axis=0)
    scale = np.maximum(1.4826 * np.median(abs(training-center), axis=0),
                       FLOORS * floor_fraction)
    model = Baseline(center, scale)
    model.threshold = max(1.0, float(model.score(calibration).max()) * margin)
    return model


def quiet_training():
    """Synthetic commissioning data; these are not recordings of the user's room."""
    def collect(seeds):
        return np.concatenate([features(background(12, s, gain=g))["x"]
                               for s, g in zip(seeds, (0.5, 1, 1.7, 2))])
    return collect((11, 12, 13, 14)), collect((101, 102, 103, 104))


def quiet_model():
    return fit_room(*quiet_training())
