"""NEXUS current same-instant bundle -> PROMETHEUS NEXUS adapter -> normalized observations.

PROMETHEUS binds only under a contract identity it pins (ADR 0002/0004/0005). The hub presents
the recorded baseline identity when the live sibling boundaries show no semantic drift from
it, and otherwise presents the live snapshot's own identity, which PROMETHEUS must quarantine
(CONTRACT_DRIFT).

``link_state``: LINKED (data flows), QUARANTINED_AS_EXPECTED (drift, correctly refused;
fail-closed but not connected) or BROKEN. ``ok`` is true only when LINKED.
"""
import json

from prometheus_loop.adapters.nexus import PINNED_NEXUS_CONTRACT_SNAPSHOT_HASHES, NexusBundleBinding, try_bind_nexus_bundle
from prometheus_loop.adapters.siblings import normalize_nexus_bundle

from ._common import emit
from ._nexus_instant import build
from .nexus_contract_drift import run as drift_report

# Sibling evidence tiers that must survive normalization unchanged (fail-closed labels).
REQUIRED_TIERS = {"ARGUS": "CANDLE_PROXY", "DAEDALUS": "RESEARCH_CANDIDATE_ONLY"}
SIBLINGS = {"NEXUS", "ARGUS", "ATHENA", "DAEDALUS"}

drift = drift_report()
bundle, _ = build()
payload = json.loads(json.dumps(bundle.to_dict()))
identity = drift["baseline_snapshot_hash"] if not drift["semantic_drift"] else drift["current_snapshot_hash"]
bound = try_bind_nexus_bundle(payload, identity)
accepted = isinstance(bound, NexusBundleBinding)
out = {"connection": "nexus->prometheus", "accepted": accepted, "contract_identity": identity,
       "identity_pinned_by_prometheus": identity in PINNED_NEXUS_CONTRACT_SNAPSHOT_HASHES,
       "semantic_drift_vs_current_baseline": drift["semantic_drift"],
       "drifted_boundaries": [i for i in drift["items"] if i["status"] == "semantic_change"]}
if accepted:
    obs = normalize_nexus_bundle(bound)
    tiers = {o.sibling: o.evidence_tier for o in obs}
    out.update(decision_ns=bound.decision_ns, bundle_hash=bound.bundle_hash,
               observations=[{"sibling": o.sibling, "evidence_tier": o.evidence_tier} for o in obs])
    linked = (not drift["semantic_drift"] and set(tiers) == SIBLINGS
              and all(tiers.get(s) == t for s, t in REQUIRED_TIERS.items()))
    out["link_state"] = "LINKED" if linked else "BROKEN"
else:
    out.update(refusal={"failure_type": bound.failure_type, "details": bound.details})
    expected_refusal = drift["semantic_drift"] and bound.failure_type == "CONTRACT_DRIFT"
    out["link_state"] = "QUARANTINED_AS_EXPECTED" if expected_refusal else "BROKEN"
out["ok"] = out["link_state"] == "LINKED"
emit(out)
