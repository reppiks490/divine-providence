from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from sklearn.metrics import brier_score_loss, roc_auc_score


@dataclass(frozen=True)
class PerformanceMetrics:
    auc: float
    brier: float
    brier_baseline: float
    brier_improvement: float
    trade_sharpe_like: float
    trade_sortino_like: float
    max_drawdown: float
    profit_factor: float
    trade_count: int
    hit_rate: float
    expectancy: float
    cumulative_return: float
    exposure: float
    avg_abs_probability_edge: float
    tail_loss_05: float

    @property
    def sharpe(self) -> float:
        return self.trade_sharpe_like

    @property
    def sortino(self) -> float:
        return self.trade_sortino_like

    def to_dict(self) -> dict:
        d = asdict(self)
        d["sharpe"] = self.trade_sharpe_like
        d["sortino"] = self.trade_sortino_like
        return d


def _safe_auc(y: np.ndarray, p: np.ndarray) -> float:
    return float(roc_auc_score(y, p)) if len(y) and len(np.unique(y)) > 1 else 0.5


def non_overlapping_trade_pnl(
    prob_up: np.ndarray,
    future_log_return: np.ndarray,
    threshold: float,
    round_trip_cost_bps: float,
    horizon_bars: int = 1,
    execution_stride_bars: int | None = None,
    source_positions: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Return accepted signal positions and log-PnL without overlapping holding windows."""
    p = np.asarray(prob_up, dtype=float)
    r = np.asarray(future_log_return, dtype=float)
    n = min(len(p), len(r))
    if n == 0:
        return np.array([], dtype=int), np.array([], dtype=float)
    p, r = p[:n], r[:n]
    pos = np.arange(n, dtype=int) if source_positions is None else np.asarray(source_positions, dtype=int)[:n]
    if len(pos) != n:
        raise ValueError("source_positions length must match probability/return vectors")
    stride = max(1, int(execution_stride_bars or horizon_bars))
    cost = float(round_trip_cost_bps) / 10_000.0
    accepted_positions: list[int] = []
    pnl: list[float] = []
    next_allowed_source_position: int | None = None
    for i in range(n):
        if not (np.isfinite(p[i]) and np.isfinite(r[i])):
            continue
        source_pos = int(pos[i])
        if next_allowed_source_position is not None and source_pos < next_allowed_source_position:
            continue
        side = 1.0 if p[i] >= threshold else (-1.0 if p[i] <= 1.0 - threshold else 0.0)
        if side == 0.0:
            continue
        accepted_positions.append(source_pos)
        pnl.append(float(side * r[i] - cost))
        next_allowed_source_position = source_pos + stride
    return np.asarray(accepted_positions, dtype=int), np.asarray(pnl, dtype=float)


def _baseline_vector(
    y: np.ndarray,
    baseline_probability: float | np.ndarray | None,
) -> np.ndarray:
    if baseline_probability is None:
        base = float(np.mean(y)) if len(y) else 0.5
        return np.full(len(y), base, dtype=float)
    if np.isscalar(baseline_probability):
        return np.full(len(y), float(baseline_probability), dtype=float)
    b = np.asarray(baseline_probability, dtype=float)
    if len(b) != len(y):
        raise ValueError("baseline probability vector length must match y_true")
    return np.clip(b, 1e-9, 1 - 1e-9)


def evaluate_predictions(
    y_true: np.ndarray,
    prob_up: np.ndarray,
    future_log_return: np.ndarray,
    threshold: float,
    round_trip_cost_bps: float,
    horizon_bars: int = 1,
    execution_stride_bars: int | None = None,
    baseline_probability: float | np.ndarray | None = None,
    source_positions: np.ndarray | None = None,
) -> PerformanceMetrics:
    y = np.asarray(y_true, dtype=int)
    p = np.asarray(prob_up, dtype=float)
    r = np.asarray(future_log_return, dtype=float)
    n = min(len(y), len(p), len(r))
    y, p, r = y[:n], p[:n], r[:n]
    pos = np.arange(n, dtype=int) if source_positions is None else np.asarray(source_positions, dtype=int)[:n]
    finite = np.isfinite(p) & np.isfinite(r)
    y, p, r, pos = y[finite], np.clip(p[finite], 1e-9, 1 - 1e-9), r[finite], pos[finite]

    auc = _safe_auc(y, p)
    if len(y):
        brier = float(brier_score_loss(y, p))
        if baseline_probability is None or np.isscalar(baseline_probability):
            base_vec = _baseline_vector(y, baseline_probability)
        else:
            raw_base = np.asarray(baseline_probability, dtype=float)[:n]
            base_vec = np.clip(raw_base[finite], 1e-9, 1 - 1e-9)
        brier_base = float(np.mean((y - base_vec) ** 2))
    else:
        brier, brier_base = 1.0, 1.0
    brier_improvement = brier_base - brier

    _, trade_pnl = non_overlapping_trade_pnl(
        p,
        r,
        threshold,
        round_trip_cost_bps,
        horizon_bars=horizon_bars,
        execution_stride_bars=execution_stride_bars,
        source_positions=pos,
    )
    trade_count = int(len(trade_pnl))
    if trade_count > 1 and np.std(trade_pnl, ddof=1) > 0:
        sharpe_like = float(np.mean(trade_pnl) / np.std(trade_pnl, ddof=1) * np.sqrt(trade_count))
    else:
        sharpe_like = 0.0
    downside = trade_pnl[trade_pnl < 0]
    if trade_count and len(downside) > 1 and np.std(downside, ddof=1) > 0:
        sortino_like = float(np.mean(trade_pnl) / np.std(downside, ddof=1) * np.sqrt(trade_count))
    else:
        sortino_like = 0.0

    if trade_count:
        equity = np.exp(np.cumsum(trade_pnl))
        series = np.r_[1.0, equity]
        peak = np.maximum.accumulate(series)
        drawdown = 1.0 - series / np.maximum(peak, 1e-12)
        max_dd = float(np.max(drawdown))
        cumulative_return = float(equity[-1] - 1.0)
    else:
        max_dd, cumulative_return = 0.0, 0.0

    gains = float(trade_pnl[trade_pnl > 0].sum()) if trade_count else 0.0
    losses = float(-trade_pnl[trade_pnl < 0].sum()) if trade_count else 0.0
    profit_factor = gains / losses if losses > 0 else (float("inf") if gains > 0 else 0.0)
    hit_rate = float(np.mean(trade_pnl > 0)) if trade_count else 0.0
    expectancy = float(np.mean(trade_pnl)) if trade_count else 0.0
    stride = max(1, int(execution_stride_bars or horizon_bars))
    exposure = float(min(1.0, trade_count * stride / len(p))) if len(p) else 0.0
    avg_edge = float(np.mean(np.abs(p - 0.5))) if len(p) else 0.0
    tail_loss = float(np.quantile(trade_pnl, 0.05)) if trade_count else 0.0

    return PerformanceMetrics(
        auc=auc,
        brier=brier,
        brier_baseline=brier_base,
        brier_improvement=brier_improvement,
        trade_sharpe_like=sharpe_like,
        trade_sortino_like=sortino_like,
        max_drawdown=max_dd,
        profit_factor=float(profit_factor),
        trade_count=trade_count,
        hit_rate=hit_rate,
        expectancy=expectancy,
        cumulative_return=cumulative_return,
        exposure=exposure,
        avg_abs_probability_edge=avg_edge,
        tail_loss_05=tail_loss,
    )
