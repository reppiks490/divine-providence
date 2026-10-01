"""Sibling-contract drift: live monorepo sibling boundaries vs the pinned NEXUS contract baselines.

The current baseline is the path-independent v1.16 snapshot PROMETHEUS pins (ADR 0005);
v1.15 and the v0.3 release baseline are both retained and reported for history. Drift is judged per
boundary on raw and AST fingerprints with NEXUS's own ``compare_contract_snapshots``.
"""
from nexus.contract_sentinel import ContractDriftSnapshot, compare_contract_snapshots

from ._common import SYSTEMS, emit, sibling_roots

BASELINES = SYSTEMS / "nexus" / "contracts" / "baselines"
CURRENT = BASELINES / "sibling_contract_drift_baseline.v1.16.monorepo.json"
PREVIOUS_V115 = BASELINES / "sibling_contract_drift_baseline.v1.15.monorepo.json"
RELEASE_V03 = BASELINES / "sibling_contract_drift_baseline.v0.3.SOL.json"


def _items(report: dict) -> list[dict]:
    return [{k: i[k] for k in ("sibling", "role", "status")} for i in report["items"]]


def run() -> dict:
    r = sibling_roots()
    current = ContractDriftSnapshot.capture({
        ("AION", "contracts"): r["aion"] / "aion" / "contracts.py",
        ("AION", "store"): r["aion"] / "aion" / "store.py",
        ("ARGUS", "contracts"): r["argus"] / "src" / "argus" / "contracts.py",
        ("ATHENA", "contracts"): r["athena"] / "src" / "athena" / "contracts.py",
        ("DAEDALUS", "bridge"): r["daedalus"] / "src" / "daedalus" / "bridge.py",
    }, relative_to=SYSTEMS)
    baseline = ContractDriftSnapshot.load(CURRENT)
    rep = compare_contract_snapshots(baseline, current).to_dict()
    v115 = compare_contract_snapshots(ContractDriftSnapshot.load(PREVIOUS_V115), current).to_dict()
    v03 = compare_contract_snapshots(ContractDriftSnapshot.load(RELEASE_V03), current).to_dict()
    return {"connection": "nexus-contract-drift", "ok": not rep["semantic_drift"],
            "baseline_snapshot_hash": baseline.snapshot_hash, "current_snapshot_hash": current.snapshot_hash,
            "semantic_drift": rep["semantic_drift"],
            "raw_drift": rep["raw_drift"], "items": _items(rep),
            "vs_v115": {"baseline_snapshot_hash": v115["baseline_hash"], "items": _items(v115)},
            "vs_v03_release": {"baseline_snapshot_hash": v03["baseline_hash"], "items": _items(v03)}}


if __name__ == "__main__":
    emit(run())
