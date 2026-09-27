from nexus.contracts import BarEvent, StreamIdentity, StreamManifest
from nexus.replay import ReplayBus
from nexus.sibling_replay import SiblingInstantRouter
from nexus.source_health import SourceHealthRegistry, SourceSLOPolicy


def _manifest(symbol: str, sha: str):
    ident = StreamIdentity('csv', 'X', symbol, '1', 'clock:1m', f'{symbol}.csv', sha * 64)
    return StreamManifest(ident, 1, ['time','open','high','low','close'], 100, 100, 60, 1.0, 0, 0, 0)


def test_replay_instants_bind_batch_and_post_batch_state():
    ma = _manifest('A', 'a'); mb = _manifest('B', 'b')
    ea = BarEvent(ma.identity.stream_id, 100, 0, 1,2,.5,1.5,None,'A.csv', available_ns=160, availability_basis='verified_bar_close')
    eb = BarEvent(mb.identity.stream_id, 100, 0, 2,3,1.5,2.5,None,'B.csv', available_ns=160, availability_basis='verified_bar_close')
    instant = next(ReplayBus().instants({ea.stream_id:[ea], eb.stream_id:[eb]}, require_available=True))
    assert instant.decision_ns == 160
    assert len(instant.batch.events) == 2
    assert instant.state.batch_size == 2
    assert set(instant.state.values) == {ea.stream_id, eb.stream_id}


def test_atomic_sibling_route_carries_same_decision_source_health():
    m = _manifest('A', 'a')
    e = BarEvent(m.identity.stream_id, 100, 0, 1,2,.5,1.5,None,'A.csv', available_ns=160, availability_basis='verified_bar_close')
    health = SourceHealthRegistry()
    health.set_policy(e.stream_id, SourceSLOPolicy(max_receive_lag_ns_p95=20))
    health.observe(e, received_ns=170)
    instant = next(ReplayBus().instants({e.stream_id:[e]}, require_available=True))
    plane = health.snapshot(instant.decision_ns)
    assert plane.verify()
    bundle = SiblingInstantRouter().package_instant(
        instant,
        manifests={e.stream_id:m},
        factors={'risk':.2}, topology={}, quality={'coverage':1.0},
        source_health=plane.to_dict(),
    )
    assert bundle.argus['source_health']['plane_hash'] == plane.plane_hash
    assert bundle.athena['source_health']['decision_ns'] == instant.decision_ns
    assert bundle.daedalus['candidate']['source_health']['healthy_fraction'] == 1.0


def test_sibling_route_rejects_health_from_another_decision_time():
    m = _manifest('A', 'a')
    e = BarEvent(m.identity.stream_id, 100, 0, 1,2,.5,1.5,None,'A.csv', available_ns=160, availability_basis='verified_bar_close')
    instant = next(ReplayBus().instants({e.stream_id:[e]}, require_available=True))
    import pytest
    with pytest.raises(ValueError, match='source_health decision_ns'):
        SiblingInstantRouter().package_instant(
            instant, manifests={e.stream_id:m}, factors={}, topology={}, quality={},
            source_health={'decision_ns':159},
        )
