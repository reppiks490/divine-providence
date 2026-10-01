from pathlib import Path
import json
import pytest

from nexus.review_registry import ReviewedRepresentationRecord,ReviewedRepresentationRegistry


def _record(**kw):
    base=dict(stream_id='csv:NQ:abc',version='1',canonical_instrument='NQ',asset_class='futures',representation_class='time-1m',kind='time_bar',timestamp_semantics='bar_open',fixed_interval_ns=60_000_000_000,review_evidence_sha256='a'*64,reviewed_by='human-review')
    base.update(kw);return ReviewedRepresentationRecord(**base)


def test_reviewed_registry_is_versioned_immutable_and_not_auto_active(tmp_path:Path):
    reg=ReviewedRepresentationRegistry();r=_record();reg.register(r)
    assert reg.get(r.stream_id) is None
    reg.activate(r.stream_id,'1')
    got=reg.get(r.stream_id);assert got==r
    assert got.representation_policy().reviewed
    assert got.identity_record().timestamp_semantics=='bar_open'
    p=tmp_path/'registry.json';reg.save(p);re=ReviewedRepresentationRegistry.load(p)
    assert re.get(r.stream_id).record_hash==r.record_hash


def test_reviewed_registry_rejects_semantic_fiction_and_unreviewed_execution():
    with pytest.raises(ValueError,match='event bars'):
        _record(kind='event_bar',timestamp_semantics='event_completion',fixed_interval_ns=60_000_000_000)
    with pytest.raises(ValueError,match='execution-safe'):
        _record(timestamp_semantics='unknown',fixed_interval_ns=None,executable=True)


def test_registry_detects_tampering_and_reports_unresolved(tmp_path:Path):
    reg=ReviewedRepresentationRegistry();r=_record();reg.register(r);reg.activate(r.stream_id,'1')
    assert reg.unresolved([r.stream_id,'x','y'])==('x','y')
    p=tmp_path/'registry.json';reg.save(p);body=json.loads(p.read_text());body['active'][r.stream_id]='999';p.write_text(json.dumps(body))
    with pytest.raises(ValueError,match='hash mismatch'):
        ReviewedRepresentationRegistry.load(p)


def test_reviewed_execution_record_is_self_consistent():
    with pytest.raises(ValueError,match='requires venue'):
        _record(executable=True)
    with pytest.raises(ValueError,match='roll_policy'):
        _record(executable=True,venue='CME',continuous_contract=True)
    good=_record(
        executable=True,venue='CME',continuous_contract=True,
        roll_policy='reviewed-front-roll',
    )
    identity=good.identity_record()
    assert identity.executable is True
    assert identity.venue=='CME'
    assert identity.roll_policy=='reviewed-front-roll'


def test_reviewed_record_rejects_invalid_policy_types():
    with pytest.raises(ValueError,match='availability_delay_ns'):
        _record(availability_delay_ns=-1)
    with pytest.raises(ValueError,match='fixed_interval_ns'):
        _record(fixed_interval_ns=1.5)
    with pytest.raises(TypeError,match='bool'):
        _record(executable=1)
    with pytest.raises(ValueError,match='trimmed'):
        _record(reviewed_by=' reviewer ')


def test_reviewed_record_rejects_invalid_semantic_metadata():
    with pytest.raises(ValueError,match='invalid timezone'):
        _record(timezone='Mars/Chicago')
    with pytest.raises(ValueError,match='venue'):
        _record(venue=' CME ')
    with pytest.raises(ValueError,match='roll_policy'):
        _record(roll_policy=' x ')
    with pytest.raises(ValueError,match='volume_semantics'):
        _record(volume_semantics='')
    with pytest.raises(TypeError,match='record'):
        ReviewedRepresentationRegistry().register(object())


def test_structured_model_identity_requires_exact_bytes_and_all_axes():
    with pytest.raises(ValueError,match='raw_sha256'):
        _record(
            chart_view_family='regular_candles',
            price_geometry='standard_ohlc',
            sampling_domain='time',
            sampling_construction='time_bar',
        )
    with pytest.raises(ValueError,match='structured model identity'):
        _record(
            raw_sha256='b'*64,
            chart_view_family='regular_candles',
            price_geometry='standard_ohlc',
            sampling_domain='time',
        )
    with pytest.raises(ValueError,match='raw_sha256'):
        _record(raw_sha256='bad')
