from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .catalog import build_catalog
from .config import DaedalusConfig
from .pipeline import research_file


def run_batch(data_root: Path, project_root: Path, cfg: DaedalusConfig | None = None, limit: int | None = None, resume: bool = True) -> dict:
    """Run resumable development-only screening over exact SHA-256 representatives.

    Catalog records remain intact. Compute de-duplication only avoids rerunning byte-identical
    exports. This function never spends protected holdouts; use research_corpus() for the
    budgeted protected-tail phase.
    """
    cfg = cfg or DaedalusConfig()
    catalog = build_catalog(data_root)
    if catalog.empty:
        return {"catalog_files": 0, "unique_compute_sources": 0, "processed": 0, "skipped_existing": 0, "errors": []}
    reps = catalog.sort_values(["sha256", "path"]).drop_duplicates("sha256", keep="first")
    reps = reps[reps["rows"] >= cfg.data.min_rows]
    if limit is not None:
        reps = reps.head(limit)
    run_dir = project_root / cfg.runtime.output_dir
    processed = skipped = 0
    errors: list[dict] = []
    for row in reps.itertuples(index=False):
        report_path = run_dir / f"{row.sha256[:16]}.json"
        if resume and report_path.exists():
            skipped += 1
            continue
        try:
            # Batch mode is deliberately development-only. Corpus-wide protected-tail
            # exposure is reserved for research_corpus(), which applies a global budget.
            report = research_file(Path(row.path), project_root, cfg, data_root=data_root, allow_holdout=False)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8")
            processed += 1
        except Exception as exc:
            errors.append({"path": row.path, "error": f"{type(exc).__name__}: {exc}"})
    summary = {
        "catalog_files": int(len(catalog)),
        "unique_compute_sources": int(len(reps)),
        "processed": processed,
        "skipped_existing": skipped,
        "errors": errors,
    }
    out = project_root / "artifacts" / "batch_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
