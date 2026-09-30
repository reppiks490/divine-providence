from nexus.contracts import BarEvent
from nexus.source_health import SourceHealthTracker, SourceSLOPolicy


def _e(seq:int, *, avail:int|None, revision:int=0):
    return BarEvent('s',100+seq,seq,1,2,.5,1.5,None,'x.csv',available_ns=avail,revision=revision,availability_basis='observed_receipt' if avail is not None else 'unknown')


def test_source_health_tracks_only_observable_receive_lag_and_gaps():
    h=SourceHealthTracker('s',lag_window=8)
    h.observe(_e(0,avail=100),received_ns=110,clock_uncertainty_ns=2)
    h.observe(_e(1,avail=None),received_ns=120,clock_uncertainty_ns=3)
    h.observe(_e(4,avail=140,revision=1),received_ns=180,clock_uncertainty_ns=7)
    snap=h.snapshot()
    assert snap.samples==3
    assert snap.receive_lag_samples==2
    assert snap.availability_unknown_samples==1
    assert snap.sequence_gap_runs==1 and snap.missing_sequence_slots==2 and snap.longest_gap==2
    assert snap.revision_events==1 and snap.revision_rate==1/3
    assert snap.clock_uncertainty_ns_max==7


def test_reconnect_epochs_and_slo_fail_closed_on_missing_lag_evidence():
    h=SourceHealthTracker('s')
    h.set_connected(False); h.set_connected(True)
    h.observe(_e(0,avail=None),received_ns=200)
    p=SourceSLOPolicy(max_receive_lag_ns_p95=10,max_gap_size=0,max_reconnect_epochs=0,min_lag_samples=1)
    snap=h.snapshot(p)
    assert snap.reconnect_epochs==1
    assert snap.slo_passed is False
    assert 'receive_lag_insufficient_evidence' in snap.slo_failures
    assert 'reconnect_epochs' in snap.slo_failures


def test_source_slo_pass_and_fail_dimensions_are_deterministic():
    h=SourceHealthTracker('s')
    h.observe(_e(0,avail=100),received_ns=105)
    h.observe(_e(1,avail=110),received_ns=117)
    ok=h.snapshot(SourceSLOPolicy(max_receive_lag_ns_p95=10,max_gap_size=0,max_clock_uncertainty_ns=0))
    assert ok.slo_passed is True
    bad=h.snapshot(SourceSLOPolicy(max_receive_lag_ns_p95=6,max_gap_size=0))
    assert bad.slo_passed is False and bad.slo_failures==('receive_lag_p95',)


def test_source_health_registry_builds_fleet_plane_without_assuming_unconfigured_slo():
    from nexus.source_health import SourceHealthRegistry
    r=SourceHealthRegistry()
    r.set_policy('s',SourceSLOPolicy(max_receive_lag_ns_p95=10,max_gap_size=0))
    r.observe(_e(0,avail=100),received_ns=105)
    r.observe(BarEvent('u',101,0,1,2,.5,1.5,None,'u.csv',available_ns=100,availability_basis='observed_receipt'),received_ns=101)
    plane=r.snapshot(110)
    assert plane.healthy_fraction==1.0
    assert plane.failed_streams==()
    assert plane.unknown_slo_streams==('u',)


def test_source_slo_does_not_mask_impossible_time_as_zero_lag():
    h=SourceHealthTracker('s')
    # Event cannot be known before it occurs, and NEXUS cannot receive it before its
    # own asserted availability. Neither observation is admitted into lag samples.
    bad=BarEvent('s',100,0,1,2,.5,1.5,None,'x.csv',available_ns=90,availability_basis='observed_receipt')
    h.observe(bad,received_ns=80)
    snap=h.snapshot(SourceSLOPolicy(max_receive_lag_ns_p95=None))
    assert snap.receive_lag_samples==0
    assert snap.availability_before_event_samples==1
    assert snap.receipt_before_available_samples==1
    assert snap.slo_passed is False
    assert snap.slo_failures==('impossible_time_evidence',)


def test_source_slo_tracks_out_of_order_receipt_and_nonmonotone_sequence():
    h=SourceHealthTracker('s')
    h.observe(_e(1,avail=101),received_ns=110)
    h.observe(_e(0,avail=100),received_ns=109)
    snap=h.snapshot(SourceSLOPolicy(max_receive_lag_ns_p95=None,max_gap_size=None))
    assert snap.out_of_order_receipts==1
    assert snap.sequence_nonmonotone_events==1
    assert snap.slo_passed is False
    assert snap.slo_failures==('out_of_order_receipts','sequence_nonmonotone')


