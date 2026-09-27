from __future__ import annotations

import argparse
import json
from pathlib import Path

from .batch import run_batch
from .bridge import summarize_nexus_handoff
from .nexus_diagnostics import write_nexus_diagnostics
from .future_evidence import write_nexus_confirmation_readiness
from .catalog import build_catalog
from .config import DaedalusConfig
from .corpus import research_corpus
from .cross_asset import aligned_lead_lag
from .data import load_bars_with_quality
from .identity import scaffold_identity_manifest
from .meta import summarize_experiment_memory
from .pipeline import research_file
from .fusion_pipeline import research_fused_sources
from .shadow import ShadowBook


def cmd_catalog(args) -> int:
    df = build_catalog(Path(args.data_root))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    summary = {
        "real_csv_files": int(len(df)),
        "unique_sha256": int(df["sha256"].nunique()) if len(df) else 0,
        "exact_duplicate_file_count": int((df["exact_duplicate_count"] > 1).sum()) if len(df) else 0,
        "unique_mechanics_signatures": int(df["mechanics_signature"].nunique()) if len(df) else 0,
        "mechanics_classes": df["mechanics_class"].value_counts().to_dict() if len(df) else {},
        "output": str(out),
    }
    print(json.dumps(summary, indent=2))
    return 0


def cmd_research(args) -> int:
    cfg = DaedalusConfig()
    root = Path(args.project_root).resolve()
    report = research_file(Path(args.csv).resolve(), root, cfg)
    final = report.get("final_candidate") or {}
    compact = {
        "status": report.get("status"),
        "reason": report.get("reason"),
        "feature_count": report.get("feature_count"),
        "feature_rows": report.get("feature_rows"),
        "selected_development_champion": report.get("selected_development_champion"),
        "protected_holdout_rows": report.get("protected_holdout_rows"),
        "holdout_auc": (final.get("protected_holdout") or {}).get("metrics", {}).get("auc"),
        "robustness": (final.get("robustness") or {}).get("robustness_score"),
        "local_gate": final.get("local_promotion_gate"),
        "global_fdr_required": report.get("global_fdr_required"),
    }
    print(json.dumps(compact, indent=2, default=str))
    return 0


def cmd_corpus(args) -> int:
    cfg = DaedalusConfig()
    summary = research_corpus(
        Path(args.data_root).resolve(),
        Path(args.project_root).resolve(),
        cfg,
        limit=args.limit,
    )
    print(json.dumps({
        "status": summary.get("status"),
        "cataloged_real_csv_files": summary.get("cataloged_real_csv_files"),
        "unique_exact_sha256": summary.get("unique_exact_sha256"),
        "development_sources_screened": summary.get("development_sources_screened"),
        "development_qualified": summary.get("development_qualified"),
        "holdout_budget": summary.get("holdout_budget"),
        "holdout_selected": summary.get("holdout_selected"),
        "protected_holdouts_exposed": summary.get("protected_holdouts_exposed"),
        "selected_source_hypotheses": summary.get("selected_source_hypotheses"),
        "globally_eligible_candidates": summary.get("globally_eligible_candidates"),
    }, indent=2))
    return 0


def cmd_cross_asset(args) -> int:
    a, _ = load_bars_with_quality(Path(args.csv_a).resolve())
    b, _ = load_bars_with_quality(Path(args.csv_b).resolve())
    results = aligned_lead_lag(a, b, max_lag=args.max_lag, alpha=args.alpha)
    print(json.dumps([r.to_dict() for r in results], indent=2))
    return 0


def cmd_meta(args) -> int:
    rows = summarize_experiment_memory(Path(args.registry))
    print(json.dumps([x.to_dict() for x in rows], indent=2))
    return 0


def cmd_shadow_summary(args) -> int:
    book = ShadowBook(Path(args.shadow_db))
    print(json.dumps(book.summary(
        args.candidate_id,
        threshold=args.threshold,
        round_trip_cost_bps=args.cost_bps,
        recent_window=args.recent_window,
    ), indent=2))
    return 0


def cmd_shadow_record(args) -> int:
    book = ShadowBook(Path(args.shadow_db))
    metadata = json.loads(args.metadata_json) if args.metadata_json else {}
    prediction_id = book.record_prediction(
        args.candidate_id,
        args.probability,
        args.source_time,
        metadata,
        source_key=args.source_key,
        threshold=args.threshold,
        horizon_bars=args.horizon_bars,
        allow_out_of_order=args.allow_out_of_order,
    )
    print(json.dumps({"status": "recorded", "prediction_id": prediction_id}, indent=2))
    return 0


def cmd_shadow_settle(args) -> int:
    book = ShadowBook(Path(args.shadow_db))
    metadata = json.loads(args.metadata_json) if args.metadata_json else {}
    book.settle_prediction(
        args.prediction_id,
        args.realized_return,
        target_source_time=args.target_source_time,
        metadata=metadata,
    )
    print(json.dumps({"status": "settled", "prediction_id": args.prediction_id}, indent=2))
    return 0


