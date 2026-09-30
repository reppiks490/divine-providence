from nexus.contracts import BarEvent
from nexus.replay import ReplayBus, ReplayAvailabilityError, ReplayOrderingError


def e(s,t,q,c): return BarEvent(s,t,q,c,c,c,c,None,s)


def test_merge_is_deterministic_and_preserves_equal_times():
    streams={'b':[e('b',10,0,2),e('b',20,1,4)], 'a':[e('a',10,0,1),e('a',20,1,3)]}
    bus=ReplayBus()
    first=[(x.stream_id,x.event_ns,x.source_sequence) for x in bus.merge(streams,require_available=False)]
    second=[(x.stream_id,x.event_ns,x.source_sequence) for x in bus.merge(streams,require_available=False)]
    assert first==second==[('a',10,0),('b',10,0),('a',20,1),('b',20,1)]


def test_asof_state_never_uses_future_value():
    merged=ReplayBus().merge({'a':[e('a',10,0,1),e('a',30,1,9)], 'b':[e('b',20,0,2)]},require_available=False)
    states=list(ReplayBus().states(merged,required_streams={'a','b'}))
    at20=next(x for x in states if x.decision_ns==20)
    assert at20.values['a']==1
    assert at20.values['b']==2


def test_replay_rejects_stream_key_mismatch():
    import pytest
    with pytest.raises(ReplayOrderingError,match='mapping key'):
        list(ReplayBus().merge({'a':[e('b',10,0,1)]},require_available=False))


def test_replay_rejects_nonincreasing_per_stream_ordering_key():
    import pytest
    rows=[e('a',20,1,2),e('a',10,0,1)]
    with pytest.raises(ReplayOrderingError,match='strictly increase'):
        list(ReplayBus().merge({'a':rows},require_available=False))


def test_strict_replay_rejects_impossible_availability_contract():
    import pytest
    early=BarEvent('a',20,0,1,1,1,1,None,'a',available_ns=10)
    with pytest.raises(ReplayAvailabilityError,match='available before'):
        list(ReplayBus().merge({'a':[early]},require_available=True))
    source_future=BarEvent('a',20,0,1,1,1,1,None,'a',available_ns=30,source_timestamp_ns=25)
    with pytest.raises(ReplayAvailabilityError,match='precedes source timestamp'):
        list(ReplayBus().merge({'a':[source_future]},require_available=True))


def test_replay_is_strict_by_default():
    import pytest
    with pytest.raises(ReplayAvailabilityError,match='unknown availability'):
        list(ReplayBus().merge({'a':[e('a',10,0,1)]}))


def test_bar_replay_rejects_negative_max_age():
    import pytest
    event=BarEvent('a',10,0,1,1,1,1,None,'a',available_ns=10)
    merged=ReplayBus().merge({'a':[event]})
    with pytest.raises(ValueError,match='max_age_ns'):
        list(ReplayBus().states(merged,max_age_ns=-1))
