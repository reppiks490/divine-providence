"""End-to-end causal intelligence fabric check.

One deterministic NEXUS instant is persisted into AION, fingerprinted by
PARALLAX, exported through ARGUS's evidence firewall, and admitted into ATHENA
only at actual ingestion time. Research/advisory evidence only; no execution.
"""
from __future__ import annotations

from tempfile import TemporaryDirectory
from pathlib import Path

from aion.contracts import Observation, SourceSpec
from aion.store import EventStore
from aion.replay import frame as aion_frame
from aion.parallax import fingerprint_from_frame
from argus.contracts import EvidenceTier as ArgusTier, MicrostructureFeature
from argus.evidence_bridge import feature_export
from athena.contracts import DataPlane, Provenance
from athena.journal import AdvisoryEvent, AdvisoryJournal

from ._common import emit
from ._nexus_instant import build


bundle, _health = build()
if bundle.production_authorized:
    raise ValueError("NEXUS bundle unexpectedly authorizes production")

# AION + PARALLAX: persist the exact routed observations, reconstruct the same
# decision instant, then build a provenance-carrying causal fingerprint.
with TemporaryDirectory() as directory:
    store = EventStore(Path(directory) / "aion.sqlite3")
    specs = {}
    for raw in bundle.aion["source_specs"]:
        spec = SourceSpec.from_dict(raw)
        store.register(spec)
        specs[spec.source_id] = spec
    appended = []
    for raw in bundle.aion["observations"]:
        observation = Observation.from_dict(raw)
        appended.append(store.append(observation))
    chain = store.verify_chain()
    if not chain.get("verified"):
        raise ValueError("AION hash chain did not verify")
    replay = aion_frame(store, bundle.decision_ns)
    fingerprint = fingerprint_from_frame(replay)
    if any(axis.available_ns > bundle.decision_ns for axis in fingerprint.axes):
        raise ValueError("PARALLAX admitted future evidence")
    if not fingerprint.axes:
        raise ValueError("PARALLAX produced an empty fingerprint")
    if replay.get("execution_authorized") is not False:
        raise ValueError("AION replay authority boundary changed")

# ARGUS: the routed NEXUS factor must remain a candle-derived proxy. Exporting
# it through the explicit bridge must not strengthen the tier.
argus_exports = []
for raw in bundle.argus["features"]:
    feature = MicrostructureFeature(
        raw["name"],
        raw["value"],
        ArgusTier(raw["evidence_tier"]),
        raw["event_time_ns"],
        raw["source_id"],
        raw["reason"],
    )
    if feature.evidence_tier is not ArgusTier.CANDLE_PROXY:
        raise ValueError("NEXUS factor escaped ARGUS CANDLE_PROXY firewall")
    exported = feature_export(feature)
    if exported["aion_evidence_tier_name"] != "CANDLE_PROXY" or exported["execution_authorized"]:
        raise ValueError("ARGUS evidence bridge strengthened or authorized a proxy")
    argus_exports.append(exported)

# ATHENA: provider/event availability is not enough to make the advisory input
# visible before actual ingestion. This explicitly exercises the stricter local
# receipt-time boundary.
journal = AdvisoryJournal()
ingestion_times = []
for index, raw in enumerate(bundle.athena["provenance"], start=1):
    provenance = Provenance(
        raw["event_time_ns"],
        raw["ingestion_time_ns"],
        raw["source_id"],
        raw["representation_id"],
        raw["version"],
        DataPlane(raw["plane"]),
        raw["lineage_id"],
        tuple(raw["quality_flags"]),
    )
    ingestion_times.append(provenance.ingestion_time_ns)
    journal.append(AdvisoryEvent(
        provenance=provenance,
        kind="nexus_market_state",
        available_ns=max(provenance.event_time_ns, bundle.decision_ns),
        payload={
            "bundle_hash": bundle.bundle_hash,
            "frame_hash": bundle.frame_hash,
            "factors": bundle.athena.get("factors", {}),
            "quality": bundle.athena.get("quality", {}),
            "ood": bundle.athena.get("ood", {}),
        },
        sequence=index,
    ))

first_ingestion = min(ingestion_times)
if first_ingestion > 0 and journal.asof(first_ingestion - 1):
    raise ValueError("ATHENA exposed NEXUS evidence before local ingestion")
athena = journal.frame(max(ingestion_times), max_age_ns=1_000_000_000)
if athena["production_authorized"] or not athena["advisory_only"]:
    raise ValueError("ATHENA authority boundary changed")
if athena["abstain_required"]:
    raise ValueError(f"ATHENA rejected healthy deterministic fixture: {athena}")
if not journal.verify()["verified"]:
    raise ValueError("ATHENA advisory journal did not verify")

emit({
    "connection": "nexus->aion/parallax->argus/athena",
    "ok": True,
    "bundle_hash": bundle.bundle_hash,
    "decision_ns": bundle.decision_ns,
    "aion": {
        "events": len(appended),
        "chain_verified": True,
        "frame_hash": replay["frame_hash"],
    },
    "parallax": {
        "fingerprint_id": fingerprint.fingerprint_id,
        "axes": len(fingerprint.axes),
        "future_axes": 0,
    },
    "argus": {
        "features": len(argus_exports),
        "proxy_only": True,
    },
    "athena": {
        "events": len(athena["evidence"]),
        "frame_id": athena["frame_id"],
        "receipt_time_gated": True,
        "abstain_required": athena["abstain_required"],
    },
    "execution_authorized": False,
    "production_authorized": False,
})
