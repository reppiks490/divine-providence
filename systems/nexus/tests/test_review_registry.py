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
    with pytest.raises(ValueError,match='event-driven'):
        _record(kind='event_bar',timestamp_semantics='event_completion',fixed_interval_ns=60_000_000_000)
    with pytest.raises(ValueError,match='execution-safe'):
        _record(timestamp_semantics='unknown',fixed_interval_ns=None,executable=True)


def test_registry_detects_tampering_and_reports_unresolved(tmp_path:Path):
    reg=ReviewedRepresentationRegistry();r=_record();reg.register(r);reg.activate(r.stream_id,'1')
    assert reg.unresolved([r.stream_id,'x','y'])==('x','y')
    p=tmp_path/'registry.json';reg.save(p);body=json.loads(p.read_text());body['active'][r.stream_id]='999';p.write_text(json.dumps(body))
    with pytest.raises(ValueError,match='hash mismatch'):
        ReviewedRepresentationRegistry.load(p)