def test_source_health_flags_availability_and_receipt_clock_violations():
    h=SourceHealthTracker('s')
    bad=BarEvent('s',100,0,1,2,.5,1.5,None,'x.csv',available_ns=90,availability_basis='verified_bar_close')
    h.observe(bad,received_ns=80)
    snap=h.snapshot(SourceSLOPolicy())
    assert snap.availability_before_event_samples==1
    assert snap.receipt_before_available_samples==1
    assert snap.impossible_time_samples==2
    assert snap.slo_passed is False
    assert 'impossible_time_evidence' in snap.slo_failures


def test_source_health_flags_out_of_order_receipts():
    h=SourceHealthTracker('s')
    h.observe(_e(0,avail=100),received_ns=120)
    h.observe(_e(1,avail=110),received_ns=115)
    snap=h.snapshot(SourceSLOPolicy(max_out_of_order_receipts=0))
    assert snap.out_of_order_receipts==1
    assert 'out_of_order_receipts' in snap.slo_failures


def test_source_health_plane_has_deterministic_aion_context_identity():
    from nexus.adapters import aion_source_health_spec, aion_source_health_observation
    from nexus.source_health import SourceHealthRegistry
    r=SourceHealthRegistry(); r.set_policy('s',SourceSLOPolicy(max_receive_lag_ns_p95=10,max_gap_size=0)); r.observe(_e(0,avail=100),received_ns=105)
    plane=r.snapshot(110)
    spec=aion_source_health_spec(plane_hash=plane.plane_hash)
    obs=aion_source_health_observation(plane,ingested_ns=120)
    assert spec['capabilities']==['context'] and spec['max_evidence_tier']==1
    assert len(spec['source_sha256'])==64 and spec['source_id']==obs['source_id']
    assert obs['payload']['plane_hash']==plane.plane_hash
    assert obs['event_ns']==110==obs['available_ns'] and obs['ingested_ns']==120
    assert obs['evidence_tier']==1 and obs['quality_flags']==['nexus_source_health']


def test_source_health_plane_rejects_rewind_lookahead():
    import pytest
    from nexus.source_health import SourceHealthRegistry
    r=SourceHealthRegistry()
    r.observe(_e(0,avail=100),received_ns=120)
    with pytest.raises(ValueError,match='cannot build source-health plane'):
        r.snapshot(110)
    assert r.snapshot(120).decision_ns==120


def test_serialized_health_plane_requires_hash_and_semantic_consistency():
    from nexus.source_health import SourceHealthRegistry, SourceHealthPlane
    r=SourceHealthRegistry()
    r.set_policy('s',SourceSLOPolicy(max_receive_lag_ns_p95=10,max_gap_size=0))
    r.observe(_e(0,avail=100),received_ns=105)
    plane=r.snapshot(110)
    restored=SourceHealthPlane.from_dict(plane.to_dict())
    assert restored.verify()

    tampered=plane.to_dict()
    tampered['healthy_fraction']=0.0
    assert not SourceHealthPlane.from_dict(tampered).verify()

    inconsistent=plane.to_dict()
    inconsistent['healthy_streams']=[]
    inconsistent['failed_streams']=['s']
    assert not SourceHealthPlane.from_dict(inconsistent).verify()


def test_source_slo_policy_change_requires_explicit_clear():
    import pytest
    from nexus.source_health import SourceHealthRegistry
    r=SourceHealthRegistry()
    p1=SourceSLOPolicy(max_gap_size=0)
    p2=SourceSLOPolicy(max_gap_size=2)
    r.set_policy('s',p1)
    r.set_policy('s',p1)
    with pytest.raises(ValueError,match='policy conflict'):
        r.set_policy('s',p2)
    r.clear_policy('s')
    r.set_policy('s',p2)


def test_source_health_missing_receipt_cannot_erase_future_evidence():
    import pytest
    from nexus.source_health import SourceHealthRegistry
    r=SourceHealthRegistry()
    r.observe(_e(0,avail=100),received_ns=200)
    # A later tracker update without a receipt must not erase the fact that
    # evidence at t=200 was already consumed.
    r.observe(_e(1,avail=150),received_ns=None)
    snap=r.tracker('s').snapshot()
    assert snap.last_received_ns==200
    assert snap.latest_evidence_ns==200
    with pytest.raises(ValueError,match='cannot build source-health plane'):
        r.snapshot(160)
    assert r.snapshot(200).decision_ns==200


def test_source_health_receipt_order_survives_missing_receipt_sample():
    h=SourceHealthTracker('s')
    h.observe(_e(0,avail=100),received_ns=200)
    h.observe(_e(1,avail=110),received_ns=None)
    h.observe(_e(2,avail=120),received_ns=190)
    snap=h.snapshot(SourceSLOPolicy(max_receive_lag_ns_p95=None))
    assert snap.out_of_order_receipts==1
