from nexus.clock import ClockPolicyError, RepresentationClockRule
from nexus.contracts import StreamIdentity, StreamManifest, BarEvent
from nexus.integrity import IntegrityPolicy, assess_manifest, partition_by_integrity
from nexus.lattice import MultiResolutionClockLattice


def manifest(*, sid="X", cadence=60, flags=(), metadata=None):
    i=StreamIdentity("csv","X",sid,"1","csv_export",f"{sid}.csv",sid.lower()*64 if len(sid)==1 else "a"*64)
    return StreamManifest(i,100,["time","open","high","low","close"],0,6000,cadence,1.0,0,0,0,None,list(flags),metadata or {"usable_ohlc_rows":100})


def test_integrity_gate_preserves_but_rejects_bad_streams():
    good=manifest()
    bad=manifest(sid="Y",flags=("duplicate_header",),metadata={"usable_ohlc_rows":100})
    assert assess_manifest(good).admitted
    a=assess_manifest(bad)
    assert not a.admitted and "duplicate_header" in a.blockers
    admitted,rejected=partition_by_integrity([good,bad])
    assert [m.identity.symbol for m in admitted]==["X"]
    assert len(rejected)==1


def test_integrity_threshold_is_explicit_not_silent():
    m=manifest(metadata={"usable_ohlc_rows":99,"inconsistent_ohlc_rows":1})
    assert not assess_manifest(m).admitted
    relaxed=IntegrityPolicy(max_inconsistent_ohlc_rate=.02)
    assert assess_manifest(m,relaxed).admitted


def test_clock_lattice_keeps_event_stream_native():
    time_m=manifest(sid="T",cadence=60_000_000_000)
    event_m=manifest(sid="E",cadence=7_000_000_000,flags=("fractional_time",))
    lat=MultiResolutionClockLattice()
    lat.register(time_m,"time:1m",rule=RepresentationClockRule("time:1m","open","manifest",reviewed=True))
    lat.register(event_m,"event:renko",rule=RepresentationClockRule("event:renko","event","variable",reviewed=True))
    assert lat.visible_ns(time_m.identity.stream_id,100)==60_000_000_100
    assert lat.visible_ns(event_m.identity.stream_id,123)==123
    events=[
        BarEvent(time_m.identity.stream_id,100,0,1,2,0,1.5,None,"T.csv"),
        BarEvent(event_m.identity.stream_id,123,0,1,2,0,1.5,None,"E.csv"),
    ]
    assert lat.native_boundaries(events)==(123,60_000_000_100)


def test_clock_lattice_refuses_unreviewed_semantics():
    m=manifest()
    lat=MultiResolutionClockLattice()
    try:
        lat.register(m,"unknown",rule=RepresentationClockRule("unknown","unknown",reviewed=False))
    except ClockPolicyError:
        pass
    else:
        raise AssertionError("unreviewed clock semantics must not be admitted")


def test_clock_rule_rejects_invalid_configuration():
    import pytest
    with pytest.raises(ClockPolicyError,match='availability_delay_ns'):
        RepresentationClockRule('x','close',availability_delay_ns=-1)
    with pytest.raises(ClockPolicyError,match='explicit cadence_mode'):
        RepresentationClockRule('x','close','explicit',reviewed=True)
    with pytest.raises(ClockPolicyError,match='variable cadence'):
        RepresentationClockRule('x','open','variable',reviewed=True)
    with pytest.raises(ClockPolicyError,match='timestamp_semantics'):
        RepresentationClockRule('x','future',reviewed=True)
