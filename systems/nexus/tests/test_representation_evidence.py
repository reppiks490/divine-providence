import hashlib
import json

from nexus.representation_evidence import (
    build_representation_source_evidence,
    tradingview_timeframe_seconds,
    verify_representation_source_evidence,
)


def _seal_triage(clusters):
    counts={}
    total=0
    for row in clusters:
        cls=row["triage_class"]
        counts[cls]=counts.get(cls,0)+row["stream_count"]
        total+=row["stream_count"]
    body={
        "schema":"nexus.representation-review-triage.v1",
        "p0_count":total,
        "p2_count":0,
        "triage_class_counts":dict(sorted(counts.items())),
        "review_reason_counts":{},
        "evidence_requirement_counts":{},
        "cluster_count":len(clusters),
        "clusters":clusters,
        "authoritative_resolution_required":True,
        "auto_resolved_count":0,
        "production_authorized":False,
    }
    body["triage_hash"]=hashlib.sha256(
        json.dumps(body,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return body


def test_tradingview_timeframe_parser_uses_reviewed_syntax():
    assert tradingview_timeframe_seconds("1S")==1
    assert tradingview_timeframe_seconds("10S")==10
    assert tradingview_timeframe_seconds("30S")==30
    assert tradingview_timeframe_seconds("1")==60
    assert tradingview_timeframe_seconds("240")==14_400
    assert tradingview_timeframe_seconds("60")==3_600
    assert tradingview_timeframe_seconds("1H") is None
    assert tradingview_timeframe_seconds("2S") is None


def test_source_evidence_separates_cadence_compatibility_without_resolution():
    clusters=[
        {
            "triage_class":"FIXED_TIME_CADENCE_MATCH_REQUIRES_EXPORT_PROVENANCE",
            "venue":"CME","symbols":["NQ1!"],"stream_ids":["a","b"],
            "stream_count":2,"filename_claim":"1S",
            "observed_cadence_ns":1_000_000_000,
            "quality_flags":[],"authoritative_resolution_required":True,
            "auto_resolved":False,
        },
        {
            "triage_class":"EVENT_DRIVEN_REQUIRES_VENDOR_DEFINITION",
            "venue":"CME","symbols":["NQ1!"],"stream_ids":["c"],
            "stream_count":1,"filename_claim":"1",
            "observed_cadence_ns":1_000_000,
            "quality_flags":[],"authoritative_resolution_required":True,
            "auto_resolved":False,
        },
    ]
    out=build_representation_source_evidence(_seal_triage(clusters))
    assert out["p0_stream_count"]==3
    assert out["standard_timeframe_cadence_compatible_stream_count"]==2
    assert out["standard_timeframe_cadence_incompatible_stream_count"]==1
    assert out["auto_resolved_count"]==0
    assert out["production_authorized"] is False
    assert verify_representation_source_evidence(out)
    exact=next(x for x in out["clusters"] if x["stream_ids"]==["a","b"])
    assert exact["claim_vs_observed"]=="EXACT_CADENCE_MATCH"
    assert exact["remaining_p0"] is True
    mismatch=next(x for x in out["clusters"] if x["stream_ids"]==["c"])
    assert mismatch["claim_vs_observed"]=="OBSERVED_FASTER_THAN_STANDARD_TIMEFRAME_CLAIM"
    assert mismatch["source_evidence"]["chart_type_standard_time_based"]=="NOT_ATTESTED"


def test_source_evidence_requires_verified_triage_and_detects_semantic_forgery():
    import pytest
    with pytest.raises(ValueError,match="tampered"):
        build_representation_source_evidence({"clusters":[]})

    out=build_representation_source_evidence(_seal_triage([]))
    assert verify_representation_source_evidence(out)
    forged=dict(out);forged.pop("evidence_hash")
    forged["p0_stream_count"]=1
    forged["evidence_hash"]=hashlib.sha256(
        json.dumps(forged,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    assert not verify_representation_source_evidence(forged)


def test_source_evidence_rejects_rehashed_claim_semantic_forgery():
    clusters=[{
        "triage_class":"FIXED_TIME_CADENCE_MATCH_REQUIRES_EXPORT_PROVENANCE",
        "venue":"CME","symbols":["NQ1!"],"stream_ids":["a"],
        "stream_count":1,"filename_claim":"1S",
        "observed_cadence_ns":1_000_000_000,
        "quality_flags":[],"authoritative_resolution_required":True,
        "auto_resolved":False,
    }]
    out=build_representation_source_evidence(_seal_triage(clusters))
    assert verify_representation_source_evidence(out)

    forged=json.loads(json.dumps(out))
    forged["clusters"][0]["source_evidence"]["chart_type_standard_time_based"]="AUTHORITATIVE_SUPPORTED"
    forged.pop("evidence_hash")
    forged["evidence_hash"]=hashlib.sha256(
        json.dumps(forged,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    assert not verify_representation_source_evidence(forged)

    forged=json.loads(json.dumps(out))
    forged["clusters"][0]["standard_time_based_cadence_compatible"]=False
    forged.pop("evidence_hash")
    forged["evidence_hash"]=hashlib.sha256(
        json.dumps(forged,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    assert not verify_representation_source_evidence(forged)
