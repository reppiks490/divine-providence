"""Cross-system connections, each verified by running a driver in isolation."""
from __future__ import annotations

from dataclasses import dataclass

from . import registry, runner


@dataclass(frozen=True)
class Connection:
    name: str
    driver: str
    systems: tuple[str, ...]
    contract: str
    description: str

    def pythonpath(self) -> list[str]:
        return [p for s in self.systems for p in registry.get(s).pythonpath()]


CONNECTIONS: dict[str, Connection] = {c.name: c for c in [
    Connection("nexus-siblings", "nexus_siblings", ("nexus",),
               "NEXUS SiblingInstantRouter -> AION EventStore / ARGUS MicrostructureFeature / ATHENA Provenance / DAEDALUS bridge",
               "One causally atomic NEXUS instant validated against the exact sibling contract modules (loaded by file path)."),
    Connection("nexus-contract-drift", "nexus_contract_drift", ("nexus",),
               "nexus.contract-drift-snapshot.v1 vs pinned path-independent v1.16 baseline 65cba148... (v1.15 and v0.3 retained historically)",
               "Per-boundary raw/AST drift of sibling contracts against the baseline PROMETHEUS pins (ADR 0004). Drift is reported, not auto-accepted."),
    Connection("nexus-oracle", "nexus_to_oracle", ("nexus", "oracle"),
               "nexus.market-state.v2 -> oracle.nexus_ingest MetricObservation -> FinancialState",
               "NEXUS market packet becomes ORACLE financial-state features without invented fields."),
    Connection("nexus-prometheus", "nexus_to_prometheus", ("nexus", "prometheus"),
               "SiblingInstantBundle -> prometheus_loop.adapters.nexus -> normalize_nexus_bundle (pinned NEXUS contract identity)",
               "LINKED when PROMETHEUS binds and normalizes the bundle with all fail-closed evidence tiers; with sibling drift it must quarantine (CONTRACT_DRIFT)."),
    Connection("prometheus-ascension", "prometheus_to_ascension", ("prometheus", "ascension"),
               "PROMETHEUS strict runtime ResearchProvenanceManifest -> exact byte-bound handoff -> ASCENSION Sibling Manifest Conformance Kit v0.1",
               "The actual PROMETHEUS runtime path emits a deterministic structural handoff into ASCENSION; authenticated=false and Transfer remains BLOCKED until separately governed trust/transparency evidence exists."),
    Connection("supermesh-witness", "supermesh_witness", ("supermesh_x", "nexus"),
               "NEXUS SiblingInstantBundle + pinned contract baseline -> SuperMesh-X RFC9162WitnessedCheckpointLedger -> GossipReceiptStore",
               "NEXUS artifacts witnessed in SuperMesh-X's quorum-signed append-only transparency log and independently re-verified; "
               "history rewrite and rollback must be rejected. Evidence only, no authority."),
    Connection("intelligence-fabric", "intelligence_fabric", ("nexus", "aion", "argus", "athena"),
               "NEXUS SiblingInstantBundle -> AION EventStore/PARALLAX fingerprint -> ARGUS evidence firewall + ATHENA receipt-time journal",
               "One deterministic instant is persisted, fingerprinted, evidence-tier checked, and admitted to ATHENA only at actual ingestion time; read-only research/advisory path."),
    Connection("argus-athena-research", "argus_to_athena_research", ("argus", "athena"),
               "ARGUS argus-orderblock-study-v2 registered survival uncertainty -> ATHENA receipt-time research advisory",
               "A prospectively locked ARGUS order-block survival study is exported only after its follow-up cutoff and becomes visible to ATHENA only at local ingestion time; research/advisory evidence only."),
    Connection("argus-impact-athena-research", "argus_impact_to_athena_research", ("argus", "athena"),
               "ARGUS argus-impact-calibration-study-v1 registered evidence-stratified calibration -> ATHENA receipt-time research advisory",
               "A prospectively locked ARGUS impact-calibration study is revalidated, exported only after cohort lock, and admitted to ATHENA only at local ingestion time; paper-emulator evidence is never strengthened into broker-confirmed evidence."),
]}

# Systems with no cross-system contract in their code (verified by import audit and repo-wide
# bidirectional search, 2026-09-27). Wiring them would require inventing semantics.
STANDALONE: dict[str, str] = {
    "aegis": "challenger_forge imports only the standard library; no sibling references in code; "
             "component_adapter_registry_v003.json lists intra-AEGIS adapters only.",
    "janus": "janus_infinity imports only stdlib + cryptography; its architecture spec declares it "
             "'does not alter NEXUS market-time authority or sibling responsibilities'.",
    "infrastructure": "no sibling references in any file; its proof/receipt/checkpoint schemas are closed to its own "
                      "intervention lifecycle (e.g. proof_envelope.STAGE_ORDER), so foreign artifacts would be mislabelled.",
}


def coverage() -> dict:
    """Every system either participates in >=1 verified connection or is standalone with a stated reason."""
    linked: dict[str, list[str]] = {}
    for c in CONNECTIONS.values():
        for s in c.systems:
            linked.setdefault(s, []).append(c.name)
    # Systems whose contracts are exercised inside another connection's driver or suite.
    for s, via in (("aion", "nexus-siblings"), ("argus", "nexus-siblings"), ("athena", "nexus-siblings"),
                   ("daedalus", "nexus-siblings")):
        linked.setdefault(s, []).append(via)
    out = {}
    for name in registry.SYSTEMS:
        if name in linked:
            out[name] = {"status": "connected", "connections": sorted(set(linked[name]))}
        else:
            out[name] = {"status": "standalone", "reason": STANDALONE.get(name, "UNEXPLAINED")}
    return out


def check(name: str, timeout_s: int = 300) -> dict:
    try:
        c = CONNECTIONS[name]
    except KeyError:
        return {"ok": False, "error": f"unknown connection {name!r}", "known": sorted(CONNECTIONS)}
    res = runner.run_json_driver(c.driver, c.pythonpath(), timeout_s=timeout_s)
    return {"name": name, "contract": c.contract, **res}


def check_all(timeout_s: int = 300) -> dict:
    results = {n: check(n, timeout_s) for n in CONNECTIONS}
    return {"ok": all(r.get("ok") for r in results.values()), "connections": results}
