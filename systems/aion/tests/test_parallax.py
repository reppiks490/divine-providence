import pytest

from aion.parallax import AnalogAtlas, AxisObservation, build_fingerprint, fingerprint_from_frame, mask_fingerprint, observations_from_frame


def obs(axis, value, available, source="s", representation="r", lineage=None):
    return AxisObservation(
        axis=axis,
        value=value,
        available_ns=available,
        source_id=source,
        representation_id=representation,
        lineage_id=lineage or f"{source}:{axis}:{available}",
    )


def fp(time, x, y, *, source_x="price", source_y="macro"):
    return build_fingerprint(time, [
        obs("x", x, time, source=source_x),
        obs("y", y, time, source=source_y),
    ])


def test_build_fingerprint_is_strictly_asof_and_latest_by_axis():
    frame = build_fingerprint(20, [
        obs("x", 1, 10),
        obs("x", 2, 20),
        obs("x", 999, 21),
        obs("y", 3, 19),
    ])
    assert frame.values == {"x": 2.0, "y": 3.0}
    assert all(x.available_ns <= 20 for x in frame.axes)


def test_analog_search_excludes_future_states_and_is_deterministic():
    atlas = AnalogAtlas()
    a = fp(10, 0.0, 0.0)
    b = fp(20, 1.0, 1.0)
    future = fp(40, 1.1, 1.1)
    for frame in (future, b, a):
        atlas.add(frame)

    query = fp(30, 1.05, 1.05)
    first = atlas.neighbors(query, k=5)
    second = atlas.neighbors(query, k=5)
    assert first == second
    ids = [x["fingerprint_id"] for x in first["neighbors"]]
    assert future.fingerprint_id not in ids
    assert ids[0] == b.fingerprint_id
    assert first["execution_authorized"] is False
    assert first["causal_only"] is True


def test_future_and_unverified_outcomes_do_not_enter_summary():
    atlas = AnalogAtlas()
    a = fp(10, 0.0, 0.0)
    b = fp(20, 1.0, 1.0)
    query = fp(30, 0.5, 0.5)
    atlas.add(a)
    atlas.add(b)
    result = atlas.neighbors(query, k=2)

    atlas.settle(a.fingerprint_id, outcome=0.5, available_ns=25, source_id="labels", verified=True)
    atlas.settle(b.fingerprint_id, outcome=-0.5, available_ns=100, source_id="labels", verified=True)
    early = atlas.outcome_summary(result, asof_ns=30)
    assert early["verified_samples"] == 1
    assert early["mean"] == 0.5
    assert early["hidden_future_outcomes"] == 1

    late = atlas.outcome_summary(result, asof_ns=100)
    assert late["verified_samples"] == 2
    assert late["mean"] == 0.0

    c = fp(25, 0.6, 0.6)
    atlas.add(c)
    atlas.settle(c.fingerprint_id, outcome=1.0, available_ns=29, source_id="fixture", verified=False)
    result = atlas.neighbors(query, k=3)
    assert atlas.outcome_summary(result, asof_ns=100)["verified_samples"] == 2


def test_source_ablation_measures_neighbor_fragility():
    atlas = AnalogAtlas()
    a = fp(10, 0.0, 10.0)
    b = fp(20, 1.0, 0.0)
    c = fp(25, 1.1, 9.0)
    for frame in (a, b, c):
        atlas.add(frame)

    query = fp(30, 1.0, 10.0)
    result = atlas.ablation(query, source_id="macro", k=2, min_shared_axes=1)
    assert 0.0 <= result["neighbor_overlap"] <= 1.0
    assert result["full"]["query_axes"] == ["x", "y"]
    assert result["masked"]["query_axes"] == ["x"]
    assert result["execution_authorized"] is False


def test_masks_and_settlements_fail_closed():
    frame = fp(10, 1, 2, source_x="same", source_y="same")
    with pytest.raises(ValueError, match="every"):
        mask_fingerprint(frame, exclude_sources=("same",))

    atlas = AnalogAtlas()
    atlas.add(frame)
    with pytest.raises(ValueError, match="after"):
        atlas.settle(frame.fingerprint_id, outcome=1, available_ns=10, source_id="labels", verified=True)
    with pytest.raises(KeyError):
        atlas.settle("missing", outcome=1, available_ns=20, source_id="labels", verified=True)


def test_nonfinite_axes_rejected():
    with pytest.raises(ValueError, match="finite"):
        obs("x", float("nan"), 1)


