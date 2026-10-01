from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd
import pytest

from nexus.adapters import aion_bar_observation, aion_source_spec, argus_candle_proxy_feature, athena_provenance
from nexus.checkpoint import ReplayCheckpoint
from nexus.clock import ClockPolicyError, ClockPolicyRegistry, RepresentationClockRule
from nexus.contracts import BarEvent, StatePacket, StreamIdentity, StreamManifest
from nexus.ensemble import AdaptiveFactorEnsemble, EnsembleDefinition
from nexus.identity_registry import IdentityRecord, IdentityRegistry
from nexus.ingest import BarClockPolicy
from nexus.ood import RollingMahalanobisOOD
from nexus.quality_state import QualityStateEngine
from nexus.replay import ReplayBus


def ev(s: str, event: int, avail: int, seq: int, value: float) -> BarEvent:
    return BarEvent(s, event, seq, value, value, value, value, None, s, available_ns=avail)


def manifest(stream_hash: str = "a" * 64, cadence: int = 60) -> StreamManifest:
    ident = StreamIdentity("csv", "CME", "NQ", "1", "clock:1m", "NQ.csv", stream_hash)
    return StreamManifest(ident, 10, ["time", "open", "high", "low", "close"], 0, 600, cadence, 1.0, 0, 0, 0)


def test_same_visibility_is_batch_atomic():
    bus = ReplayBus()
    streams = {
        "a": [ev("a", 10, 20, 0, 1.0)],
        "b": [ev("b", 15, 20, 0, 2.0)],
    }
    states = list(bus.states_batches(bus.merge_batches(streams), required_streams={"a", "b"}))
    assert len(states) == 1
    assert states[0].batch_size == 2
    assert states[0].values == {"a": 1.0, "b": 2.0}


def test_open_stamped_bar_is_not_visible_until_completion():
    p = BarClockPolicy(source_stamp="open", cadence_ns=60, availability_delay_ns=5, basis="verified_bar_close")
    event_ns, available_ns, flags, basis = p.resolve(100)
    assert event_ns == 160 and available_ns == 165
    assert flags == () and basis == "verified_bar_close"


def test_clock_registry_refuses_unreviewed_or_variable_bar_coercion():
    m = manifest()
    r = ClockPolicyRegistry()
    r.register(RepresentationClockRule("clock:1m", "open", reviewed=True))
    assert r.bar_policy("clock:1m", m).resolve(100)[1] == 160
    r.register(RepresentationClockRule("renko", "event", cadence_mode="variable", reviewed=True))
    with pytest.raises(ClockPolicyError):
        r.bar_policy("renko", m)
    r.register(RepresentationClockRule("mystery", "open", reviewed=False))
    with pytest.raises(ClockPolicyError):
        r.bar_policy("mystery", m)


def test_identity_registry_is_immutable():
    r = IdentityRegistry()
    a = IdentityRecord("s", "NQ", "future", representation_class="clock:1m")
    r.register(a)
    with pytest.raises(ValueError):
        r.register(IdentityRecord("s", "MNQ", "future", representation_class="clock:1m"))


def test_factor_ensemble_exposes_disagreement_and_confidence():
    rng = np.random.default_rng(11)
    n = 220
    base = np.cumsum(rng.normal(0, .01, n))
    x = pd.DataFrame({
        "A": 100 * np.exp(base + rng.normal(0, .003, n)),
        "B": 100 * np.exp(base + rng.normal(0, .006, n)),
        "C": 100 * np.exp(-0.4 * base + rng.normal(0, .02, n)),
    })
    out = AdaptiveFactorEnsemble().build(x, EnsembleDefinition("NEXUS:X", ("A", "B", "C"), window=80, min_periods=40))
    assert len(out) > 0
    assert {"value", "confidence", "method_disagreement"}.issubset(out.columns)
    assert (out["method_disagreement"].fillna(0) >= 0).all()
    assert out["confidence"].dropna().between(0, 1).all()


