from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from nexus.session_semantics import (
    CME_EQUITY_23X5, CME_CRYPTO_24X7_2026, _assess_gap,
    verify_session_gap_resolution,
)


def _ns(dt):
    return int(dt.astimezone(timezone.utc).timestamp() * 1_000_000_000)


def test_cme_equity_daily_halt_is_session_explained():
    ct = ZoneInfo("America/Chicago")
    # One-minute bars bracketing the recurring 16:00-17:00 CT maintenance halt.
    prev = _ns(datetime(2026, 9, 24, 15, 59, tzinfo=ct))
    nxt = _ns(datetime(2026, 9, 24, 17, 0, tzinfo=ct))
    row = _assess_gap(CME_EQUITY_23X5, prev, nxt, 60_000_000_000)
    assert row.classification == "EXPLAINED_BY_RECURRING_SESSION_CLOSURE"


def test_cme_equity_open_session_gap_is_residual():
    ct = ZoneInfo("America/Chicago")
    prev = _ns(datetime(2026, 9, 24, 10, 0, tzinfo=ct))
    nxt = _ns(datetime(2026, 9, 24, 10, 10, tzinfo=ct))
    row = _assess_gap(CME_EQUITY_23X5, prev, nxt, 60_000_000_000)
    assert row.classification == "RESIDUAL_OPEN_SESSION_GAP"


def test_cme_crypto_profile_rejects_pre_effective_period():
    ct = ZoneInfo("America/Chicago")
    prev = _ns(datetime(2026, 5, 1, 15, 59, tzinfo=ct))
    nxt = _ns(datetime(2026, 5, 1, 17, 0, tzinfo=ct))
    row = _assess_gap(CME_CRYPTO_24X7_2026, prev, nxt, 60_000_000_000)
    assert row.classification == "UNSUPPORTED_PROFILE_EFFECTIVE_PERIOD"


def test_exact_nymex_platinum_and_palladium_profiles_are_registered():
    from nexus.session_semantics import EXACT_PROFILES
    assert EXACT_PROFILES[("NYMEX", "PL1!")].profile_id == "nymex-platinum-pl-23x5"
    assert EXACT_PROFILES[("NYMEX", "PA1!")].profile_id == "nymex-palladium-pa-23x5"


def test_tvc_vix_uses_reviewed_underlying_index_profile_with_provider_wrapper_flag():
    from nexus.session_semantics import EXACT_PROFILES
    p = EXACT_PROFILES[("TVC", "VIX")]
    assert p.profile_id == "cboe-vix-gth-rth"
    assert p.confidence == "UNDERLYING_INDEX_PROFILE_PROVIDER_WRAPPER"
    assert len(p.windows_for_weekday(0)) == 2


def test_bzx_long_rth_only_export_fingerprint_can_resolve_representation_session():
    from datetime import datetime, timedelta, timezone
    from zoneinfo import ZoneInfo
    from nexus.session_semantics import _infer_bzx_export_profile
    tz = ZoneInfo("America/New_York")
    times = []
    day = datetime(2025, 1, 6, 9, 30, tzinfo=tz)
    emitted_days = 0
    while emitted_days < 110:
        if day.weekday() < 5:
            for hour in range(7):
                dt = day + timedelta(hours=hour)
                times.append(int(dt.astimezone(timezone.utc).timestamp() * 1_000_000_000))
            emitted_days += 1
        day += timedelta(days=1)
    profile, status, reason = _infer_bzx_export_profile(times)
    assert profile is not None
    assert profile.profile_id == "cboe-bzx-rth"
    assert status == "OBSERVED_EXPORT_RTH_FINGERPRINT_SUPPORT_ONLY"
    assert "support evidence only" in reason


def test_bzx_out_of_rth_rows_directly_attest_extended_export():
    from datetime import datetime, timedelta, timezone
    from zoneinfo import ZoneInfo
    from nexus.session_semantics import _infer_bzx_export_profile
    tz = ZoneInfo("America/New_York")
    times = []
    day = datetime(2025, 1, 6, 8, 0, tzinfo=tz)
    emitted_days = 0
    while emitted_days < 110:
        if day.weekday() < 5:
            for hour in range(10):
                dt = day + timedelta(hours=hour)
                times.append(int(dt.astimezone(timezone.utc).timestamp() * 1_000_000_000))
            emitted_days += 1
        day += timedelta(days=1)
    profile, status, _ = _infer_bzx_export_profile(times)
    assert profile is not None
    assert profile.profile_id == "cboe-bzx-extended"
    assert status == "OBSERVED_EXPORT_EXTENDED_SESSION_DIRECTLY_ATTESTED"


def test_reviewed_frozen_wrapper_and_lse_mag7_profiles_are_registered():
    from nexus.session_semantics import EXACT_PROFILES

    dxy = EXACT_PROFILES[("TVC", "DXY")]
    tnx = EXACT_PROFILES[("TVC", "TNX")]
    mag7 = EXACT_PROFILES[("LSE", "MAG7")]

    assert dxy.confidence == "FROZEN_EXPORT_SUPPORT_PROFILE"
    assert tnx.confidence == "FROZEN_EXPORT_SUPPORT_PROFILE"
    assert mag7.confidence == "EXACT_CONTRACT_OR_INDEX"
    assert mag7.timezone_name == "Europe/London"
    assert mag7.windows_for_weekday(0)[0].start_minute == 8 * 60
    assert mag7.windows_for_weekday(0)[0].end_minute == 16 * 60 + 30
    assert tnx.windows_for_weekday(0)[0].start_minute == 8 * 60 + 20
    assert tnx.windows_for_weekday(0)[0].end_minute == 15 * 60


