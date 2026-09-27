from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .bridge import export_candidate
from .catalog import build_catalog
from .config import DaedalusConfig
from .holdout_budget import development_rank_key, select_holdout_exposures
from .hypotheses import benjamini_hochberg
from .pipeline import research_file
from .registry import ExperimentRegistry
from .shadow import ShadowBook


def research_corpus(
    data_root: Path,
    project_root: Path,
    cfg: DaedalusConfig | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Research a corpus with a development-first, budgeted holdout protocol.

    Phase 1 runs every unique-byte source through development-only research. Exact
    duplicate exports stay in the catalog but consume compute only once. Phase 2
    spends protected holdouts only on the strongest/diverse development survivors.
    Global FDR is then applied only to the valid protected-tail tests actually run.
    """
    cfg = cfg or DaedalusConfig()
    data_root = data_root.resolve()
    project_root = project_root.resolve()
    catalog = build_catalog(data_root)
    if catalog.empty:
        return {"status": "empty", "data_root": str(data_root)}

    artifacts = project_root / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    catalog.to_csv(artifacts / "catalog.csv", index=False)

    # Preserve every catalog row, but avoid duplicate compute for byte-identical exports.
    unique = catalog.sort_values(["sha256", "path"]).drop_duplicates("sha256", keep="first")
    unique = unique[unique["rows"] >= cfg.data.min_rows]
    if limit is not None:
        unique = unique.head(limit)

    source_rows = list(unique.to_dict(orient="records"))
    development_reports: list[dict[str, Any]] = []
    for row in source_rows:
        try:
            report = research_file(
                Path(row["path"]),
                project_root,
                cfg,
                data_root=data_root,
                allow_holdout=False,
            )
        except Exception as exc:
            report = {
                "status": "error",
                "source_path": str(row["path"]),
                "error": f"{type(exc).__name__}: {exc}",
                "protected_holdout_touched": False,
            }
        development_reports.append(report)

    selection = select_holdout_exposures(development_reports, cfg.holdout_budget)
    selected_set = set(selection.selected_indices)

    # Final report list retains every screened source. Qualified but unselected sources
    # explicitly record that their protected tails remain pristine.
    reports: list[dict[str, Any]] = []
    tests: list[tuple[int, float]] = []
    selection_rank = {
        idx: rank + 1
        for rank, idx in enumerate(
            sorted(selection.selected_indices, key=lambda i: development_rank_key(development_reports[i]), reverse=True)
        )
    }

    for idx, (row, dev_report) in enumerate(zip(source_rows, development_reports)):
        if idx not in selected_set:
            if dev_report.get("status") == "development_qualified":
                dev_report = dict(dev_report)
                dev_report.update({
                    "status": "development_budget_rejected",
                    "reason": "qualified_but_not_selected_for_protected_holdout_budget",
                    "protected_holdout_touched": False,
                    "corpus_holdout_budget": selection.budget,
                })
            reports.append(dev_report)
            continue

        try:
            final_report = research_file(
                Path(row["path"]),
                project_root,
                cfg,
                data_root=data_root,
                allow_holdout=True,
            )
        except Exception as exc:
            final_report = {
                "status": "error",
                "source_path": str(row["path"]),
                "error": f"{type(exc).__name__}: {exc}",
            }
        final_report = dict(final_report)
        final_report["corpus_holdout_selection_rank"] = selection_rank.get(idx)
        final_report["corpus_holdout_budget"] = selection.budget
        report_index = len(reports)
        reports.append(final_report)

        final = final_report.get("final_candidate") if final_report.get("status") == "ok" else None
        if final:
            p = float(final.get("permutation", {}).get("pvalue", 1.0))
            tests.append((report_index, p))

    # Development-only selection is independent of protected-tail outcomes. Therefore
    # corpus-level q-values are computed only after all selected tails have been tested.
    qvalues = benjamini_hochberg([t[1] for t in tests])
    globally_eligible: list[dict[str, Any]] = []
    registry = ExperimentRegistry(project_root / cfg.runtime.registry_path)

    for (report_i, _), q in zip(tests, qvalues):
        report = reports[report_i]
        result = report["final_candidate"]
        result["corpus_qvalue"] = float(q)
        result["globally_statistically_eligible"] = q <= cfg.promotion.max_global_qvalue
        local = bool(result.get("local_promotion_gate", {}).get("promoted", False))
        eligible = local and result["globally_statistically_eligible"]
        result["globally_eligible"] = eligible
        registry.update_result(result["experiment_id"], result)
        if not eligible:
            continue

        source = report["profile"]
        identity = report["identity"]
        candidate = {
            "experiment_id": result["experiment_id"],
            "source_sha256": source["sha256"],
            "source_path": source["path"],
            "source_mechanics_signature": source["mechanics_signature"],
            "source_mechanics_class": source["mechanics_class"],
            "identity": identity,
            "model": result["model"],
            "corpus_qvalue": float(q),
            "protected_holdout": result["protected_holdout"],
            "robustness": result["robustness"],
            "local_promotion_gate": result["local_promotion_gate"],
            "production_authorized": False,
        }
        candidate_path = project_root / cfg.runtime.candidate_dir / f"{result['experiment_id']}.json"
        export_candidate(candidate_path, candidate)
        ShadowBook(project_root / cfg.runtime.shadow_path).register(result["experiment_id"], candidate)
        globally_eligible.append(candidate)
        registry.set_promoted(result["experiment_id"], True)

    holdout_touched = sum(bool(r.get("final_candidate", {}).get("protected_holdout_touched", False)) for r in reports)
    summary = {
        "status": "ok",
        "cataloged_real_csv_files": int(len(catalog)),
        "unique_exact_sha256": int(catalog["sha256"].nunique()),
        "development_sources_screened": len(development_reports),
        "development_qualified": selection.qualified,
        "holdout_budget": selection.budget,
        "holdout_selected": len(selection.selected_indices),
        "protected_holdouts_exposed": int(holdout_touched),
        "selected_source_hypotheses": len(tests),
        "globally_eligible_candidates": len(globally_eligible),
        "global_qvalue_threshold": cfg.promotion.max_global_qvalue,
        "holdout_selection": selection.to_dict(),
        "reports": reports,
    }
    (artifacts / "corpus_research_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    return summary