def test_aion_frame_adapter_preserves_lineage_and_normalizes_price_geometry():
    frame = {
        "asof_ns": 100,
        "frame_hash": "f" * 64,
        "source_count": 2,
        "synthetic": False,
        "evidence_hashes": ["a" * 64, "b" * 64],
        "prices": [{
            "symbol": "NQ",
            "representation_id": "clock:1m",
            "source_id": "nq-bars",
            "event_ns": 90,
            "available_ns": 95,
            "open": 100.0,
            "high": 103.0,
            "low": 99.0,
            "close": 102.0,
            "event_hash": "a" * 64,
        }],
        "books": {
            "nq-depth": {
                "status": "true_depth",
                "sequence": 7,
                "best_bid": 101.75,
                "best_ask": 102.0,
                "spread": 0.25,
                "imbalance": 0.2,
                "age_ns": 2,
            }
        },
        "macro": [{
            "source_id": "macro-fed",
            "available_ns": 80,
            "revision": 1,
            "values": {"series": "DXY", "period": "2026-09", "value": 97.5},
        }],
    }
    observations = observations_from_frame(frame)
    assert all(x.available_ns <= frame["asof_ns"] for x in observations)
    fingerprint = fingerprint_from_frame(frame)
    assert fingerprint.decision_ns == 100
    assert fingerprint.values["price.NQ.clock:1m.body_pct"] == pytest.approx(2 / 102)
    assert fingerprint.values["book.nq-depth.imbalance"] == pytest.approx(0.2)
    assert fingerprint.values["macro.macro-fed.DXY.value"] == pytest.approx(97.5)
    assert fingerprint.sources["price.NQ.clock:1m.body_pct"] == "nq-bars"


def test_aion_frame_adapter_rejects_future_evidence_instead_of_hiding_it():
    frame = {
        "asof_ns": 100,
        "frame_hash": "f" * 64,
        "prices": [{
            "symbol": "NQ",
            "representation_id": "clock:1m",
            "source_id": "nq-bars",
            "available_ns": 101,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.5,
            "event_hash": "a" * 64,
        }],
        "books": {},
        "macro": [],
    }
    with pytest.raises(ValueError, match="future evidence"):
        fingerprint_from_frame(frame)


def test_neighbor_distance_balances_sources_not_axis_width():
    atlas = AnalogAtlas()
    query = build_fingerprint(30, [
        obs("price.a", 0.0, 30, source="wide"),
        obs("price.b", 0.0, 30, source="wide"),
        obs("price.c", 0.0, 30, source="wide"),
        obs("macro.x", 0.0, 30, source="macro"),
    ])
    candidate_wide_close = build_fingerprint(10, [
        obs("price.a", 0.1, 10, source="wide"),
        obs("price.b", 0.1, 10, source="wide"),
        obs("price.c", 0.1, 10, source="wide"),
        obs("macro.x", 10.0, 10, source="macro"),
    ])
    candidate_balanced = build_fingerprint(20, [
        obs("price.a", 1.0, 20, source="wide"),
        obs("price.b", 1.0, 20, source="wide"),
        obs("price.c", 1.0, 20, source="wide"),
        obs("macro.x", 0.1, 20, source="macro"),
    ])
    atlas.add(candidate_wide_close)
    atlas.add(candidate_balanced)
    result = atlas.neighbors(query, k=2, min_shared_axes=1)
    assert "source_distances" in result["neighbors"][0]
    assert set(result["neighbors"][0]["source_distances"]) == {"macro", "wide"}


def test_same_time_conflicting_axis_observations_fail_closed():
    with pytest.raises(ValueError, match="ambiguous same-time observations"):
        build_fingerprint(20, [
            obs("x", 1.0, 20, lineage="first"),
            obs("x", 2.0, 20, lineage="second"),
        ])


def test_neighbor_mask_honors_one_shot_iterables():
    atlas = AnalogAtlas()
    candidate_a = build_fingerprint(10, [
        obs("x", 0.0, 10, source="keep"),
        obs("y", 100.0, 10, source="drop"),
    ])
    candidate_b = build_fingerprint(20, [
        obs("x", 2.0, 20, source="keep"),
        obs("y", 0.0, 20, source="drop"),
    ])
    atlas.add(candidate_a)
    atlas.add(candidate_b)
    query = build_fingerprint(30, [
        obs("x", 0.1, 30, source="keep"),
        obs("y", 0.0, 30, source="drop"),
    ])

    excluded_sources = (name for name in ["drop"])
    result = atlas.neighbors(
        query,
        k=2,
        min_shared_axes=1,
        exclude_sources=excluded_sources,
    )
    assert result["query_axes"] == ["x"]
    assert result["neighbors"][0]["fingerprint_id"] == candidate_a.fingerprint_id

    excluded_axes = (name for name in ["y"])
    result_axes = atlas.neighbors(
        query,
        k=2,
        min_shared_axes=1,
        exclude_axes=excluded_axes,
    )
    assert result_axes["query_axes"] == ["x"]
