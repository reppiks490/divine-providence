from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp


def feature_drift_score(train: pd.DataFrame, test: pd.DataFrame) -> tuple[float, dict[str, float]]:
    scores: dict[str, float] = {}
    for c in train.columns:
        a = pd.to_numeric(train[c], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
        b = pd.to_numeric(test[c], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
        if len(a) < 20 or len(b) < 20:
            scores[c] = 0.0
        else:
            scores[c] = float(ks_2samp(a, b, method="auto").statistic)
    return (float(np.mean(list(scores.values()))) if scores else 0.0), scores