def cmd_shadow_health(args) -> int:
    cfg = DaedalusConfig()
    book = ShadowBook(Path(args.shadow_db))
    health = book.apply_health_status(
        args.candidate_id,
        cfg.shadow,
        threshold=args.threshold,
        round_trip_cost_bps=args.cost_bps,
    ) if args.apply else book.health(
        args.candidate_id,
        cfg.shadow,
        threshold=args.threshold,
        round_trip_cost_bps=args.cost_bps,
    )
    print(json.dumps(health.to_dict(), indent=2, default=str))
    return 0


def cmd_shadow_list(args) -> int:
    book = ShadowBook(Path(args.shadow_db))
    print(json.dumps(book.list_candidates(), indent=2, default=str))
    return 0



def cmd_batch(args) -> int:
    summary = run_batch(
        Path(args.data_root).resolve(),
        Path(args.project_root).resolve(),
        DaedalusConfig(),
        limit=args.limit,
        resume=not args.no_resume,
    )
    print(json.dumps(summary, indent=2, default=str))
    return 0


def cmd_identity_scaffold(args) -> int:
    out = scaffold_identity_manifest(Path(args.data_root).resolve(), Path(args.output).resolve())
    print(json.dumps({"status": "ok", "output": str(out)}, indent=2))
    return 0


def cmd_research_fusion(args) -> int:
    reps: dict[str, Path] = {}
    for item in args.representation:
        if "=" not in item:
            raise ValueError("--representation must be NAME=/path/to/source.csv")
        name, raw = item.split("=", 1)
        name = name.strip()
        if not name or name in reps:
            raise ValueError("representation names must be unique and non-empty")
        reps[name] = Path(raw).expanduser().resolve()
    report = research_fused_sources(
        Path(args.execution).expanduser().resolve(),
        reps,
        Path(args.project_root).resolve(),
        DaedalusConfig(),
        data_root=Path(args.data_root).resolve() if args.data_root else None,
    )
    final = report.get("final_candidate") or {}
    hold = final.get("protected_holdout") or {}
    print(json.dumps({
        "status": report.get("status"),
        "reason": report.get("reason"),
        "research_mode": report.get("research_mode"),
        "feature_rows": report.get("feature_rows"),
        "feature_count": report.get("feature_count"),
        "selected_development_champion": report.get("selected_development_champion"),
        "holdout_auc": (hold.get("metrics") or {}).get("auc"),
        "local_gate": final.get("local_promotion_gate"),
    }, indent=2, default=str))
    return 0


def cmd_nexus_handoff(args) -> int:
    summary = summarize_nexus_handoff(Path(args.handoff).expanduser().resolve())
    print(json.dumps(summary, indent=2, default=str))
    return 0


def cmd_nexus_diagnostics(args) -> int:
    out = write_nexus_diagnostics(
        Path(args.handoff).expanduser().resolve(),
        Path(args.corpus_root).expanduser().resolve(),
        Path(args.output).expanduser().resolve(),
        requested_blocks=args.blocks,
        min_rows_per_block=args.min_rows_per_block,
    )
    payload = json.loads(out.read_text(encoding="utf-8"))
    print(json.dumps({
        "status": "ok",
        "output": str(out),
        "diagnosed_candidate_count": payload["diagnosed_candidate_count"],
        "status_counts": payload["status_counts"],
        "protected_holdout_touched": False,
        "production_authorized": False,
    }, indent=2))
    return 0


