"""End-to-end tour: one NEXUS market instant followed through every connected system.

Runs every connection driver (each in its own isolated interpreter), checks that they all
carried the same deterministic NEXUS instant (identical bundle hash), and narrates the flow:
NEXUS -> AION/ARGUS/ATHENA/DAEDALUS -> ORACLE -> PROMETHEUS -> ASCENSION -> SuperMesh-X.
It then reports the standalone systems and the live engine. Output is ASCII (Windows consoles
are cp1252). Research/verification only: nothing here trades, promotes or grants authority.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from . import connections, engine, registry

FLOW = ["nexus-siblings", "intelligence-fabric", "nexus-oracle", "nexus-contract-drift", "nexus-prometheus",
        "prometheus-ascension", "supermesh-witness"]
AUXILIARY = ["argus-athena-research"]


def _short(h: str | None) -> str:
    return (h or "?")[:12]


def run(include_engine: bool = True) -> dict:
    instant_results = {name: connections.check(name) for name in FLOW}
    auxiliary_results = {name: connections.check(name) for name in AUXILIARY}
    results = {**instant_results, **auxiliary_results}
    # Only the FLOW connections are required to carry the same NEXUS instant.
    # Auxiliary research bridges have their own prospective study identities.
    hashes = {n: r.get("bundle_hash") or r.get("nexus_bundle_hash") for n, r in instant_results.items()}
    carried = {h for h in hashes.values() if h}
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "connections": results,
        "same_instant_everywhere": len(carried) == 1,
        "instant_bundle_hash": next(iter(carried)) if len(carried) == 1 else sorted(carried),
        "coverage": connections.coverage(),
        "engine": ({"health": engine.health(), "assets": engine.assets()} if include_engine else None),
    }
    report["ok"] = all(r.get("ok") for r in results.values()) and report["same_instant_everywhere"]
    return report


def narrate(t: dict) -> str:
    c = t["connections"]
    sib, fabric, ora, drift, pro, asc, sm = (c[n] for n in FLOW)
    research = c["argus-athena-research"]
    mark = lambda r: "OK " if r.get("ok") else "FAIL"  # noqa: E731
    lines = ["ICARUS / Divine Providence - end-to-end tour  (" + t["generated_at"] + ")", ""]
    lines.append(f"[{mark(sib)}] 1. NEXUS packages one causally atomic market instant "
                 f"(bundle {_short(t['instant_bundle_hash'] if t['same_instant_everywhere'] else None)})")
    for s in ("aion", "argus", "athena", "daedalus"):
        lines.append(f"        -> {s.upper():8s} {sib.get('result', {}).get('details', {}).get(s, sib.get('error', ''))}")
    lines.append(f"[{mark(fabric)}] 2. Causal intelligence fabric persists AION evidence, builds PARALLAX fingerprint "
                 f"({fabric.get('parallax', {}).get('axes', '?')} axes), preserves ARGUS proxy tier, and gates ATHENA by receipt time")
    lines.append(f"[{mark(research)}] 3. ARGUS publishes a prospectively locked order-block survival study "
                 f"(schema={research.get('study_schema_version', '?')}, alpha={research.get('confidence_alpha', '?')}) "
                 f"to ATHENA only after follow-up completion and local receipt")
    feats = ora.get("financial_state_features", {})
    lines.append(f"[{mark(ora)}] 4. ORACLE turns the {ora.get('packet_contract', '?')} packet into financial state: "
                 + ", ".join(f"{k}={v}" for k, v in sorted(feats.items())))
    lines.append(f"[{mark(drift)}] 5. Sibling contracts vs the baseline PROMETHEUS pins ({_short(drift.get('baseline_snapshot_hash'))}): "
                 + ("no semantic drift" if not drift.get("semantic_drift") else "DRIFT: " + json.dumps(drift.get("items"))))
    obs = ", ".join(f"{o['sibling']}:{o['evidence_tier']}" for o in pro.get("observations", []))
    lines.append(f"[{mark(pro)}] 6. PROMETHEUS binds the same instant ({pro.get('link_state', '?')}) -> {obs or pro.get('refusal')}")
    lines.append(f"[{mark(asc)}] 7. PROMETHEUS emits exact runtime provenance bytes into ASCENSION: "
                 f"status={asc.get('ascension_status', '?')}, "
                 f"ready_for_adapter={asc.get('ready_for_adapter_v0_4')}, "
                 f"authenticated={asc.get('authenticated')}, "
                 f"transfer={str(asc.get('transfer', '?')).split(':')[0]}")
    neg = sm.get("negative_controls", {})
    lines.append(f"[{mark(sm)}] 8. SuperMesh-X witnesses the instant: log {sm.get('log_id', '?')}, size {sm.get('tree_size', '?')}, "
                 f"root {_short(sm.get('root'))}, quorum {sm.get('witness_quorum', '?')}/2; rewrite rejected="
                 f"{bool(neg.get('history_rewrite_rejected'))}, rollback rejected={bool(neg.get('rollback_rejected'))}")
    lines.append("")
    lines.append("Same instant at every hop: " + ("YES" if t["same_instant_everywhere"] else "NO " + str(t["instant_bundle_hash"])))
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
    lines.append("RESULT: " + ("ALL CONNECTED SYSTEMS RAN TOGETHER" if t["ok"] else "SOMETHING FAILED - see details above"))
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
