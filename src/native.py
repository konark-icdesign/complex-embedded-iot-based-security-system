"""ctypes bindings for the independently compiled host-side C numerical core."""

import ctypes as ct
from pathlib import Path
import numpy as np


class NativeCore:
    def __init__(self, path):
        self.lib = ct.CDLL(str(Path(path).resolve()))
        self.double = np.ctypeslib.ndpointer(dtype=np.float64, flags="C_CONTIGUOUS")
        self.integer = np.ctypeslib.ndpointer(dtype=np.int32, flags="C_CONTIGUOUS")
        self.lib.room_features.argtypes = [self.double, self.double]
        self.lib.room_features.restype = ct.c_int
        self.lib.room_confirm.argtypes = [ct.c_uint, ct.POINTER(ct.c_double)]
        self.lib.room_confirm.restype = ct.c_int
        self.lib.room_detect.argtypes = [self.double, self.integer, ct.c_uint,
                                        self.double, self.double, ct.c_double,
                                        self.double, self.integer]
        self.lib.room_detect.restype = None

    def features(self, audio):
        x = np.ascontiguousarray(audio, dtype=np.float64)
        if x.shape != (2048,):
            raise ValueError("C feature kernel needs exactly 2048 mono samples")
        out = np.empty(9, dtype=np.float64)
        valid = self.lib.room_features(x, out)
        if valid < 0:
            raise ValueError("nonfinite audio")
        return {"x": out[None, :], "valid": np.array([bool(valid)])}

    def confirm(self, channels):
        mask = sum(1 << i for i, key in enumerate("AVPMU") if key in channels)
        score = ct.c_double()
        confirmed = self.lib.room_confirm(mask, ct.byref(score))
        return score.value, bool(confirmed)

    def model(self, baseline):
        core = self

        class Model:
            def detect(self, f):
                x = np.ascontiguousarray(f["x"], dtype=np.float64)
                valid = np.ascontiguousarray(f["valid"], dtype=np.int32)
                scores = np.empty(len(x), dtype=np.float64)
                flags = np.empty(len(x), dtype=np.int32)
                core.lib.room_detect(x, valid, len(x),
                                     np.ascontiguousarray(baseline.center, dtype=np.float64),
                                     np.ascontiguousarray(baseline.scale, dtype=np.float64),
                                     baseline.threshold, scores, flags)
                return scores, flags.astype(bool)

        return Model()
