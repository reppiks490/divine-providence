import pytest

from aion.parallax import AnalogAtlas, AxisObservation, build_fingerprint, mask_fingerprint


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