def cmd_nexus_confirmation_readiness(args) -> int:
    out = write_nexus_confirmation_readiness(
        Path(args.handoff).expanduser().resolve(),
        Path(args.corpus_root).expanduser().resolve(),
        Path(args.output).expanduser().resolve(),
        min_new_rows=args.min_new_rows,
    )
    payload = json.loads(out.read_text(encoding="utf-8"))
    print(json.dumps({
        "status": "ok",
        "output": str(out),
        "candidate_count": payload["candidate_count"],
        "confirmation_ready_count": payload["confirmation_ready_count"],
        "status_counts": payload["status_counts"],
        "protected_outcomes_touched": False,
        "protected_holdout_spent": False,
        "production_authorized": False,
    }, indent=2))
    return 0

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="daedalus", description="DAEDALUS Research OS")
    sub = p.add_subparsers(dest="command", required=True)

    nr = sub.add_parser("nexus-confirmation-readiness", help="Check for append-only unseen evidence after NEXUS discovery")
    nr.add_argument("handoff")
    nr.add_argument("corpus_root")
    nr.add_argument("--output", default="artifacts/nexus_confirmation_readiness.json")
    nr.add_argument("--min-new-rows", type=int, default=250)
    nr.set_defaults(func=cmd_nexus_confirmation_readiness)

    nd = sub.add_parser("nexus-diagnostics", help="Run retrospective-only block diagnostics on NEXUS behavioral candidates")
    nd.add_argument("handoff")
    nd.add_argument("corpus_root")
    nd.add_argument("--output", default="artifacts/nexus_retrospective_diagnostics.json")
    nd.add_argument("--blocks", type=int, default=5)
    nd.add_argument("--min-rows-per-block", type=int, default=50)
    nd.set_defaults(func=cmd_nexus_diagnostics)

    nh = sub.add_parser("nexus-handoff", help="Validate a NEXUS candidate handoff without spending protected holdouts")
    nh.add_argument("handoff")
    nh.set_defaults(func=cmd_nexus_handoff)

    c = sub.add_parser("catalog", help="Recursively catalog CSV sources without collapsing chart variants")
    c.add_argument("data_root")
    c.add_argument("--output", default="artifacts/catalog.csv")
    c.set_defaults(func=cmd_catalog)

    r = sub.add_parser("research", help="Run protected-holdout research on one CSV")
    r.add_argument("csv")
    r.add_argument("--project-root", default=".")
    r.set_defaults(func=cmd_research)

    rf = sub.add_parser("research-fusion", help="Research alternate chart representations against one execution-safe price stream")
    rf.add_argument("execution", help="CSV used for execution target/PnL")
    rf.add_argument("--representation", action="append", default=[], help="NAME=/path/to/representation.csv; repeatable")
    rf.add_argument("--project-root", default=".")
    rf.add_argument("--data-root", default=None, help="Authoritative corpus root for identity mapping")
    rf.set_defaults(func=cmd_research_fusion)

    b = sub.add_parser("batch", help="Resumable development-only screening; never spends protected holdouts")
    b.add_argument("data_root")
    b.add_argument("--project-root", default=".")
    b.add_argument("--limit", type=int, default=None)
    b.add_argument("--no-resume", action="store_true")
    b.set_defaults(func=cmd_batch)

    ident = sub.add_parser("identity-scaffold", help="Create explicit chart-type/source identity manifest for review")
    ident.add_argument("data_root")
    ident.add_argument("--output", default="config/source_identity.csv")
    ident.set_defaults(func=cmd_identity_scaffold)

    rc = sub.add_parser("research-corpus", help="Two-phase corpus research: development screen, budgeted holdouts, global FDR")
    rc.add_argument("data_root")
    rc.add_argument("--project-root", default=".")
    rc.add_argument("--limit", type=int, default=None, help="Safety limit for staged runs")
    rc.set_defaults(func=cmd_corpus)

    x = sub.add_parser("cross-asset", help="Exact-timestamp lead/lag diagnostic between two sources")
    x.add_argument("csv_a")
    x.add_argument("csv_b")
    x.add_argument("--max-lag", type=int, default=10)
    x.add_argument("--alpha", type=float, default=0.05)
    x.set_defaults(func=cmd_cross_asset)

    m = sub.add_parser("meta", help="Summarize experiment-memory evidence by model family")
    m.add_argument("--registry", default="artifacts/experiments.sqlite3")
    m.set_defaults(func=cmd_meta)

    s = sub.add_parser("shadow-summary", help="Summarize immutable matured forward observations for a candidate")
    s.add_argument("candidate_id")
    s.add_argument("--shadow-db", default="artifacts/shadow.sqlite3")
    s.add_argument("--threshold", type=float, default=0.55)
    s.add_argument("--cost-bps", type=float, default=0.0)
    s.add_argument("--recent-window", type=int, default=100)
    s.set_defaults(func=cmd_shadow_summary)

    sr = sub.add_parser("shadow-record", help="Append one forward prediction before its outcome is known")
    sr.add_argument("candidate_id")
    sr.add_argument("probability", type=float)
    sr.add_argument("--source-time", type=float, default=None)
    sr.add_argument("--source-key", default=None)
    sr.add_argument("--threshold", type=float, default=None)
    sr.add_argument("--horizon-bars", type=int, default=None)
    sr.add_argument("--metadata-json", default=None)
    sr.add_argument("--allow-out-of-order", action="store_true")
    sr.add_argument("--shadow-db", default="artifacts/shadow.sqlite3")
    sr.set_defaults(func=cmd_shadow_record)

    ss = sub.add_parser("shadow-settle", help="Immutably settle one previously recorded prediction")
    ss.add_argument("prediction_id")
    ss.add_argument("realized_return", type=float)
    ss.add_argument("--target-source-time", type=float, default=None)
    ss.add_argument("--metadata-json", default=None)
    ss.add_argument("--shadow-db", default="artifacts/shadow.sqlite3")
    ss.set_defaults(func=cmd_shadow_settle)

    sh = sub.add_parser("shadow-health", help="Assess forward degradation without changing the model")
    sh.add_argument("candidate_id")
    sh.add_argument("--threshold", type=float, default=0.55)
    sh.add_argument("--cost-bps", type=float, default=0.0)
    sh.add_argument("--apply", action="store_true", help="Persist the research-only lifecycle status event")
    sh.add_argument("--shadow-db", default="artifacts/shadow.sqlite3")
    sh.set_defaults(func=cmd_shadow_health)

    sl = sub.add_parser("shadow-list", help="List registered shadow candidates and pending predictions")
    sl.add_argument("--shadow-db", default="artifacts/shadow.sqlite3")
    sl.set_defaults(func=cmd_shadow_list)
    return p


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
