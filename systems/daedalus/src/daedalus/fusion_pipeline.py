from __future__ import annotations

from pathlib import Path
from typing import Mapping

from .catalog import profile_csv
from .config import DaedalusConfig
from .data import load_bars_with_quality
from .fusion import build_fused_dataset
from .pipeline import research_file


def research_fused_sources(
    execution_path: Path,
    representation_paths: Mapping[str, Path],
    project_root: Path,
    cfg: DaedalusConfig | None = None,
    *,
    data_root: Path | None = None,
) -> dict:
    """Research heterogeneous representations against one explicit execution stream.

    The execution file supplies the target/PnL path. Auxiliary chart constructions only
    supply backward-aligned predictors. Their exact file hashes and fusion diagnostics
    become part of the protected protocol hash, so changing any representation after a
    holdout exposure creates a ledger conflict instead of silently reusing the tail.
    """
    cfg = cfg or DaedalusConfig()
    execution_path = execution_path.resolve()
    project_root = project_root.resolve()
    data_root = (data_root or execution_path.parent).resolve()

    execution, execution_quality = load_bars_with_quality(
        execution_path,
        cfg.data.max_rows_per_file,
        require_nondecreasing_time=cfg.data.require_nondecreasing_time,
        reject_nonfinite_required_rows=cfg.data.reject_nonfinite_required_rows,
    )
    representations = {}
    rep_manifest = {}
    for name, path in sorted(representation_paths.items()):
        p = Path(path).resolve()
        frame, quality = load_bars_with_quality(
            p,
            cfg.data.max_rows_per_file,
            require_nondecreasing_time=cfg.data.require_nondecreasing_time,
            reject_nonfinite_required_rows=cfg.data.reject_nonfinite_required_rows,
        )
        representations[name] = frame
        profile = profile_csv(p)
        rep_manifest[name] = {
            "path": str(p),
            "sha256": profile.sha256,
            "mechanics_signature": profile.mechanics_signature,
            "mechanics_class": profile.mechanics_class,
            "quality": quality.to_dict(),
        }

    x, y, future_ret, fusion_diag = build_fused_dataset(
        execution,
        representations,
        cfg.features,
        include_execution_features=True,
    )
    execution_profile = profile_csv(execution_path)
    protocol_context = {
        "mode": "cross_representation_fusion_v1",
        "execution_sha256": execution_profile.sha256,
        "representations": {
            name: {
                "sha256": item["sha256"],
                "mechanics_signature": item["mechanics_signature"],
            }
            for name, item in rep_manifest.items()
        },
        "alignment": "strict_backward_no_exact_timestamp_matches",
        "target": "execution_open_to_horizon_close",
        "fusion_diagnostics": fusion_diag.to_dict(),
    }
    extra_report = {
        "research_mode": "cross_representation_fusion",
        "fusion": {
            "execution": {
                "path": str(execution_path),
                "sha256": execution_profile.sha256,
                "quality": execution_quality.to_dict(),
            },
            "representations": rep_manifest,
            "diagnostics": fusion_diag.to_dict(),
        },
    }
    return research_file(
        execution_path,
        project_root,
        cfg,
        data_root=data_root,
        prebuilt_dataset=(x, y, future_ret),
        protocol_context=protocol_context,
        extra_report=extra_report,
    )
