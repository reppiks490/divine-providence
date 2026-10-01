from pathlib import Path
import sys

SYSTEMS = Path(__file__).resolve().parents[2]
sys.path[:0] = [
    str(SYSTEMS / "aion"),
    str(SYSTEMS / "argus" / "src"),
    str(SYSTEMS / "athena" / "src"),
]

from aion.parallax import AnalogAtlas, AxisObservation, build_fingerprint
from argus.contracts import EvidenceTier, MicrostructureFeature
from argus.evidence_bridge import feature_export
from athena.contracts import DataPlane, Provenance
from athena.journal import AdvisoryEvent, AdvisoryJournal


def test_research_fabric_is_causal_and_advisory():
    feature = MicrostructureFeature("state", 0.25, EvidenceTier.CANDLE_PROXY, 100, "nexus", "smoke")
    assert feature_export(feature)["execution_authorized"] is False

    p = Provenance(100, 110, "nexus", "state-v2", "v2", DataPlane.RESEARCH, "lineage")
    journal = AdvisoryJournal()
    journal.append(AdvisoryEvent(p, "market_state", 110, {"factor": 0.25}, 1))
    assert journal.asof(109) == []
    assert journal.frame(110, max_age_ns=20)["production_authorized"] is False

    atlas = AnalogAtlas()
    old = build_fingerprint(90, (
        AxisObservation("factor", 0.2, 90, "nexus", "state-v2", "old-factor"),
        AxisObservation("quality", 0.9, 90, "nexus", "state-v2", "old-quality"),
    ))
    now = build_fingerprint(110, (
        AxisObservation("factor", 0.25, 110, "nexus", "state-v2", "now-factor"),
        AxisObservation("quality", 0.95, 110, "nexus", "state-v2", "now-quality"),
    ))
    atlas.add(old)
    result = atlas.neighbors(now, k=1, min_shared_axes=2)
    assert result["neighbors"][0]["fingerprint_id"] == old.fingerprint_id
    assert result["execution_authorized"] is False
