
from __future__ import annotations

def chronological_purged_partitions(n_rows: int, train_frac=0.60, validation_frac=0.20, purge_bars=24, embargo_bars=24):
    """
    Creates development partitions while keeping the final holdout untouched.
    Purge/embargo zones are excluded from train/validation boundaries.
    """
    if n_rows < 50:
        raise ValueError("too few rows for a protected chronological split")
    if not (0 < train_frac < 1 and 0 < validation_frac < 1 and train_frac + validation_frac < 1):
        raise ValueError("invalid fractions")
    if purge_bars < 0 or embargo_bars < 0:
        raise ValueError("purge/embargo must be non-negative")

    train_end_raw = int(n_rows * train_frac)
    val_end_raw = int(n_rows * (train_frac + validation_frac))

    train = (0, max(0, train_end_raw - purge_bars))
    train_to_val_excluded = (train[1], min(n_rows, train_end_raw + embargo_bars))
    validation = (train_to_val_excluded[1], max(train_to_val_excluded[1], val_end_raw - purge_bars))
    val_to_holdout_excluded = (validation[1], min(n_rows, val_end_raw + embargo_bars))
    holdout = (val_to_holdout_excluded[1], n_rows)

    if not (train[0] < train[1] <= validation[0] < validation[1] <= holdout[0] < holdout[1]):
        raise ValueError("split settings consume too much data")

    return {
        "train": train,
        "purge_embargo_between_train_validation": train_to_val_excluded,
        "validation": validation,
        "purge_embargo_before_holdout": val_to_holdout_excluded,
        "final_holdout_untouched": holdout,
        "n_rows": n_rows,
        "policy": {
            "train_frac": train_frac,
            "validation_frac": validation_frac,
            "purge_bars": purge_bars,
            "embargo_bars": embargo_bars,
        }
    }
