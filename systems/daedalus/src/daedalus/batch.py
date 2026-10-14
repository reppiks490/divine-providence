from __future__ import annotations

import json
import importlib.metadata
import sys
from pathlib import Path

import pandas as pd

from .catalog import build_catalog
from .config import DaedalusConfig
from .pipeline import research_file
from .utils import sha256_file, stable_hash


def _context(cfg, project_root):
    source_root = Path(__file__).parent
    manifest = project_root / cfg.runtime.identity_manifest
    return stable_hash({"schema": "daedalus.batch.context.v1", "config": cfg.to_dict(),
        "code": {p.name: sha256_file(p) for p in sorted(source_root.glob("*.py"))},
        "identity_manifest": sha256_file(manifest) if manifest.is_file() else None,
        "python": list(sys.version_info[:2]),
        "dependencies": {n: importlib.metadata.version(n) for n in
                         ("numpy", "pandas", "scipy", "scikit-learn", "joblib")}})


def _cache_valid(path, source_hash, context_hash):
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 16_000_000:
            return False
        report = json.loads(path.read_text(encoding="utf-8"))
        metadata = report.pop("batch_cache", None)
        return (isinstance(metadata, dict) and metadata.get("schema") == "daedalus.batch.cache.v1"
                and metadata.get("source_sha256") == source_hash
                and metadata.get("context_hash") == context_hash
                and metadata.get("result_hash") == stable_hash(report)
                and report.get("protected_holdout_touched") is False)
    except (ValueError, OSError, TypeError, AttributeError):
        return False


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
    context_hash = _context(cfg, project_root)
    processed = skipped = stale = 0
    errors: list[dict] = []
    for row in reps.itertuples(index=False):
        was_stale = False
        report_path = run_dir / f"{row.sha256[:16]}.json"
        if resume and report_path.exists():
            if _cache_valid(report_path, row.sha256, context_hash):
                skipped += 1
                continue
            was_stale = True
        try:
            if report_path.is_symlink():
                raise ValueError("Batch cache output may not be a symbolic link")
            # Batch mode is deliberately development-only. Corpus-wide protected-tail
            # exposure is reserved for research_corpus(), which applies a global budget.
            report = research_file(Path(row.path), project_root, cfg, data_root=data_root, allow_holdout=False)
            if report.get("protected_holdout_touched") is not False:
                raise ValueError("Batch result lacks development-only authority")
            # Normalize serialization before hashing so the decoded cache has
            # exactly the same types as the sealed result.
            report = json.loads(json.dumps(report, default=str, allow_nan=False))
            report["batch_cache"] = {"schema": "daedalus.batch.cache.v1", "source_sha256": row.sha256,
                                     "context_hash": context_hash, "result_hash": stable_hash(report)}
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8")
            processed += 1
            stale += int(was_stale)
        except Exception as exc:
            errors.append({"path": row.path, "error": f"{type(exc).__name__}: {exc}"})
    summary = {
        "catalog_files": int(len(catalog)),
        "unique_compute_sources": int(len(reps)),
        "processed": processed,
        "skipped_existing": skipped,
        "refreshed_stale": stale,
        "context_hash": context_hash,
        "errors": errors,
    }
    out = project_root / "artifacts" / "batch_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
