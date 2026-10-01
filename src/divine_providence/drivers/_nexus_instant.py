"""Build one causally atomic NEXUS same-instant sibling bundle from NEXUS's public API.

Mirrors the fixture NEXUS itself uses in ``nexus.sibling_validation`` (one verified
1-minute NQ bar). Synthetic: it proves contract shape and routing, not market truth.
"""
from __future__ import annotations

from nexus.contracts import BarEvent, StreamIdentity, StreamManifest
from nexus.replay import ReplayBus
from nexus.lineage import DerivationRecord
from nexus.source_health import SourceHealthRegistry, SourceSLOPolicy
from nexus.sibling_replay import SiblingInstantRouter

FACTORS = {"market_state": 0.25}
TOPOLOGY = {"entropy": 0.5}
QUALITY = {"coverage": 1.0}
OOD = {"novelty": 0.1}


def build():
    ident = StreamIdentity("csv", "CME", "NQ1!", "1", "clock:1m", "NQ.csv", "a" * 64)
    manifest = StreamManifest(ident, 2, ["time", "open", "high", "low", "close"], 1, 2, 60_000_000_000, 1.0, 0, 0, 0)
    event = BarEvent(ident.stream_id, 100, 0, 1, 2, 0.5, 1.5, 10, "NQ.csv", available_ns=160,
                     availability_basis="verified_bar_close")
    bus = ReplayBus()
    batch = next(bus.merge_batches({ident.stream_id: [event]}, require_available=True))
    state = next(bus.states_batches([batch]))
    deriv = DerivationRecord.create(product_id="NEXUS:DIVINE_PROVIDENCE_LINK", product_version="1",
                                    decision_ns=state.decision_ns, spec_hash="b" * 64,
                                    input_hashes={"NQ": ident.raw_sha256}, code_version="divine-providence-hub")
    health = SourceHealthRegistry()
    health.set_policy(ident.stream_id, SourceSLOPolicy(max_receive_lag_ns_p95=20, max_gap_size=0))
    # This fixture represents evidence that was actually received by the decision instant.
    # SourceHealthRegistry correctly refuses to project a receipt observed at t=170 back into
    # the t=160 decision state, so keep the synthetic receipt clock causally aligned here.
    health.observe(event, received_ns=state.decision_ns)
    plane = health.snapshot(state.decision_ns)
    bundle = SiblingInstantRouter().package(batch=batch, state=state, manifests={ident.stream_id: manifest},
                                            factors=FACTORS, topology=TOPOLOGY, quality=QUALITY, ood=OOD,
                                            ingested_ns=170, factor_derivations=[deriv], source_health=plane)
    return bundle, plane
