from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import beta as beta_dist
from scipy.stats import ks_2samp
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from .config import ShadowConfig
from .metrics import non_overlapping_trade_pnl


SCHEMA = """
CREATE TABLE IF NOT EXISTS shadow_candidates (
    candidate_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    manifest_json TEXT NOT NULL,
    status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS shadow_observations (
    candidate_id TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    source_time REAL,
    probability REAL NOT NULL,
    realized_return REAL,
    mature INTEGER NOT NULL,
    metadata_json TEXT NOT NULL,
    PRIMARY KEY(candidate_id, observed_at, source_time)
);
CREATE INDEX IF NOT EXISTS idx_shadow_obs_candidate ON shadow_observations(candidate_id);

CREATE TABLE IF NOT EXISTS shadow_predictions_v2 (
    prediction_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    source_time REAL,
    source_key TEXT,
    probability REAL NOT NULL,
    threshold REAL,
    horizon_bars INTEGER,
    metadata_json TEXT NOT NULL,
    metadata_sha256 TEXT NOT NULL,
    FOREIGN KEY(candidate_id) REFERENCES shadow_candidates(candidate_id)
);
CREATE INDEX IF NOT EXISTS idx_shadow_pred_candidate ON shadow_predictions_v2(candidate_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_shadow_pred_source_time ON shadow_predictions_v2(candidate_id, source_time);

CREATE TABLE IF NOT EXISTS shadow_outcomes_v2 (
    prediction_id TEXT PRIMARY KEY,
    matured_at TEXT NOT NULL,
    realized_return REAL NOT NULL,
    target_source_time REAL,
    metadata_json TEXT NOT NULL,
    metadata_sha256 TEXT NOT NULL,
    FOREIGN KEY(prediction_id) REFERENCES shadow_predictions_v2(prediction_id)
);

CREATE TABLE IF NOT EXISTS shadow_status_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT NOT NULL,
    reason TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY(candidate_id) REFERENCES shadow_candidates(candidate_id)
);
CREATE INDEX IF NOT EXISTS idx_shadow_status_candidate ON shadow_status_events(candidate_id, event_id);
"""

_ALLOWED_STATUSES = {
    "SHADOW",
    "SHADOW_WARMING",
    "SHADOW_HEALTHY",
    "SHADOW_WATCH",
    "SHADOW_DEGRADED",
    "SHADOW_RETIRED",
}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _finite_float(name: str, value: float) -> float:
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{name} must be finite")
    return out


def _safe_auc(y: np.ndarray, p: np.ndarray) -> float:
    return float(roc_auc_score(y, p)) if len(y) and len(np.unique(y)) > 1 else 0.5


def _max_drawdown_from_log_pnl(pnl: np.ndarray) -> tuple[float, float]:
    if not len(pnl):
        return 0.0, 0.0
    equity = np.exp(np.cumsum(pnl))
    path = np.r_[1.0, equity]
    peak = np.maximum.accumulate(path)
    dd = 1.0 - path / np.maximum(peak, 1e-12)
    return float(np.max(dd)), float(equity[-1] - 1.0)


def _calibration_bins(y: np.ndarray, p: np.ndarray, bins: int) -> tuple[list[dict[str, float | int]], float, float]:
    bins = max(2, int(bins))
    edges = np.linspace(0.0, 1.0, bins + 1)
    rows: list[dict[str, float | int]] = []
    ece = 0.0
    mce = 0.0
    n = max(1, len(p))
    for i in range(bins):
        lo, hi = float(edges[i]), float(edges[i + 1])
        mask = (p >= lo) & ((p < hi) if i < bins - 1 else (p <= hi))
        count = int(mask.sum())
        if not count:
            continue
        mean_p = float(np.mean(p[mask]))
        observed = float(np.mean(y[mask]))
        gap = abs(mean_p - observed)
        ece += (count / n) * gap
        mce = max(mce, gap)
        rows.append({
            "lower": lo,
            "upper": hi,
            "count": count,
            "mean_probability": mean_p,
            "observed_frequency": observed,
            "absolute_gap": float(gap),
        })
    return rows, float(ece), float(mce)


