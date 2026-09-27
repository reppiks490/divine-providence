from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr


@dataclass(frozen=True)
class HypothesisResult:
    feature: str
    method: str
    statistic: float
    pvalue: float
    qvalue: float
    rejected_null: bool
    n: int

    def to_dict(self) -> dict:
        return asdict(self)


def benjamini_hochberg(pvalues: list[float]) -> list[float]:
    if not pvalues:
        return []
    p = np.asarray(pvalues, dtype=float)
    if np.any(~np.isfinite(p)) or np.any((p < 0) | (p > 1)):
        raise ValueError("pvalues must be finite values in [0, 1]")
    order = np.argsort(p)
    ranked = p[order]
    m = len(p)
    adjusted = ranked * m / np.arange(1, m + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    adjusted = np.clip(adjusted, 0, 1)
    out = np.empty_like(adjusted)
    out[order] = adjusted
    return out.tolist()


def screen_features(
    x: pd.DataFrame,
    future_return: pd.Series,
    alpha: float = 0.05,
    method: str = "spearman",
    min_observations: int = 80,
) -> list[HypothesisResult]:
    if method not in {"spearman", "pearson"}:
        raise ValueError("method must be spearman or pearson")
    raw: list[tuple[str, float, float, int]] = []
    for c in x.columns:
        pair = pd.concat([x[c], future_return], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
        if len(pair) < min_observations or pair.iloc[:, 0].nunique() < 3:
            continue
        if method == "pearson":
            stat, p = pearsonr(pair.iloc[:, 0], pair.iloc[:, 1])
        else:
            stat, p = spearmanr(pair.iloc[:, 0], pair.iloc[:, 1])
        if np.isfinite(stat) and np.isfinite(p):
            raw.append((c, float(stat), float(p), len(pair)))
    qs = benjamini_hochberg([r[2] for r in raw])
    return [
        HypothesisResult(feature=c, method=method, statistic=s, pvalue=p, qvalue=q, rejected_null=q <= alpha, n=n)
        for (c, s, p, n), q in zip(raw, qs)
    ]



def screen_interactions(
    x: pd.DataFrame,
    future_return: pd.Series,
    base_results: list[HypothesisResult],
    *,
    alpha: float = 0.05,
    seed_features: int = 10,
    max_interactions: int = 30,
    min_observations: int = 80,
) -> list[HypothesisResult]:
    """Screen standardized pairwise products using development data only.

    The inputs are chosen from the strongest univariate development hypotheses, but
    interaction p-values receive their own Benjamini-Hochberg correction. These results
    are discovery evidence only; they are not injected into model validation without a
    future nested-selection protocol.
    """
    if max_interactions <= 0 or seed_features < 2 or not base_results:
        return []
    ranked = sorted(base_results, key=lambda r: (r.qvalue, r.pvalue, -abs(r.statistic)))
    seeds = [r.feature for r in ranked if r.feature in x.columns][: int(seed_features)]
    raw: list[tuple[str, float, float, int]] = []
    tested = 0
    for i, a in enumerate(seeds):
        if tested >= max_interactions:
            break
        aa = pd.to_numeric(x[a], errors="coerce")
        astd = float(aa.std())
        za = (aa - float(aa.mean())) / astd if np.isfinite(astd) and astd > 0 else aa * 0.0
        for b in seeds[i + 1 :]:
            if tested >= max_interactions:
                break
            bb = pd.to_numeric(x[b], errors="coerce")
            bstd = float(bb.std())
            zb = (bb - float(bb.mean())) / bstd if np.isfinite(bstd) and bstd > 0 else bb * 0.0
            name = f"interaction::{a}*{b}"
            pair = pd.concat([(za * zb).rename(name), future_return], axis=1).replace(
                [np.inf, -np.inf], np.nan
            ).dropna()
            tested += 1
            if len(pair) < min_observations or pair.iloc[:, 0].nunique() < 3:
                continue
            stat, p = spearmanr(pair.iloc[:, 0], pair.iloc[:, 1])
            if np.isfinite(stat) and np.isfinite(p):
                raw.append((name, float(stat), float(p), len(pair)))
    qs = benjamini_hochberg([r[2] for r in raw])
    return [
        HypothesisResult(
            feature=name,
            method="spearman_interaction",
            statistic=stat,
            pvalue=p,
            qvalue=q,
            rejected_null=q <= alpha,
            n=n,
        )
        for (name, stat, p, n), q in zip(raw, qs)
    ]
