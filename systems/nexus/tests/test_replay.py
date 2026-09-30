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
    states=list(ReplayBus().states(
        merged,required_streams={'a','b'},require_available=False
    ))
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


def test_bar_event_rejects_structurally_invalid_identity_and_numbers():
    import pytest
    with pytest.raises(ValueError,match='event_ns'):
        BarEvent('s',-1,0,1,2,0,1,None,'p')
    with pytest.raises(ValueError,match='source_sequence'):
        BarEvent('s',1,-1,1,2,0,1,None,'p')
    with pytest.raises(ValueError,match='revision'):
        BarEvent('s',1,0,1,2,0,1,None,'p',revision=-1)
    with pytest.raises(ValueError,match='close'):
        BarEvent('s',1,0,1,2,0,float('nan'),None,'p')
    with pytest.raises(ValueError,match='available_ns'):
        BarEvent('s',1,0,1,2,0,1,None,'p',available_ns=-1)


def test_direct_state_construction_cannot_bypass_availability_gate():
    import pytest
    unknown=BarEvent('a',10,0,1,1,1,1,None,'a')
    with pytest.raises(Exception,match='unknown availability'):
        list(ReplayBus().states([unknown]))
    forensic=list(ReplayBus().states([unknown],require_available=False))
    assert forensic[0].decision_ns==10


def test_direct_state_batches_reject_nonincreasing_batch_time():
    import pytest
    from nexus.contracts import ReplayBatch
    a=BarEvent('a',10,0,1,1,1,1,None,'a',available_ns=10)
    b=BarEvent('b',9,0,1,1,1,1,None,'b',available_ns=9)
    batches=[ReplayBatch(10,(a,)),ReplayBatch(9,(b,))]
    with pytest.raises(Exception,match='strictly increase'):
        list(ReplayBus().states_batches(batches))


def test_direct_states_reject_global_visibility_rewind():
    import pytest
    a=BarEvent('a',20,0,1,1,1,1,None,'a',available_ns=20)
    b=BarEvent('b',10,0,1,1,1,1,None,'b',available_ns=10)
    with pytest.raises(Exception,match='visibility moved backward'):
        list(ReplayBus().states([a,b]))


def test_replay_batch_rejects_empty_events():
    import pytest
    from nexus.contracts import ReplayBatch
    with pytest.raises(ValueError,match='at least one'):
        ReplayBatch(10,())


def test_state_packet_rejects_inconsistent_maps_and_invalid_age():
    import pytest
    from nexus.contracts import StatePacket
    with pytest.raises(ValueError,match='keys must match'):
        StatePacket(10,{'a':1.0},{},(),{'a':0},{'a':'x'})
    with pytest.raises(ValueError,match='also be missing'):
        StatePacket(10,{'a':1.0},{'a':0},('a',),{'a':0},{'a':'x'})
    with pytest.raises(ValueError,match='age'):
        StatePacket(10,{'a':1.0},{'a':11},(),{'a':0},{'a':'x'})
    with pytest.raises(ValueError,match='finite'):
        StatePacket(10,{'a':float('inf')},{'a':0},(),{'a':0},{'a':'x'})


def test_state_packet_requires_canonical_missing_and_lineage():
    import pytest
    from nexus.contracts import StatePacket
    with pytest.raises(ValueError,match='sorted canonically'):
        StatePacket(10,{}, {}, ('b','a'), {}, {})
    with pytest.raises(ValueError,match='non-empty stream ids'):
        StatePacket(10,{}, {}, ('',), {}, {})
    with pytest.raises(ValueError,match='lineage'):
        StatePacket(10,{'a':1.0},{'a':0},(),{'a':0},{'a':''})


def test_replay_rejects_coerced_option_types():
    import pytest
    event=BarEvent("a",10,0,1,1,1,1,None,"a",available_ns=10)
    with pytest.raises(TypeError,match="require_available"):
        list(ReplayBus().merge({"a":[event]},require_available=1))
    with pytest.raises(ValueError,match="max_age_ns"):
        list(ReplayBus().states([event],max_age_ns=1.5))
    with pytest.raises(ValueError,match="max_age_ns"):
        list(ReplayBus().states([event],max_age_ns=True))