def _extract_reference_metrics(manifest: dict[str, Any]) -> dict[str, float]:
    """Extract protected-holdout metrics from supported manifest shapes."""
    candidates = [manifest]
    if isinstance(manifest.get("candidate"), dict):
        candidates.append(manifest["candidate"])
    for obj in candidates:
        hold = obj.get("protected_holdout") if isinstance(obj, dict) else None
        metrics = hold.get("metrics") if isinstance(hold, dict) else None
        if isinstance(metrics, dict):
            out: dict[str, float] = {}
            for key in ("auc", "brier", "brier_improvement", "max_drawdown", "profit_factor", "trade_count"):
                val = metrics.get(key)
                if isinstance(val, (int, float)) and math.isfinite(float(val)):
                    out[key] = float(val)
            return out
    return {}


@dataclass(frozen=True)
class ShadowHealth:
    candidate_id: str
    recommended_status: str
    mature_observations: int
    failures: tuple[str, ...]
    warnings: tuple[str, ...]
    reference_metrics: dict[str, float]
    current_metrics: dict[str, Any]
    recent_metrics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ShadowBook:
    """Immutable forward-evidence store for research candidates.

    Predictions are recorded before outcomes exist. Outcomes are append-once and cannot
    be overwritten with a different result. Repeated source timestamps are supported by
    independent prediction IDs, which matters for alternate chart constructions.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as con:
            con.execute("PRAGMA foreign_keys=ON")
            con.executescript(SCHEMA)
            self._migrate_candidate_columns(con)

    @staticmethod
    def _migrate_candidate_columns(con: sqlite3.Connection) -> None:
        cols = {row[1] for row in con.execute("PRAGMA table_info(shadow_candidates)").fetchall()}
        if "manifest_sha256" not in cols:
            con.execute("ALTER TABLE shadow_candidates ADD COLUMN manifest_sha256 TEXT")
            rows = con.execute("SELECT candidate_id, manifest_json FROM shadow_candidates").fetchall()
            for candidate_id, raw in rows:
                try:
                    manifest = json.loads(raw)
                    digest = _sha256_json(manifest)
                except (json.JSONDecodeError, TypeError):
                    digest = hashlib.sha256(str(raw).encode("utf-8")).hexdigest()
                con.execute(
                    "UPDATE shadow_candidates SET manifest_sha256=? WHERE candidate_id=?",
                    (digest, candidate_id),
                )

    def register(self, candidate_id: str, manifest: dict[str, Any]) -> None:
        """Idempotently register an immutable candidate manifest.

        Re-registering the exact same manifest is allowed. Reusing a candidate ID for a
        different manifest is rejected because that would corrupt forward evidence.
        """
        candidate_id = str(candidate_id).strip()
        if not candidate_id:
            raise ValueError("candidate_id cannot be empty")
        manifest_json = _canonical_json(manifest)
        digest = _sha256_json(manifest)
        with sqlite3.connect(self.path) as con:
            con.execute("PRAGMA foreign_keys=ON")
            row = con.execute(
                "SELECT manifest_sha256, manifest_json FROM shadow_candidates WHERE candidate_id=?",
                (candidate_id,),
            ).fetchone()
            if row is not None:
                existing_digest = row[0] or hashlib.sha256(str(row[1]).encode("utf-8")).hexdigest()
                if existing_digest != digest:
                    raise ValueError(f"candidate_id {candidate_id!r} is already bound to a different manifest")
                return
            con.execute(
                "INSERT INTO shadow_candidates(candidate_id, created_at, manifest_json, status, manifest_sha256) "
                "VALUES (?, ?, ?, ?, ?)",
                (candidate_id, _utcnow(), manifest_json, "SHADOW", digest),
            )
            con.execute(
                "INSERT INTO shadow_status_events(candidate_id, occurred_at, from_status, to_status, reason, evidence_json) "
                "VALUES (?, ?, NULL, 'SHADOW', 'candidate_registered', '{}')",
                (candidate_id, _utcnow()),
            )

    def candidate(self, candidate_id: str) -> dict[str, Any]:
        with sqlite3.connect(self.path) as con:
            row = con.execute(
                "SELECT candidate_id, created_at, manifest_json, status, manifest_sha256 "
                "FROM shadow_candidates WHERE candidate_id=?",
                (candidate_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown shadow candidate: {candidate_id}")
        return {
            "candidate_id": row[0],
            "created_at": row[1],
            "manifest": json.loads(row[2]),
            "status": row[3],
            "manifest_sha256": row[4],
        }

    def set_status(
        self,
        candidate_id: str,
        to_status: str,
        reason: str,
        evidence: dict[str, Any] | None = None,
    ) -> None:
        if to_status not in _ALLOWED_STATUSES:
            raise ValueError(f"Unsupported shadow status: {to_status}")
        with sqlite3.connect(self.path) as con:
            con.execute("PRAGMA foreign_keys=ON")
            row = con.execute(
                "SELECT status FROM shadow_candidates WHERE candidate_id=?",
                (candidate_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown shadow candidate: {candidate_id}")
            prior = str(row[0])
            if prior == "SHADOW_RETIRED" and to_status != "SHADOW_RETIRED":
                raise ValueError("retired shadow candidates cannot be reactivated in-place")
            con.execute(
                "UPDATE shadow_candidates SET status=? WHERE candidate_id=?",
                (to_status, candidate_id),
            )
            con.execute(
                "INSERT INTO shadow_status_events(candidate_id, occurred_at, from_status, to_status, reason, evidence_json) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (candidate_id, _utcnow(), prior, to_status, str(reason), _canonical_json(evidence or {})),
            )

    def status_history(self, candidate_id: str) -> list[dict[str, Any]]:
        with sqlite3.connect(self.path) as con:
            rows = con.execute(
                "SELECT event_id, occurred_at, from_status, to_status, reason, evidence_json "
                "FROM shadow_status_events WHERE candidate_id=? ORDER BY event_id",
                (candidate_id,),
            ).fetchall()
        return [
            {
                "event_id": int(r[0]),
                "occurred_at": r[1],
                "from_status": r[2],
                "to_status": r[3],
                "reason": r[4],
                "evidence": json.loads(r[5]),
            }
            for r in rows
        ]

    def record_prediction(
        self,
        candidate_id: str,
        probability: float,
        source_time: float | None,
        metadata: dict[str, Any] | None = None,
        *,
        source_key: str | None = None,
        threshold: float | None = None,
        horizon_bars: int | None = None,
        allow_out_of_order: bool = False,
    ) -> str:
        """Record a prediction and return its immutable prediction_id.

        source_time may repeat. By default it may not move backwards for a candidate,
        protecting forward evidence from accidental replay/backfill contamination.
        """
        p = _finite_float("probability", probability)
        if not 0.0 <= p <= 1.0:
            raise ValueError("probability must be in [0, 1]")
        st = None if source_time is None else _finite_float("source_time", source_time)
        if threshold is not None:
            th = _finite_float("threshold", threshold)
            if not 0.5 < th < 1.0:
                raise ValueError("threshold must be strictly between 0.5 and 1")
        else:
            th = None
        if horizon_bars is not None and int(horizon_bars) <= 0:
            raise ValueError("horizon_bars must be > 0")
        metadata = metadata or {}
        meta_json = _canonical_json(metadata)
        meta_sha = _sha256_json(metadata)
        prediction_id = uuid.uuid4().hex
        now = _utcnow()

        with sqlite3.connect(self.path) as con:
            con.execute("PRAGMA foreign_keys=ON")
            exists = con.execute(
                "SELECT 1 FROM shadow_candidates WHERE candidate_id=?",
                (candidate_id,),
            ).fetchone()
            if exists is None:
                raise KeyError(f"Unknown shadow candidate: {candidate_id}")
            if st is not None and not allow_out_of_order:
                row = con.execute(
                    "SELECT MAX(source_time) FROM shadow_predictions_v2 WHERE candidate_id=? AND source_time IS NOT NULL",
                    (candidate_id,),
                ).fetchone()
                latest = row[0] if row else None
                if latest is not None and st < float(latest):
                    raise ValueError(
                        f"source_time moved backwards for {candidate_id}: {st} < {float(latest)}; "
                        "set allow_out_of_order=True only for an explicitly audited import"
                    )
            con.execute(
                "INSERT INTO shadow_predictions_v2(" 
                "prediction_id, candidate_id, recorded_at, source_time, source_key, probability, threshold, horizon_bars, "
                "metadata_json, metadata_sha256) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (prediction_id, candidate_id, now, st, source_key, p, th, horizon_bars, meta_json, meta_sha),
            )
        return prediction_id

    def settle_prediction(
        self,
        prediction_id: str,
        realized_return: float,
        *,
        target_source_time: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Append an immutable realized outcome for one prior prediction.

        Exact retry of an already-recorded outcome is idempotent. A conflicting second
        outcome raises instead of rewriting history.
        """
        rr = _finite_float("realized_return", realized_return)
        target = None if target_source_time is None else _finite_float("target_source_time", target_source_time)
        metadata = metadata or {}
        meta_json = _canonical_json(metadata)
        meta_sha = _sha256_json(metadata)

        with sqlite3.connect(self.path) as con:
            con.execute("PRAGMA foreign_keys=ON")
            pred = con.execute(
                "SELECT source_time FROM shadow_predictions_v2 WHERE prediction_id=?",
                (prediction_id,),
            ).fetchone()
            if pred is None:
                raise KeyError(f"Unknown shadow prediction: {prediction_id}")
            source_time = pred[0]
            if target is not None and source_time is not None and target < float(source_time):
                raise ValueError("target_source_time cannot precede the prediction source_time")
            existing = con.execute(
                "SELECT realized_return, target_source_time, metadata_sha256 FROM shadow_outcomes_v2 WHERE prediction_id=?",
                (prediction_id,),
            ).fetchone()
            if existing is not None:
                same_return = math.isclose(float(existing[0]), rr, rel_tol=0.0, abs_tol=1e-15)
                same_target = (
                    (existing[1] is None and target is None)
                    or (existing[1] is not None and target is not None and math.isclose(float(existing[1]), target, rel_tol=0.0, abs_tol=1e-12))
                )
                if same_return and same_target and str(existing[2]) == meta_sha:
                    return
                raise ValueError("shadow outcomes are immutable; conflicting settlement rejected")
            con.execute(
                "INSERT INTO shadow_outcomes_v2(" 
                "prediction_id, matured_at, realized_return, target_source_time, metadata_json, metadata_sha256) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (prediction_id, _utcnow(), rr, target, meta_json, meta_sha),
            )

    def mature(
        self,
        candidate_id: str,
        observed_at_or_prediction_id: str,
        source_time: float | None,
        realized_return: float,
    ) -> None:
        """Backward-compatible maturity API.

        New code should call settle_prediction(prediction_id, ...). If the second
        argument is a v2 prediction ID it is settled immutably. Otherwise a legacy row
        is updated for compatibility with pre-v2 databases/tests.
        """
        with sqlite3.connect(self.path) as con:
            row = con.execute(
                "SELECT candidate_id FROM shadow_predictions_v2 WHERE prediction_id=?",
                (observed_at_or_prediction_id,),
            ).fetchone()
        if row is not None:
            if str(row[0]) != candidate_id:
                raise ValueError("prediction_id does not belong to candidate_id")
            self.settle_prediction(observed_at_or_prediction_id, realized_return)
            return
        with sqlite3.connect(self.path) as con:
            cur = con.execute(
                "UPDATE shadow_observations SET realized_return=?, mature=1 "
                "WHERE candidate_id=? AND observed_at=? AND source_time IS ? AND mature=0",
                (float(realized_return), candidate_id, observed_at_or_prediction_id, source_time),
            )
            if cur.rowcount != 1:
                raise KeyError("Unknown or already-mature legacy shadow observation")

    def _mature_rows(self, candidate_id: str) -> list[dict[str, Any]]:
        with sqlite3.connect(self.path) as con:
            v2 = con.execute(
                "SELECT p.prediction_id, p.recorded_at, p.source_time, p.probability, p.threshold, p.horizon_bars, "
                "p.metadata_json, o.matured_at, o.realized_return, o.target_source_time "
                "FROM shadow_predictions_v2 p JOIN shadow_outcomes_v2 o ON o.prediction_id=p.prediction_id "
                "WHERE p.candidate_id=? ORDER BY p.recorded_at, p.rowid",
                (candidate_id,),
            ).fetchall()
            legacy = con.execute(
                "SELECT observed_at, source_time, probability, realized_return, metadata_json "
                "FROM shadow_observations WHERE candidate_id=? AND mature=1 ORDER BY observed_at",
                (candidate_id,),
            ).fetchall()
        rows = [
            {
                "prediction_id": r[0],
                "recorded_at": r[1],
                "source_time": r[2],
                "probability": float(r[3]),
                "threshold": r[4],
                "horizon_bars": r[5],
                "prediction_metadata": json.loads(r[6]),
                "matured_at": r[7],
                "realized_return": float(r[8]),
                "target_source_time": r[9],
                "schema": "v2",
            }
            for r in v2
        ]
        rows.extend(
            {
                "prediction_id": f"legacy:{i}:{r[0]}",
                "recorded_at": r[0],
                "source_time": r[1],
                "probability": float(r[2]),
                "threshold": None,
                "horizon_bars": None,
                "prediction_metadata": json.loads(r[4]),
                "matured_at": None,
                "realized_return": float(r[3]),
                "target_source_time": None,
                "schema": "legacy",
            }
            for i, r in enumerate(legacy)
        )
        rows.sort(key=lambda x: (str(x["recorded_at"]), str(x["prediction_id"])))
        return rows

    @staticmethod
    def _metrics_for_rows(
        rows: list[dict[str, Any]],
        *,
        threshold: float,
        round_trip_cost_bps: float,
        calibration_bins: int,
    ) -> dict[str, Any]:
        if not rows:
            return {"mature_observations": 0}
        p = np.asarray([float(r["probability"]) for r in rows], dtype=float)
        ret = np.asarray([float(r["realized_return"]) for r in rows], dtype=float)
        finite = np.isfinite(p) & np.isfinite(ret)
        p, ret = np.clip(p[finite], 1e-9, 1 - 1e-9), ret[finite]
        if not len(p):
            return {"mature_observations": 0}
        y = (ret > 0).astype(int)
        prevalence = float(np.mean(y))
        baseline = float(np.clip(prevalence, 1e-9, 1 - 1e-9))
        auc = _safe_auc(y, p)
        brier = float(brier_score_loss(y, p))
        brier_base = float(np.mean((y - baseline) ** 2))
        ll = float(log_loss(y, p, labels=[0, 1]))
        ll_base = float(log_loss(y, np.full(len(y), baseline), labels=[0, 1]))
        calibration, ece, mce = _calibration_bins(y, p, calibration_bins)

        sides = np.where(p >= threshold, 1.0, np.where(p <= 1.0 - threshold, -1.0, 0.0))
        active = sides != 0
        active_pnl = sides[active] * ret[active] - float(round_trip_cost_bps) / 10_000.0
        max_dd, cumulative = _max_drawdown_from_log_pnl(active_pnl)
        signal_count = int(active.sum())
        signal_hit_rate = float(np.mean(active_pnl > 0.0)) if signal_count else 0.0
        if signal_count:
            successes = int(np.sum(active_pnl > 0.0))
            alpha = 0.5 + successes
            beta = 0.5 + signal_count - successes
            lower = float(beta_dist.ppf(0.025, alpha, beta))
            upper = float(beta_dist.ppf(0.975, alpha, beta))
        else:
            lower, upper = 0.0, 1.0

        return {
            "mature_observations": int(len(p)),
            "positive_prevalence": prevalence,
            "auc": auc,
            "brier": brier,
            "brier_baseline": brier_base,
            "brier_improvement": brier_base - brier,
            "log_loss": ll,
            "log_loss_baseline": ll_base,
            "log_loss_improvement": ll_base - ll,
            "expected_calibration_error": ece,
            "max_calibration_error": mce,
            "calibration_bins": calibration,
            "mean_confidence": float(np.mean(np.abs(p - 0.5) * 2.0)),
            "signal_threshold": float(threshold),
            "signal_count": signal_count,
            "signal_hit_rate": signal_hit_rate,
            "directional_hit_posterior_95_lower": lower,
            "directional_hit_posterior_95_upper": upper,
            "cumulative_log_return_repriced": cumulative,
            "max_drawdown_repriced": max_dd,
            "mean_realized_return": float(np.mean(ret)),
            "median_realized_return": float(np.median(ret)),
        }

    def summary(
        self,
        candidate_id: str,
        *,
        threshold: float = 0.55,
        round_trip_cost_bps: float = 0.0,
        recent_window: int | None = None,
        calibration_bins: int = 10,
    ) -> dict[str, Any]:
        """Summarize genuinely forward observations recorded before outcomes matured."""
        cand = self.candidate(candidate_id)
        rows = self._mature_rows(candidate_id)
        metrics = self._metrics_for_rows(
            rows,
            threshold=threshold,
            round_trip_cost_bps=round_trip_cost_bps,
            calibration_bins=calibration_bins,
        )
        metrics["candidate_id"] = candidate_id
        metrics["candidate_status"] = cand["status"]
        metrics["immutable_manifest_sha256"] = cand["manifest_sha256"]
        metrics["reference_metrics"] = _extract_reference_metrics(cand["manifest"])
        if recent_window is not None and recent_window > 0 and rows:
            recent = rows[-int(recent_window):]
            metrics["recent"] = self._metrics_for_rows(
                recent,
                threshold=threshold,
                round_trip_cost_bps=round_trip_cost_bps,
                calibration_bins=calibration_bins,
            )
        return metrics

    def health(
        self,
        candidate_id: str,
        cfg: ShadowConfig | None = None,
        *,
        threshold: float = 0.55,
        round_trip_cost_bps: float = 0.0,
    ) -> ShadowHealth:
        """Return a research-only lifecycle recommendation from immutable forward evidence."""
        cfg = cfg or ShadowConfig()
        cand = self.candidate(candidate_id)
        rows = self._mature_rows(candidate_id)
        current = self._metrics_for_rows(
            rows,
            threshold=threshold,
            round_trip_cost_bps=round_trip_cost_bps,
            calibration_bins=cfg.calibration_bins,
        )
        recent_rows = rows[-cfg.recent_window:]
        recent = self._metrics_for_rows(
            recent_rows,
            threshold=threshold,
            round_trip_cost_bps=round_trip_cost_bps,
            calibration_bins=cfg.calibration_bins,
        )
        reference = _extract_reference_metrics(cand["manifest"])
        n = int(current.get("mature_observations", 0))
        failures: list[str] = []
        warnings: list[str] = []

        if cand["status"] == "SHADOW_RETIRED":
            return ShadowHealth(candidate_id, "SHADOW_RETIRED", n, tuple(), tuple(), reference, current, recent)
        if n < cfg.min_mature_observations:
            return ShadowHealth(
                candidate_id,
                "SHADOW_WARMING",
                n,
                tuple(),
                (f"need_{cfg.min_mature_observations - n}_more_mature_observations",),
                reference,
                current,
                recent,
            )

        ref_auc = reference.get("auc")
        if ref_auc is not None and current.get("auc", 0.5) < ref_auc - cfg.max_auc_drop_vs_reference:
            failures.append("auc_degraded_vs_protected_reference")
        ref_brier = reference.get("brier")
        if ref_brier is not None and current.get("brier", 1.0) > ref_brier + cfg.max_brier_degradation_vs_reference:
            failures.append("brier_degraded_vs_protected_reference")
        if current.get("expected_calibration_error", 1.0) > cfg.max_expected_calibration_error:
            failures.append("calibration_error_excessive")
        if current.get("max_drawdown_repriced", 1.0) > cfg.max_drawdown:
            failures.append("forward_drawdown_excessive")
        if int(current.get("signal_count", 0)) >= cfg.min_signal_count:
            if current.get("directional_hit_posterior_95_lower", 0.0) < cfg.min_directional_posterior_lower:
                warnings.append("directional_hit_posterior_weak")
        else:
            warnings.append("insufficient_forward_signals")

        if len(recent_rows) >= max(20, min(cfg.recent_window, cfg.min_mature_observations)):
            if recent.get("auc", 0.5) < current.get("auc", 0.5) - cfg.max_recent_auc_drop:
                failures.append("recent_auc_breakdown")
            if recent.get("brier", 1.0) > current.get("brier", 1.0) + cfg.max_recent_brier_degradation:
                failures.append("recent_brier_breakdown")

        if len(rows) >= 40:
            cut = max(20, len(rows) // 2)
            early = np.asarray([float(r["probability"]) for r in rows[:cut]], dtype=float)
            late = np.asarray([float(r["probability"]) for r in rows[-cut:]], dtype=float)
            if len(early) >= 20 and len(late) >= 20:
                ks = float(ks_2samp(early, late, method="auto").statistic)
                current["probability_ks_drift"] = ks
                if ks > cfg.max_probability_ks_drift:
                    warnings.append("prediction_distribution_drift")

        failure_count = len(set(failures))
        if failure_count >= cfg.degraded_failures:
            status = "SHADOW_DEGRADED"
        elif failure_count >= cfg.watch_failures or warnings:
            status = "SHADOW_WATCH"
        else:
            status = "SHADOW_HEALTHY"
        return ShadowHealth(
            candidate_id,
            status,
            n,
            tuple(sorted(set(failures))),
            tuple(sorted(set(warnings))),
            reference,
            current,
            recent,
        )

    def apply_health_status(
        self,
        candidate_id: str,
        cfg: ShadowConfig | None = None,
        *,
        threshold: float = 0.55,
        round_trip_cost_bps: float = 0.0,
    ) -> ShadowHealth:
        """Persist the research-only health recommendation as an auditable status event."""
        health = self.health(
            candidate_id,
            cfg,
            threshold=threshold,
            round_trip_cost_bps=round_trip_cost_bps,
        )
        current = self.candidate(candidate_id)["status"]
        if current != health.recommended_status:
            self.set_status(
                candidate_id,
                health.recommended_status,
                "forward_evidence_health_assessment",
                health.to_dict(),
            )
        return health

    def pending_count(self, candidate_id: str) -> int:
        with sqlite3.connect(self.path) as con:
            row = con.execute(
                "SELECT COUNT(*) FROM shadow_predictions_v2 p "
                "LEFT JOIN shadow_outcomes_v2 o ON o.prediction_id=p.prediction_id "
                "WHERE p.candidate_id=? AND o.prediction_id IS NULL",
                (candidate_id,),
            ).fetchone()
        return int(row[0]) if row else 0

    def list_candidates(self) -> list[dict[str, Any]]:
        with sqlite3.connect(self.path) as con:
            rows = con.execute(
                "SELECT candidate_id, created_at, status, manifest_sha256 FROM shadow_candidates ORDER BY created_at DESC"
            ).fetchall()
        return [
            {
                "candidate_id": r[0],
                "created_at": r[1],
                "status": r[2],
                "manifest_sha256": r[3],
                "pending_predictions": self.pending_count(r[0]),
            }
            for r in rows
        ]
