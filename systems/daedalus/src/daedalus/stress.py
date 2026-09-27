from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from .metrics import evaluate_predictions


@dataclass(frozen=True)
class RobustnessSurface:
    cells: dict[str, dict]
    profitable_fraction: float
    worst_cumulative_return: float
    worst_profit_factor: float

    def to_dict(self) -> dict:
        return asdict(self)


def cost_sensitivity(y_true, prob_up, future_log_return, threshold: float, base_cost_bps: float, multipliers=(0.0, 1.0, 2.0, 5.0)) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for m in multipliers:
        out[f"{m:g}x"] = evaluate_predictions(
            np.asarray(y_true), np.asarray(prob_up), np.asarray(future_log_return),
            threshold, base_cost_bps * float(m),
        ).to_dict()
    return out


def threshold_cost_surface(
    y_true,
    prob_up,
    future_log_return,
    base_threshold: float,
    base_cost_bps: float,
    cost_multipliers: tuple[float, ...],
    threshold_offsets: tuple[float, ...],
) -> RobustnessSurface:
    """Predeclared stress grid over execution friction and decision threshold.

    This never refits or selects a new model; it reprices the exact protected-holdout probability vector.
    The surface is therefore a robustness gate, not a model-selection search.
    """
    cells: dict[str, dict] = {}
    profitable = 0
    total = 0
    returns: list[float] = []
    pfs: list[float] = []
    for cm in cost_multipliers:
        for off in threshold_offsets:
            threshold = float(np.clip(base_threshold + off, 0.500001, 0.95))
            m = evaluate_predictions(
                np.asarray(y_true), np.asarray(prob_up), np.asarray(future_log_return),
                threshold, base_cost_bps * float(cm),
            ).to_dict()
            key = f"cost_{cm:g}x__threshold_{threshold:.3f}"
            cells[key] = m
            ok = m["trade_count"] > 0 and m["cumulative_return"] > 0 and m["profit_factor"] > 1.0
            profitable += int(ok)
            total += 1
            returns.append(float(m["cumulative_return"]))
            pf = float(m["profit_factor"])
            if np.isfinite(pf):
                pfs.append(pf)
    return RobustnessSurface(
        cells=cells,
        profitable_fraction=float(profitable / total) if total else 0.0,
        worst_cumulative_return=float(min(returns)) if returns else 0.0,
        worst_profit_factor=float(min(pfs)) if pfs else 0.0,
    )
