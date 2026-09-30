import hashlib
import json

from nexus.session_semantics import build_session_semantic_blocker_report


def _assessment(i, classification):
    a=10+i*20
    b=a+10
    return {
        "previous_event_ns":a,
        "next_event_ns":b,
        "gap_ns":10,
        "classification":classification,
    }


def _row(
    candidate_id,stream_id,venue,symbol,profile_status,gap_count,
    *,coarse=0,resolved=False,explained=0,
):
    assessments=[]
    assessments += [_assessment(i,"COARSE_BAR_CALENDAR_REVIEW_REQUIRED") for i in range(coarse)]
    assessments += [
        _assessment(coarse+i,"EXPLAINED_BY_RECURRING_SESSION_CLOSURE")
        for i in range(explained)
    ]
    return {
        "candidate_id":candidate_id,
        "stream_id":stream_id,
        "venue":venue,
        "symbol":symbol,
        "profile_id":"reviewed-profile" if resolved else None,
        "profile_status":profile_status,
        "gap_count":gap_count,
        "session_explained_gap_count":explained,
        "residual_open_session_gap_count":0,
        "unsupported_effective_period_gap_count":0,
        "coarse_calendar_gap_count":coarse,
        "session_semantics_resolved":resolved,
        "residual_data_quality_diagnostic_required":False,
        "reason":"reviewed" if resolved else "blocked",
        "evidence_authority":"authority" if resolved else None,
        "evidence_summary":"summary" if resolved else None,
        "gap_assessments":assessments,
        "coarse_resolution_method":None,
        "coarse_evidence_stream_id":None,
    }


def _seal(rows):
    body={
        "schema":"nexus.session-gap-resolution.v1",
        "candidate_count":len(rows),
        "session_semantics_resolved_count":sum(bool(r["session_semantics_resolved"]) for r in rows),
        "residual_diagnostic_count":sum(bool(r["residual_data_quality_diagnostic_required"]) for r in rows),
        "still_session_blocked_count":sum(not bool(r["session_semantics_resolved"]) for r in rows),
        "resolutions":rows,
        "data_loss_asserted":False,
        "production_authorized":False,
    }
    body["resolution_hash"]=hashlib.sha256(
        json.dumps(body,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return body


def test_blocker_report_separates_coarse_provider_wrapper_and_symbol_identity():
    rows=[
        _row("coarse","s1","CME","ES1!","EXACT_PROFILE_REVIEWED",5,coarse=5),
        _row("tvc","s2","TVC","DXY","NO_REVIEWED_PROFILE",8),
        _row("lse","s3","LSE","MAG7","NO_REVIEWED_PROFILE",9),
        _row("done","s4","CME","NQ1!","EXACT_PROFILE_REVIEWED",1,resolved=True,explained=1),
    ]
    out=build_session_semantic_blocker_report(_seal(rows))
    assert out["unresolved_candidate_count"]==3
    assert out["blocker_class_counts"]=={
        "COARSE_BAR_HOLIDAY_AGGREGATION_SEMANTICS":1,
        "PROVIDER_WRAPPER_UNDERLYING_SESSION_IDENTITY":1,
        "SYMBOL_VENUE_CONTRACT_IDENTITY":1,
    }
    assert all(row["production_authorized"] is False for row in out["blockers"])
