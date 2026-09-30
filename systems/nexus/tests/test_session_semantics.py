from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from nexus.session_semantics import CME_EQUITY_23X5, CME_CRYPTO_24X7_2026, _assess_gap


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
    assert status == "OBSERVED_EXPORT_RTH_FINGERPRINT_REVIEWED"
    assert "frozen export" in reason


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