def test_multivariate_ood_is_trailing_only():
    rng = np.random.default_rng(3)
    x = pd.DataFrame(rng.normal(size=(180, 3)), columns=list("abc"))
    eng = RollingMahalanobisOOD(window=80, min_periods=40)
    before = eng.score(x).copy()
    y = x.copy()
    y.iloc[-1] = [100, 100, 100]
    after = eng.score(y)
    common = before.index.intersection(after.index)
    # Changing the future/final row cannot alter earlier OOD scores.
    earlier = common[common < x.index[-1]]
    assert np.allclose(before.loc[earlier, "ood_score"], after.loc[earlier, "ood_score"])
    assert after.loc[x.index[-1], "ood_score"] > before.loc[x.index[-1], "ood_score"]


def test_checkpoint_is_deterministic_and_tamper_evident(tmp_path: Path):
    s = StatePacket(20, {"a": 1.0}, {"a": 0}, (), {"a": 1}, {"a": "x"}, batch_size=1, frame_hash="f")
    a = ReplayCheckpoint.from_state(s)
    b = ReplayCheckpoint.from_state(s)
    assert a.checkpoint_hash == b.checkpoint_hash and a.verify()
    path = tmp_path / "cp.json"
    a.save(path)
    loaded = ReplayCheckpoint.load(path)
    assert loaded.verify()
    d = json.loads(path.read_text())
    d["state"]["values"]["a"] = 2.0
    path.write_text(json.dumps(d))
    with pytest.raises(ValueError,match='integrity/semantic'):
        ReplayCheckpoint.load(path)
    assert not ReplayCheckpoint.load(path,verify=False).verify()


def test_dynamic_quality_plane_tracks_missingness_and_age():
    m = manifest(cadence=100)
    sid = m.identity.stream_id
    p = StatePacket(250, {sid: 1.0}, {sid: 150}, (), {sid: 2}, {sid: "NQ.csv"})
    q = QualityStateEngine().build(p, {sid: m})
    assert q.coverage == 1.0
    assert 0 < q.streams[sid].dynamic_quality < q.streams[sid].base_quality
    p2 = StatePacket(250, {}, {}, (sid,), {}, {})
    q2 = QualityStateEngine().build(p2, {sid: m})
    assert q2.streams[sid].dynamic_quality == 0.0 and q2.missing_count == 1


def test_sibling_export_shapes_include_strict_aion_fields():
    m = manifest()
    spec = aion_source_spec(m)
    assert spec["max_evidence_tier"] == 1 and spec["capabilities"] == ["bar"]
    event = ev(m.identity.stream_id, 100, 160, 4, 2.0)
    obs = aion_bar_observation(event, ingested_ns=170, availability_basis='observed_receipt')
    assert obs["published_ns"] is None
    assert obs["event_ns"] <= obs["available_ns"] <= obs["ingested_ns"]
    assert argus_candle_proxy_feature(name="x", value=1, event_ns=100, source_id="s", reason="csv")["evidence_tier"] == 1
    prov = athena_provenance(event_time_ns=100, ingestion_time_ns=170, source_id="s", representation_id="clock:1m", version="2", lineage_id="h")
    assert prov["plane"] == "research"


def test_strict_replay_rejects_unknown_availability():
    from nexus.replay import ReplayAvailabilityError
    unknown = BarEvent('x', 10, 0, 1, 1, 1, 1, None, 'x')
    with pytest.raises(ReplayAvailabilityError):
        list(ReplayBus().merge({'x': [unknown]}, require_available=True))
    known = BarEvent('x', 10, 0, 1, 1, 1, 1, None, 'x', available_ns=20)
    assert list(ReplayBus().merge({'x': [known]}, require_available=True))[0].visible_ns == 20


def test_aion_adapter_refuses_conservative_inferred_availability_basis():
    e = BarEvent('s', 10, 0, 1, 1, 1, 1, None, 'x', available_ns=20,
                 availability_basis='conservative_next_strictly_later_source_stamp')
    with pytest.raises(ValueError):
        aion_bar_observation(e)


def test_aion_adapter_rejects_impossible_known_availability():
    bad=BarEvent('s',20,0,1,1,1,1,None,'x',available_ns=10,availability_basis='verified_bar_close')
    with pytest.raises(ValueError,match='before event'):
        aion_bar_observation(bad)
