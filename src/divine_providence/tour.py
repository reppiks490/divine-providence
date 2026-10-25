"""Tour of bundle-carrying connections and independent contract checks.

Each driver runs in its own isolated interpreter. The four bundle-carrying drivers
must return the same valid hash for the deterministic NEXUS fixture. Sibling
validation, contract drift, PROMETHEUS -> ASCENSION, and ARGUS research checks
use independent gates or fixtures; they do not prove continuity of that bundle.
Output is ASCII (Windows consoles are cp1252). Research/verification only:
nothing here trades, promotes or grants authority.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from . import connections, engine, registry

FLOW = ["nexus-siblings", "intelligence-fabric", "nexus-oracle", "nexus-contract-drift", "nexus-prometheus",
        "prometheus-ascension", "supermesh-witness"]
AUXILIARY = [
    "argus-athena-research",
    "argus-impact-athena-research",
    "argus-bootstrap-athena-research",
]
# These drivers actually build and consume the shared deterministic NEXUS bundle.
# A missing hash from any one of them must fail the continuity assertion.
BUNDLE_HASH_FIELDS = {
    "intelligence-fabric": "bundle_hash",
    "nexus-oracle": "bundle_hash",
    "nexus-prometheus": "bundle_hash",
    "supermesh-witness": "nexus_bundle_hash",
}


def _valid_hash(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _short(h: str | None) -> str:
    return (h or "?")[:12]


def run(include_engine: bool = True) -> dict:
    instant_results = {name: connections.check(name) for name in FLOW}
    auxiliary_results = {name: connections.check(name) for name in AUXILIARY}
    results = {**instant_results, **auxiliary_results}
    hashes = {name: results[name].get(field) for name, field in BUNDLE_HASH_FIELDS.items()}
    verified = {name: value for name, value in hashes.items()
                if results[name].get("ok") is True and _valid_hash(value)}
    same_instant = len(verified) == len(BUNDLE_HASH_FIELDS) and len(set(verified.values())) == 1
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "connections": results,
        # Keep the legacy key for CLI/MCP callers; "everywhere" is scoped to the
        # declared bundle-carrying checks, listed alongside the observed hashes.
        "same_instant_everywhere": same_instant,
        "instant_bundle_hash": next(iter(verified.values())) if same_instant else None,
        "bundle_checks": list(BUNDLE_HASH_FIELDS),
        "bundle_hashes": hashes,
        "independent_checks": [name for name in results if name not in BUNDLE_HASH_FIELDS],
        "coverage": connections.coverage(),
        "engine": ({"health": engine.health(), "assets": engine.assets()} if include_engine else None),
    }
    report["ok"] = all(r.get("ok") is True for r in results.values()) and same_instant
    return report


def narrate(t: dict) -> str:
    c = t["connections"]
    sib, fabric, ora, drift, pro, asc, sm = (c[n] for n in FLOW)
    research = c["argus-athena-research"]
    impact_research = c["argus-impact-athena-research"]
    bootstrap_research = c["argus-bootstrap-athena-research"]
    mark = lambda r: "OK " if r.get("ok") is True else "FAIL"  # noqa: E731
    lines = ["ICARUS / Divine Providence - contract tour  (" + t["generated_at"] + ")", ""]
    lines.append(f"[{mark(sib)}] 1. NEXUS validates sibling contracts using its own fixture")
    for s in ("aion", "argus", "athena", "daedalus"):
        lines.append(f"        -> {s.upper():8s} {sib.get('result', {}).get('details', {}).get(s, sib.get('error', ''))}")
    lines.append(f"[{mark(fabric)}] 2. NEXUS bundle {_short(fabric.get('bundle_hash'))}: causal intelligence fabric "
                 f"persists AION evidence, builds PARALLAX fingerprint "
                 f"({fabric.get('parallax', {}).get('axes', '?')} axes), preserves ARGUS proxy tier, and gates ATHENA by receipt time")
    lines.append(f"[{mark(research)}] 3. ARGUS publishes a prospectively locked order-block survival study "
                 f"(schema={research.get('study_schema_version', '?')}, alpha={research.get('confidence_alpha', '?')}) "
                 f"to ATHENA only after follow-up completion and local receipt")
    lines.append(f"[{mark(impact_research)}] 4. ARGUS publishes a prospectively locked impact-calibration study "
                 f"(schema={impact_research.get('study_schema_version', '?')}, "
                 f"paper={impact_research.get('argus', {}).get('paper_emulator_observations', '?')}, "
                 f"broker={impact_research.get('argus', {}).get('broker_confirmed_observations', '?')}) "
                 f"to ATHENA only after cohort lock and local receipt")
    lines.append(f"[{mark(bootstrap_research)}] 5. ARGUS publishes pre-registered deterministic bootstrap uncertainty "
                 f"(confidence={bootstrap_research.get('argus', {}).get('confidence_level', '?')}, "
                 f"reps={bootstrap_research.get('argus', {}).get('bootstrap_replicates', '?')}, "
                 f"paper={bootstrap_research.get('argus', {}).get('paper_emulator_observations', '?')}) "
                 f"to ATHENA as descriptive research only after local receipt")
    feats = ora.get("financial_state_features", {})
    lines.append(f"[{mark(ora)}] 6. ORACLE turns the {ora.get('packet_contract', '?')} packet into financial state: "
                 + ", ".join(f"{k}={v}" for k, v in sorted(feats.items())))
    lines.append(f"[{mark(drift)}] 7. Sibling contracts vs the baseline PROMETHEUS pins ({_short(drift.get('baseline_snapshot_hash'))}): "
                 + ("no semantic drift" if not drift.get("semantic_drift") else "DRIFT: " + json.dumps(drift.get("items"))))
    obs = ", ".join(f"{o['sibling']}:{o['evidence_tier']}" for o in pro.get("observations", []))
    lines.append(f"[{mark(pro)}] 8. PROMETHEUS binds a NEXUS bundle ({pro.get('link_state', '?')}) -> {obs or pro.get('refusal')}")
    lines.append(f"[{mark(asc)}] 9. Independent PROMETHEUS runtime fixture emits provenance bytes into ASCENSION: "
                 f"status={asc.get('ascension_status', '?')}, "
                 f"ready_for_adapter={asc.get('ready_for_adapter_v0_4')}, "
                 f"authenticated={asc.get('authenticated')}, "
                 f"transfer={str(asc.get('transfer', '?')).split(':')[0]}")
    neg = sm.get("negative_controls", {})
    lines.append(f"[{mark(sm)}] 10. SuperMesh-X witnesses a NEXUS bundle: log {sm.get('log_id', '?')}, size {sm.get('tree_size', '?')}, "
                 f"root {_short(sm.get('root'))}, quorum {sm.get('witness_quorum', '?')}/2; rewrite rejected="
                 f"{bool(neg.get('history_rewrite_rejected'))}, rollback rejected={bool(neg.get('rollback_rejected'))}")
    lines.append("")
    lines.append("Same NEXUS bundle across bundle-carrying checks: " + ("YES" if t["same_instant_everywhere"] else "NO"))
    if not t["same_instant_everywhere"]:
        lines.append("    " + ", ".join(
            f"{name}={_short(value) if _valid_hash(value) else 'MISSING/INVALID'}"
            for name, value in t["bundle_hashes"].items()))
    standalone = {n: v for n, v in t["coverage"].items() if v["status"] == "standalone"}
    lines.append("Standalone by design (no sibling contract in their code): " + ", ".join(sorted(standalone)))
    eng = t.get("engine")
    if eng is not None:
        h = eng["health"]
        if "error" in h:
            lines.append(f"Live ICARUS engine: offline ({h.get('error')}) - start it to include live data")
        else:
            lines.append(f"Live ICARUS engine: ok={h.get('ok')} warm={h.get('warm')} assets={','.join(h.get('assets', []))}")
    lines.append("")
    lines.append("RESULT: " + ("ALL DECLARED CHECKS PASSED" if t["ok"] else "CHECKS FAILED - see details above"))
    lines.append("(research/verification only - no trading, promotion or execution authority anywhere)")
    return "\n".join(lines)


def main() -> int:
    t = run()
    out = registry.repo_root() / "provenance" / "tour_report.json"
    out.write_text(json.dumps(t, indent=1, sort_keys=True, default=str), encoding="utf-8", newline="\n")
    print(narrate(t).encode("ascii", "replace").decode("ascii"))
    return 0 if t["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
