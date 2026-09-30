from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math
from typing import Mapping
import numpy as np


@dataclass(frozen=True)
class LatentFactorPoint:
    event_ns: int
    score: float
    explained_variance: float
    loadings: Mapping[str, float]
    coverage: float


class CausalPCAFactor:
    """Online PCA factor fitted only on frames strictly prior to the emitted point."""

    def __init__(self, window: int = 256, min_obs: int = 48, min_coverage: float = 0.65) -> None:
        if int(min_obs) < 2 or int(window) < int(min_obs):
            raise ValueError("require window >= min_obs >= 2")
        coverage=float(min_coverage)
        if not math.isfinite(coverage) or not 0.0 <= coverage <= 1.0:
            raise ValueError("min_coverage must be finite and in [0,1]")
        self.window = int(window)
        self.min_obs = int(min_obs)
        self.min_coverage = coverage
        self.history: deque[dict[str, float]] = deque(maxlen=self.window)

    def update(self, event_ns: int, frame: Mapping[str, float]) -> LatentFactorPoint:
        if type(event_ns) is not int or event_ns < 0:
            raise ValueError("event_ns must be a non-negative integer")
        current = {k: float(v) for k, v in frame.items() if math.isfinite(float(v))}
        if self.history:
            common = set(current)
            for hist in self.history:
                common &= set(hist)
            keys = sorted(common)
            expected_keys=set(current)
            for hist in self.history:
                expected_keys.update(hist)
            expected = max(len(expected_keys), 1)
        else:
            keys = sorted(current)
            expected = max(len(current), 1)

        score = math.nan
        explained = math.nan
        loadings: dict[str, float] = {}
        if len(self.history) >= self.min_obs and len(keys) >= 2:
            X = np.array([[h[k] for k in keys] for h in self.history], dtype=float)
            mu = X.mean(axis=0)
            sd = X.std(axis=0)
            usable = sd > 1e-12
            if int(usable.sum()) >= 2:
                ukeys = [k for k, ok in zip(keys, usable) if ok]
                Z = (X[:, usable] - mu[usable]) / sd[usable]
                _, singular, vt = np.linalg.svd(Z, full_matrices=False)
                vec = vt[0]
                # Fix PCA sign ambiguity so repeat runs are bitwise stable in orientation.
                if vec.sum() < 0:
                    vec = -vec
                total = float((singular * singular).sum())
                explained = float(singular[0] ** 2 / total) if total > 0 else math.nan
                z = (np.array([current[k] for k in ukeys]) - mu[usable]) / sd[usable]
                score = float(np.dot(z, vec) / math.sqrt(len(vec)))
                loadings = {k: float(v) for k, v in zip(ukeys, vec)}

        coverage = len(current) / expected
        if coverage >= self.min_coverage:
            self.history.append(current)
        return LatentFactorPoint(
            event_ns=int(event_ns),
            score=score,
            explained_variance=explained,
            loadings=loadings,
            coverage=max(0.0, min(1.0, coverage)),
        )
