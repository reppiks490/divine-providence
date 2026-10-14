from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Fold:
    train_idx: np.ndarray
    test_idx: np.ndarray


class PurgedWalkForwardSplit:
    """Expanding-window time split with explicit purge and embargo gaps."""

    def __init__(self, n_splits: int, min_train_size: int, test_size: int, purge_bars: int, embargo_bars: int,
                 *, placement: str = "sequential", max_train_size: int | None = None):
        if placement not in {"sequential", "spread"}:
            raise ValueError("Unknown fold placement")
        if min(n_splits, min_train_size, test_size) < 1 or min(purge_bars, embargo_bars) < 0:
            raise ValueError("Invalid split geometry")
        if max_train_size is not None and (type(max_train_size) is not int or max_train_size < min_train_size):
            raise ValueError("Training window smaller than minimum")
        self.placement = placement
        self.max_train_size = max_train_size
        self.n_splits = n_splits
        self.min_train_size = min_train_size
        self.test_size = test_size
        self.purge_bars = purge_bars
        self.embargo_bars = embargo_bars

    def split(self, n_samples: int) -> list[Fold]:
        folds: list[Fold] = []
        test_start = self.min_train_size + self.purge_bars
        if self.placement == "spread":
            last = n_samples - self.test_size
            if last < test_start:
                return folds
            count = min(self.n_splits, 1 + (last - test_start) // (self.test_size + self.embargo_bars))
            starts = np.linspace(test_start, last, count, dtype=int) if count > 1 else [test_start]
            for start in starts:
                end = int(start) - self.purge_bars
                begin = max(0, end - self.max_train_size) if self.max_train_size else 0
                folds.append(Fold(np.arange(begin, end, dtype=int),
                                  np.arange(int(start), int(start) + self.test_size, dtype=int)))
            return folds
        for _ in range(self.n_splits):
            test_end = min(test_start + self.test_size, n_samples)
            train_end = max(0, test_start - self.purge_bars)
            if train_end < self.min_train_size or test_end - test_start < max(20, self.test_size // 4):
                break
            train_start = max(0, train_end - self.max_train_size) if self.max_train_size else 0
            train_idx = np.arange(train_start, train_end, dtype=int)
            test_idx = np.arange(test_start, test_end, dtype=int)
            if len(train_idx) and len(test_idx):
                folds.append(Fold(train_idx=train_idx, test_idx=test_idx))
            test_start = test_end + self.embargo_bars
            if test_start >= n_samples:
                break
        return folds
