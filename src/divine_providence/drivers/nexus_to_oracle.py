"""NEXUS market-state.v2 packet -> ORACLE MetricObservations -> FinancialState."""
from oracle.financial import FinancialStateEngine
from oracle.nexus_ingest import metric_observations_from_nexus_bundle

from ._common import emit
from ._nexus_instant import FACTORS, OOD, QUALITY, TOPOLOGY, build

bundle, _ = build()
packet = bundle.to_dict()["athena"]  # contract nexus.market-state.v2 (research data plane)
rows = metric_observations_from_nexus_bundle(packet)
engine = FinancialStateEngine()
for row in rows:
    engine.ingest(row)
state = engine.build(packet["decision_ns"], ood_score=OOD["novelty"])
expected = {f"{sec}.{k}": v for sec, vals in (("factors", FACTORS), ("topology", TOPOLOGY), ("quality", QUALITY), ("ood", OOD))
            for k, v in vals.items()}
features = dict(state.features)
emit({"connection": "nexus->oracle",
      "ok": (packet["contract"] == "nexus.market-state.v2" and packet["production_authorized"] is False
             and features == expected),
      "packet_contract": packet["contract"], "observations": len(rows),
      "financial_state_features": features, "expected_features": expected})