def test_cme_daily_gap_can_be_resolved_by_weekend_holiday_and_sibling_evidence():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from nexus.session_semantics import CME_EQUITY_23X5, _assess_cme_equity_daily_gap, _ns_from_local

    tz = ZoneInfo("America/Chicago")
    # Labor-Day pattern: Sunday daily anchor -> Tuesday daily anchor, while the
    # finer sibling directly shows Monday 17:00 CT trading for the next trade date.
    a = _ns_from_local(datetime(2025, 8, 31, 17, 0, tzinfo=tz))
    b = _ns_from_local(datetime(2025, 9, 2, 17, 0, tzinfo=tz))
    sibling = [
        _ns_from_local(datetime(2025, 9, 1, 17, 0, tzinfo=tz)),
        _ns_from_local(datetime(2025, 9, 1, 19, 0, tzinfo=tz)),
        _ns_from_local(datetime(2025, 9, 1, 21, 0, tzinfo=tz)),
    ]
    out = _assess_cme_equity_daily_gap(CME_EQUITY_23X5, a, b, sibling)
    assert out.classification == "COARSE_BAR_AGGREGATION_SESSION_SEMANTICS_RESOLVED"


def test_cme_daily_gap_stays_blocked_without_holiday_or_sibling_evidence():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from nexus.session_semantics import CME_EQUITY_23X5, _assess_cme_equity_daily_gap, _ns_from_local

    tz = ZoneInfo("America/Chicago")
    a = _ns_from_local(datetime(2026, 8, 2, 17, 0, tzinfo=tz))
    b = _ns_from_local(datetime(2026, 8, 4, 17, 0, tzinfo=tz))
    out = _assess_cme_equity_daily_gap(CME_EQUITY_23X5, a, b, [])
    assert out.classification == "COARSE_BAR_CALENDAR_REVIEW_REQUIRED"


def test_session_profile_rejects_invalid_calendar_geometry():
    import pytest
    from nexus.session_semantics import DailyWindow, SessionProfile
    with pytest.raises(TypeError,match='integers'):
        DailyWindow(1.5,10)
    with pytest.raises(ValueError,match='timezone'):
        SessionProfile(
            'x','Not/AZone',((0,(DailyWindow(0,10),)),),
            'authority','summary',
        )
    with pytest.raises(ValueError,match='non-overlapping'):
        SessionProfile(
            'x','UTC',((0,(DailyWindow(0,10),DailyWindow(5,20))),),
            'authority','summary',
        )
    with pytest.raises(ValueError,match='effective_end_ns'):
        SessionProfile(
            'x','UTC',((0,(DailyWindow(0,10),)),),
            'authority','summary',effective_start_ns=20,effective_end_ns=10,
        )


def test_session_resolution_verifier_rejects_rehashed_impossible_counts():
    import hashlib,json
    body={
        "schema":"nexus.session-gap-resolution.v1",
        "candidate_count":1,
        "session_semantics_resolved_count":1,
        "residual_diagnostic_count":0,
        "still_session_blocked_count":0,
        "resolutions":[{
            "candidate_id":"x","stream_id":"s","venue":"CME","symbol":"NQ1!",
            "profile_id":"p","profile_status":"EXACT_PROFILE_REVIEWED",
            "gap_count":1,"session_explained_gap_count":1,
            "residual_open_session_gap_count":0,
            "unsupported_effective_period_gap_count":0,
            "coarse_calendar_gap_count":0,
            "session_semantics_resolved":True,
            "residual_data_quality_diagnostic_required":False,
            "reason":"x","evidence_authority":"CME","evidence_summary":"reviewed",
            "gap_assessments":[{
                "previous_event_ns":10,"next_event_ns":20,"gap_ns":10,
                "classification":"EXPLAINED_BY_RECURRING_SESSION_CLOSURE",
            }],
            "coarse_resolution_method":None,"coarse_evidence_stream_id":None,
        }],
        "data_loss_asserted":False,"production_authorized":False,
    }
    body["resolution_hash"]=hashlib.sha256(
        json.dumps(body,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    assert verify_session_gap_resolution(body)

    broken=dict(body); rows=[dict(x) for x in broken["resolutions"]]
    rows[0]["session_explained_gap_count"]=0
    broken["resolutions"]=rows;broken.pop("resolution_hash")
    broken["resolution_hash"]=hashlib.sha256(
        json.dumps(broken,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    assert not verify_session_gap_resolution(broken)


def test_session_time_parser_rejects_nonfinite_negative_and_subnanosecond_values():
    from nexus.session_semantics import _to_event_ns
    assert _to_event_ns("100.25") == 100_250_000_000
    assert _to_event_ns("-1") is None
    assert _to_event_ns("NaN") is None
    assert _to_event_ns("Infinity") is None
    assert _to_event_ns("1.0000000001") is None


def test_session_resolution_rejects_stream_collisions_and_duplicate_candidate_ids(tmp_path):
    import pytest
    from nexus.contracts import StreamIdentity, StreamManifest
    from nexus.session_semantics import build_session_gap_resolution

    def m(raw, path):
        ident=StreamIdentity("src","CME","NQ1!","20",source_path=path,raw_sha256=raw)
        return StreamManifest(ident,10,["time","open","high","low","close"],1,10,1_200_000_000_000,1.0,0,0,0)

    a=m("a"*64,"a.csv")
    b=m("b"*64,"b.csv")
    candidate={"candidate_id":"gap","family":"sampling_gap_sensitivity","scope":[a.identity.stream_id]}
    with pytest.raises(ValueError,match="stream_id collision"):
        build_session_gap_resolution(tmp_path,[a,b],[candidate])

    one=m("a"*64,"a.csv")
    with pytest.raises(ValueError,match="candidate_id"):
        build_session_gap_resolution(tmp_path,[one],[candidate,dict(candidate)])
