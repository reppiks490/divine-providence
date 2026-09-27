from nexus.contracts import BarEvent
from nexus.replay import ReplayBus


def e(s,t,q,c): return BarEvent(s,t,q,c,c,c,c,None,s)


def test_merge_is_deterministic_and_preserves_equal_times():
    streams={'b':[e('b',10,0,2),e('b',20,1,4)], 'a':[e('a',10,0,1),e('a',20,1,3)]}
    bus=ReplayBus()
    first=[(x.stream_id,x.event_ns,x.source_sequence) for x in bus.merge(streams)]
    second=[(x.stream_id,x.event_ns,x.source_sequence) for x in bus.merge(streams)]
    assert first==second==[('a',10,0),('b',10,0),('a',20,1),('b',20,1)]


def test_asof_state_never_uses_future_value():
    merged=ReplayBus().merge({'a':[e('a',10,0,1),e('a',30,1,9)], 'b':[e('b',20,0,2)]})
    states=list(ReplayBus().states(merged,required_streams={'a','b'}))
    at20=next(x for x in states if x.decision_ns==20)
    assert at20.values['a']==1
    assert at20.values['b']==2
