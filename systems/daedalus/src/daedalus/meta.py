from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class ModelFamilyMemory:
    model_name: str
    experiments: int
    promoted: int
    smoothed_promotion_rate: float
    mean_validation_auc: float
    mean_holdout_auc: float
    mean_robustness: float
    shrinkage_auc: float

    def to_dict(self) -> dict:
        return asdict(self)


def _extract(result: dict) -> tuple[float | None, float | None, float | None]:
    # Development record.
    validation = result.get("validation") or result.get("development_validation") or {}
    val_auc = (validation.get("aggregate") or {}).get("auc") if isinstance(validation, dict) else None

    # Champion final record.
    hold = result.get("protected_holdout") or result.get("holdout") or {}
    hold_auc = (hold.get("metrics") or {}).get("auc") if isinstance(hold, dict) else None
    robust = result.get("robustness") or {}
    robust_score = robust.get("robustness_score") if isinstance(robust, dict) else None
    return (
        float(val_auc) if val_auc is not None else None,
        float(hold_auc) if hold_auc is not None else None,
        float(robust_score) if robust_score is not None else None,
    )


def summarize_model_memory(registry_path: Path, prior_strength: float = 10.0) -> list[ModelFamilyMemory]:
    if not registry_path.exists():
        return []
    with sqlite3.connect(registry_path) as con:
        rows = con.execute("SELECT model_name, result_json, promoted FROM experiments").fetchall()
    grouped: dict[str, list[tuple[dict, int]]] = {}
    for name, payload, promoted in rows:
        try:
            result = json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            continue
        grouped.setdefault(name, []).append((result, int(promoted)))

    out: list[ModelFamilyMemory] = []
    for name, items in grouped.items():
        n = len(items)
        k = sum(p for _, p in items)
        val_aucs: list[float] = []
        hold_aucs: list[float] = []
        robustness: list[float] = []
        for result, _ in items:
            v, h, r = _extract(result)
            if v is not None:
                val_aucs.append(v)
            if h is not None:
                hold_aucs.append(h)
            if r is not None:
                robustness.append(r)
        mean_val = float(np.mean(val_aucs)) if val_aucs else 0.5
        shrink = (mean_val * n + 0.5 * prior_strength) / (n + prior_strength)
        out.append(ModelFamilyMemory(
            model_name=name,
            experiments=n,
            promoted=k,
            smoothed_promotion_rate=float((k + 1) / (n + 2)),
            mean_validation_auc=mean_val,
            mean_holdout_auc=float(np.mean(hold_aucs)) if hold_aucs else 0.5,
            mean_robustness=float(np.mean(robustness)) if robustness else 0.0,
            shrinkage_auc=float(shrink),
        ))
    return sorted(
        out,
        key=lambda x: (x.smoothed_promotion_rate, x.mean_robustness, x.shrinkage_auc, x.experiments),
        reverse=True,
    )


def summarize_experiment_memory(registry_path: Path) -> list[ModelFamilyMemory]:
    return summarize_model_memory(registry_path)
