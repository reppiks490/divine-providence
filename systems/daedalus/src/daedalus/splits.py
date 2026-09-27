from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Fold:
    train_idx: np.ndarray
    test_idx: np.ndarray


class PurgedWalkForwardSplit:
    """Expanding-window time split with explicit purge and embargo gaps."""

    def __init__(self, n_splits: int, min_train_size: int, test_size: int, purge_bars: int, embargo_bars: int):
        self.n_splits = n_splits
        self.min_train_size = min_train_size
        self.test_size = test_size
        self.purge_bars = purge_bars
        self.embargo_bars = embargo_bars

    def split(self, n_samples: int) -> list[Fold]:
        folds: list[Fold] = []
        test_start = self.min_train_size + self.purge_bars
        for _ in range(self.n_splits):
            test_end = min(test_start + self.test_size, n_samples)
            train_end = max(0, test_start - self.purge_bars)
            if train_end < self.min_train_size or test_end - test_start < max(20, self.test_size // 4):
                break
            train_idx = np.arange(0, train_end, dtype=int)
            test_idx = np.arange(test_start, test_end, dtype=int)
            if len(train_idx) and len(test_idx):
                folds.append(Fold(train_idx=train_idx, test_idx=test_idx))
            test_start = test_end + self.embargo_bars
            if test_start >= n_samples:
                break
        return folds
