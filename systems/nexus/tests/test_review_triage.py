import hashlib
import json

from nexus.review_triage import (
    build_representation_review_triage,
    verify_representation_review_triage,
)


def _sealed_queue(candidates):
    families={}
    for row in candidates:
        family=f"{row.get('venue') or '?'}:{row.get('symbol')}:{row.get('hypothesis_kind')}:{row.get('filename_claim') or '?'}"
        families[family]=families.get(family,0)+1
    body={
        "schema":"nexus.representation-review-queue.v1",
        "candidates":candidates,
        "family_counts":[[k,v] for k,v in sorted(families.items())],
    }
    body["queue_hash"]=hashlib.sha256(
        json.dumps(body,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return body


def _candidate(**overrides):
    row={
        "priority":"P0","priority_score":100,
        "hypothesis_kind":"event_or_transformed_candidate",
        "hypothesis_confidence":0.8,
        "venue":"CME","symbol":"NQ1!","filename_claim":"1",
        "observed_cadence_ns":1_000_000,"cadence_confidence":0.8,
        "quality_flags":["claim_mismatch","fractional_time"],
        "review_reasons":["flag:claim_mismatch"],
        "evidence_required":["vendor definition"],
        "stream_id":"a","source_path":"a.csv","row_count":100,
        "fixed_interval_candidate_ns":None,
        "timestamp_semantics_candidate":"UNKNOWN_REQUIRES_REVIEW",
        "authoritative":False,
    }
    row.update(overrides)
    return row


def test_review_triage_groups_without_auto_resolution():
    rows=[
        _candidate(stream_id="a",source_path="a.csv",symbol="NQ1!"),
        _candidate(stream_id="b",source_path="b.csv",symbol="ES1!"),
        _candidate(
            stream_id="c",source_path="c.csv",
            hypothesis_kind="timeframe_mismatch_candidate",
            filename_claim="2",observed_cadence_ns=3_600_000_000_000,
            quality_flags=["cadence_ambiguous"],
            review_reasons=["hypothesis:timeframe_mismatch_candidate"],
            evidence_required=["export settings"],
        ),
        _candidate(
            stream_id="d",source_path="d.csv",priority="P2",priority_score=10,
            hypothesis_kind="fixed_time_candidate",
        ),
    ]
    out=build_representation_review_triage(_sealed_queue(rows))
    assert out["p0_count"]==3
    assert out["p2_count"]==1
    assert out["triage_class_counts"]["EVENT_DRIVEN_REQUIRES_VENDOR_DEFINITION"]==2
    assert out["triage_class_counts"]["TIMEFRAME_MISMATCH_REQUIRES_EXPORT_SETTING_EVIDENCE"]==1
    assert out["auto_resolved_count"]==0
    assert out["production_authorized"] is False
    assert any(x["stream_count"]==2 for x in out["clusters"])
    assert verify_representation_review_triage(out)


def test_review_triage_rejects_unsealed_or_rehashed_inconsistent_queue():
    import pytest
    row=_candidate()
    with pytest.raises(ValueError,match="tampered"):
        build_representation_review_triage({"candidates":[row]})

    queue=_sealed_queue([row])
    queue["family_counts"]=[["fake",1]]
    queue.pop("queue_hash")
    queue["queue_hash"]=hashlib.sha256(
        json.dumps(
            {k:v for k,v in queue.items() if k!="queue_hash"},
            sort_keys=True,separators=(",",":"),allow_nan=False
        ).encode()
    ).hexdigest()
    with pytest.raises(ValueError,match="tampered"):
        build_representation_review_triage(queue)


def test_review_triage_artifact_is_semantically_tamper_evident():
    row=_candidate()
    out=build_representation_review_triage(_sealed_queue([row]))
    assert verify_representation_review_triage(out)
    forged=dict(out);forged.pop("triage_hash")
    forged["p0_count"]=999
    forged["triage_hash"]=hashlib.sha256(
        json.dumps(forged,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    assert not verify_representation_review_triage(forged)


def test_review_triage_rejects_rehashed_invalid_cluster_identity():
    out=build_representation_review_triage(_sealed_queue([_candidate()]))
    forged=json.loads(json.dumps(out))
    forged["clusters"][0]["stream_ids"]=[""]
    forged.pop("triage_hash")
    forged["triage_hash"]=hashlib.sha256(
        json.dumps(forged,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    assert not verify_representation_review_triage(forged)

    forged=json.loads(json.dumps(out))
    forged["clusters"][0]["symbols"]=["NQ1!","NQ1!"]
    forged.pop("triage_hash")
    forged["triage_hash"]=hashlib.sha256(
        json.dumps(forged,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    assert not verify_representation_review_triage(forged)
