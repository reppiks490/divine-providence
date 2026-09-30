from __future__ import annotations

import csv
import io
import json
import hashlib
from dataclasses import dataclass, asdict
from datetime import date, datetime, time, timedelta, timezone
from bisect import bisect_left
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Mapping
from zoneinfo import ZoneInfo
import zipfile

from .contracts import StreamManifest


SCHEMA = "nexus.session-gap-resolution.v1"


@dataclass(frozen=True, slots=True)
class DailyWindow:
    start_minute: int
    end_minute: int

    def __post_init__(self) -> None:
        if type(self.start_minute) is not int or type(self.end_minute) is not int:
            raise TypeError("daily-window minutes must be integers")
        if not (0 <= self.start_minute <= 1440 and 0 <= self.end_minute <= 1440):
            raise ValueError("daily-window minutes must lie in [0,1440]")
        if self.end_minute <= self.start_minute:
            raise ValueError("daily-window end must be after start")


@dataclass(frozen=True, slots=True)
class SessionProfile:
    profile_id: str
    timezone_name: str
    weekly_open_windows: tuple[tuple[int, tuple[DailyWindow, ...]], ...]
    evidence_authority: str
    evidence_summary: str
    confidence: str = "EXACT_CONTRACT_OR_INDEX"
    effective_start_ns: int | None = None
    effective_end_ns: int | None = None
    holiday_calendar_complete: bool = False

    def __post_init__(self) -> None:
        for name,value in (
            ("profile_id",self.profile_id),
            ("timezone_name",self.timezone_name),
            ("evidence_authority",self.evidence_authority),
            ("evidence_summary",self.evidence_summary),
            ("confidence",self.confidence),
        ):
            if not isinstance(value,str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        try:
            ZoneInfo(self.timezone_name)
        except Exception as exc:
            raise ValueError(f"invalid session timezone: {self.timezone_name}") from exc
        if type(self.holiday_calendar_complete) is not bool:
            raise TypeError("holiday_calendar_complete must be bool")
        for name,value in (
            ("effective_start_ns",self.effective_start_ns),
            ("effective_end_ns",self.effective_end_ns),
        ):
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"{name} must be a non-negative integer or None")
        if (
            self.effective_start_ns is not None
            and self.effective_end_ns is not None
            and self.effective_end_ns < self.effective_start_ns
        ):
            raise ValueError("session effective_end_ns cannot precede effective_start_ns")
        seen=set()
        for weekday,windows in self.weekly_open_windows:
            if type(weekday) is not int or not 0 <= weekday <= 6:
                raise ValueError("session weekdays must be integers in [0,6]")
            if weekday in seen:
                raise ValueError("session weekdays must be unique")
            seen.add(weekday)
            if not isinstance(windows,tuple) or any(not isinstance(w,DailyWindow) for w in windows):
                raise TypeError("session windows must be tuples of DailyWindow")
            prior_end=None
            for window in windows:
                if prior_end is not None and window.start_minute < prior_end:
                    raise ValueError("session windows must be sorted and non-overlapping")
                prior_end=window.end_minute

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)

    def windows_for_weekday(self, weekday: int) -> tuple[DailyWindow, ...]:
        return dict(self.weekly_open_windows).get(weekday, ())

    def supports_interval(self, start_ns: int, end_ns: int) -> bool:
        if self.effective_start_ns is not None and start_ns < self.effective_start_ns:
            return False
        if self.effective_end_ns is not None and end_ns > self.effective_end_ns:
            return False
        return True


@dataclass(frozen=True, slots=True)
class GapAssessment:
    previous_event_ns: int
    next_event_ns: int
    gap_ns: int
    classification: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SessionGapCandidateResolution:
    candidate_id: str
    stream_id: str | None
    venue: str | None
    symbol: str | None
    profile_id: str | None
    profile_status: str
    gap_count: int
    session_explained_gap_count: int
    residual_open_session_gap_count: int
    unsupported_effective_period_gap_count: int
    coarse_calendar_gap_count: int
    session_semantics_resolved: bool
    residual_data_quality_diagnostic_required: bool
    reason: str
    evidence_authority: str | None
    evidence_summary: str | None
    gap_assessments: tuple[GapAssessment, ...]
    coarse_resolution_method: str | None = None
    coarse_evidence_stream_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["gap_assessments"] = [x.to_dict() for x in self.gap_assessments]
        return d


def _weekly(*rows: tuple[int, tuple[DailyWindow, ...]]) -> tuple[tuple[int, tuple[DailyWindow, ...]], ...]:
    return tuple(sorted(rows))


def _cme_23x5_profile(profile_id: str, authority: str, summary: str, confidence: str = "EXACT_CONTRACT_OR_INDEX") -> SessionProfile:
    full0_16 = (DailyWindow(0, 16 * 60),)
    split = (DailyWindow(0, 16 * 60), DailyWindow(17 * 60, 24 * 60))
    sunday = (DailyWindow(17 * 60, 24 * 60),)
    return SessionProfile(
        profile_id=profile_id,
        timezone_name="America/Chicago",
        weekly_open_windows=_weekly(
            (0, split), (1, split), (2, split), (3, split),
            (4, full0_16), (5, ()), (6, sunday),
        ),
        evidence_authority=authority,
        evidence_summary=summary,
        confidence=confidence,
        holiday_calendar_complete=False,
    )


# Exact profiles use official exchange/index documentation. Holiday/early-close layers
# remain incomplete unless separately attested, so the resolver never equates a midweek
# absence with data loss merely because the recurring weekly session is known.
CME_EQUITY_23X5 = _cme_23x5_profile(
    "cme-equity-index-23x5",
    "CME Group",
    "Equity index futures trade Sunday-Friday 17:00-16:00 CT with a 16:00-17:00 CT daily halt.",
)

COMEX_SILVER_23X5 = _cme_23x5_profile(
    "comex-silver-23x5",
    "CME Group / COMEX",
    "Silver futures trade Sunday-Friday 17:00-16:00 CT with a 60-minute daily break beginning 16:00 CT.",
)

NYMEX_PLATINUM_23X5 = _cme_23x5_profile(
    "nymex-platinum-pl-23x5",
    "CME Group / NYMEX",
    "CME/Nymex materials identify Platinum Futures (PL, Rulebook Chapter 105) and current metals trading hours as Sunday-Friday 17:00-16:00 CT with a 60-minute daily maintenance break beginning 16:00 CT.",
)

NYMEX_PALLADIUM_23X5 = _cme_23x5_profile(
    "nymex-palladium-pa-23x5",
    "CME Group / NYMEX",
    "CME/Nymex materials identify Palladium Futures (PA, Rulebook Chapter 106) and current metals trading hours as Sunday-Friday 17:00-16:00 CT with a 60-minute daily maintenance break beginning 16:00 CT.",
)


def _ns_from_local(dt: datetime) -> int:
    return int(dt.astimezone(timezone.utc).timestamp() * 1_000_000_000)


_crypto_effective = _ns_from_local(datetime(2026, 5, 29, 16, 0, tzinfo=ZoneInfo("America/Chicago")))
CME_CRYPTO_24X7_2026 = SessionProfile(
    profile_id="cme-crypto-24x7-2026-05-29",
    timezone_name="America/Chicago",
    weekly_open_windows=_weekly(
        (0, (DailyWindow(0, 16 * 60), DailyWindow(16 * 60 + 2, 24 * 60))),
        (1, (DailyWindow(0, 16 * 60), DailyWindow(16 * 60 + 2, 24 * 60))),
        (2, (DailyWindow(0, 16 * 60), DailyWindow(16 * 60 + 2, 24 * 60))),
        (3, (DailyWindow(0, 16 * 60), DailyWindow(16 * 60 + 2, 24 * 60))),
        (4, (DailyWindow(0, 16 * 60), DailyWindow(16 * 60 + 2, 24 * 60))),
        (5, (DailyWindow(0, 2 * 60), DailyWindow(4 * 60, 24 * 60))),
        (6, (DailyWindow(0, 24 * 60),)),
    ),
    evidence_authority="CME Group",
    evidence_summary="CME cryptocurrency futures moved to 24/7 trading on 2026-05-29, with 16:00-16:02 CT weekday and 02:00-04:00 CT Saturday maintenance windows.",
    effective_start_ns=_crypto_effective,
    holiday_calendar_complete=True,
)

CBOE_VXN_RTH = SessionProfile(
    profile_id="cboe-vxn-rth",
    timezone_name="America/New_York",
    weekly_open_windows=_weekly(
        (0, (DailyWindow(9 * 60 + 31, 16 * 60 + 15),)),
        (1, (DailyWindow(9 * 60 + 31, 16 * 60 + 15),)),
        (2, (DailyWindow(9 * 60 + 31, 16 * 60 + 15),)),
        (3, (DailyWindow(9 * 60 + 31, 16 * 60 + 15),)),
        (4, (DailyWindow(9 * 60 + 31, 16 * 60 + 15),)),
        (5, ()), (6, ()),
    ),
    evidence_authority="Cboe",
    evidence_summary="Cboe VXN methodology lists RTH dissemination approximately 09:31-16:15 ET on Cboe business days.",
    holiday_calendar_complete=False,
)

CBOE_VIX_GTH_RTH = SessionProfile(
    profile_id="cboe-vix-gth-rth",
    timezone_name="America/New_York",
    weekly_open_windows=_weekly(
        (0, (DailyWindow(3 * 60 + 15, 9 * 60 + 25), DailyWindow(9 * 60 + 30, 16 * 60 + 16))),
        (1, (DailyWindow(3 * 60 + 15, 9 * 60 + 25), DailyWindow(9 * 60 + 30, 16 * 60 + 16))),
        (2, (DailyWindow(3 * 60 + 15, 9 * 60 + 25), DailyWindow(9 * 60 + 30, 16 * 60 + 16))),
        (3, (DailyWindow(3 * 60 + 15, 9 * 60 + 25), DailyWindow(9 * 60 + 30, 16 * 60 + 16))),
        (4, (DailyWindow(3 * 60 + 15, 9 * 60 + 25), DailyWindow(9 * 60 + 30, 16 * 60 + 16))),
        (5, ()), (6, ()),
    ),
    evidence_authority="Cboe",
    evidence_summary="Cboe VIX methodology/FAQ specifies GTH calculation roughly 03:15-09:25 ET and RTH calculation roughly 09:30-16:15 ET on Cboe business days; the TVC wrapper is therefore checked against the underlying index schedule, not assumed to be an exchange feed.",
    confidence="UNDERLYING_INDEX_PROFILE_PROVIDER_WRAPPER",
    holiday_calendar_complete=False,
)

BITSTAMP_CRYPTO_24X7 = SessionProfile(
    profile_id="bitstamp-crypto-24x7",
    timezone_name="UTC",
    weekly_open_windows=_weekly(*[(i, (DailyWindow(0, 24 * 60),)) for i in range(7)]),
    evidence_authority="Bitstamp",
    evidence_summary="Bitstamp describes cryptocurrency markets/trading access as 24/7; no recurring exchange-session closure is assumed here.",
    holiday_calendar_complete=True,
)

BZX_REGULAR = SessionProfile(
    profile_id="cboe-bzx-rth",
    timezone_name="America/New_York",
    weekly_open_windows=_weekly(*[(i, (DailyWindow(9 * 60 + 30, 16 * 60),)) for i in range(5)], (5, ()), (6, ())),
    evidence_authority="Cboe BZX",
    evidence_summary="Cboe BZX regular session is 09:30-16:00 ET.",
    confidence="POSSIBLE_CHART_SESSION",
    holiday_calendar_complete=False,
)
BZX_EXTENDED = SessionProfile(
    profile_id="cboe-bzx-extended",
    timezone_name="America/New_York",
    weekly_open_windows=_weekly(*[(i, (DailyWindow(4 * 60, 20 * 60),)) for i in range(5)], (5, ()), (6, ())),
    evidence_authority="Cboe BZX",
    evidence_summary="Cboe BZX executable trading sessions span 04:00-20:00 ET; a TradingView export may still reflect chart session settings.",
    confidence="POSSIBLE_CHART_SESSION",
    holiday_calendar_complete=False,
)

# The following profiles deliberately describe the *frozen export representation*
# rather than claiming a universal exchange schedule. They are backed by a stable
# sibling-stream support fingerprint inside the reviewed corpus plus authoritative
# instrument/provider identity. Effective bounds prevent the profile from silently
# extending into future appended data without re-review.
TVC_DXY_FROZEN_EXPORT = SessionProfile(
    profile_id="tvc-dxy-frozen-export-support-2023-2026",
    timezone_name="America/New_York",
    weekly_open_windows=_weekly(
        (0, (DailyWindow(0, 24 * 60),)),
        (1, (DailyWindow(0, 24 * 60),)),
        (2, (DailyWindow(0, 24 * 60),)),
        (3, (DailyWindow(0, 24 * 60),)),
        (4, (DailyWindow(0, 17 * 60),)),
        (5, ()),
        (6, (DailyWindow(18 * 60, 24 * 60),)),
    ),
    evidence_authority="TradingView TVC identity documentation + reviewed frozen CSV sibling fingerprint",
    evidence_summary=(
        "TradingView states TVC symbols are TradingView-calculated/provider-composed instruments rather than exchange feeds. "
        "Within the frozen corpus, TVC:DXY sibling exports repeatedly support a Sunday-evening through Friday-afternoon ET window; "
        "this profile is used only to classify the reviewed export representation and is not asserted as ICE futures trading hours."
    ),
    confidence="FROZEN_EXPORT_SUPPORT_PROFILE",
    effective_start_ns=1672704000000000000,
    effective_end_ns=1790027040000000000,
    holiday_calendar_complete=False,
)

TVC_TNX_FROZEN_EXPORT = SessionProfile(
    profile_id="tvc-tnx-frozen-export-support-2015-2026",
    timezone_name="America/New_York",
    weekly_open_windows=_weekly(
        (0, (DailyWindow(8 * 60 + 20, 15 * 60),)),
        (1, (DailyWindow(8 * 60 + 20, 15 * 60),)),
        (2, (DailyWindow(8 * 60 + 20, 15 * 60),)),
        (3, (DailyWindow(8 * 60 + 20, 15 * 60),)),
        (4, (DailyWindow(8 * 60 + 20, 15 * 60),)),
        (5, ()), (6, ()),
    ),
    evidence_authority="Cboe TNX instrument identity + TradingView TVC identity documentation + reviewed frozen CSV sibling fingerprint",
    evidence_summary=(
        "Cboe identifies TNX as its 10-Year Treasury Note yield index and TradingView identifies TVC as a calculated/provider-composed namespace. "
        "Across long-lived frozen TVC:TNX sibling exports, observations recur from 08:20 through 14:59 ET on weekdays. "
        "The profile is therefore a corpus-specific support envelope, not a claim about every external TNX vendor feed."
    ),
    confidence="FROZEN_EXPORT_SUPPORT_PROFILE",
    effective_start_ns=1420204800000000000,
    effective_end_ns=1790017200000000000,
    holiday_calendar_complete=False,
)

LSE_MAG7_ETP = SessionProfile(
    profile_id="lse-mag7-etp-sets-rth",
    timezone_name="Europe/London",
    weekly_open_windows=_weekly(
        (0, (DailyWindow(8 * 60, 16 * 60 + 30),)),
        (1, (DailyWindow(8 * 60, 16 * 60 + 30),)),
        (2, (DailyWindow(8 * 60, 16 * 60 + 30),)),
        (3, (DailyWindow(8 * 60, 16 * 60 + 30),)),
        (4, (DailyWindow(8 * 60, 16 * 60 + 30),)),
        (5, ()), (6, ()),
    ),
    evidence_authority="London Stock Exchange",
    evidence_summary=(
        "LSE identifies ticker MAG7 as Leverage Shares 5X Long Magnificent 7 ETP. LSE ETPs trade on SETS, "
        "with continuous trading after the 07:50-08:00 opening auction until the 16:30 closing auction on London business days."
    ),
    confidence="EXACT_CONTRACT_OR_INDEX",
    holiday_calendar_complete=False,
)


def _infer_bzx_export_profile(times: list[int]) -> tuple[SessionProfile | None, str | None, str | None]:
    """Infer only the *exported representation's* recurring support window.

    This does not infer the exchange's capabilities from missing observations. Direct
    out-of-RTH timestamps prove an extended-session export. For an RTH-only inference,
    require a long multi-year fingerprint in which nearly every complete interior day
    starts near the official RTH open, extends well into the RTH close, and contains no
    observations outside RTH. This is evidence about the frozen export representation,
    not a claim that BZX itself lacks extended trading.
    """
    if len(times) < 500:
        return None, None, None
    tz = ZoneInfo("America/New_York")
    local = [datetime.fromtimestamp(ns / 1e9, timezone.utc).astimezone(tz) for ns in times]
    # Direct positive evidence beats absence-based inference.
    outside_rth = [dt for dt in local if dt.weekday() < 5 and not (9 * 60 + 30 <= dt.hour * 60 + dt.minute < 16 * 60)]
    outside_extended = [dt for dt in local if dt.weekday() < 5 and not (4 * 60 <= dt.hour * 60 + dt.minute < 20 * 60)]
    if outside_rth and not outside_extended:
        outside_days = {dt.date() for dt in outside_rth}
        if len(outside_days) >= 5:
            return (
                BZX_EXTENDED,
                "OBSERVED_EXPORT_EXTENDED_SESSION_DIRECTLY_ATTESTED",
                f"The export contains out-of-RTH observations on {len(outside_days)} dates while remaining inside official BZX extended hours.",
            )

    if outside_rth:
        return None, None, None

    by_day: dict[date, list[int]] = {}
    for dt in local:
        if dt.weekday() < 5:
            by_day.setdefault(dt.date(), []).append(dt.hour * 60 + dt.minute)
    days = sorted(by_day)
    if len(days) < 100:
        return None, None, None
    interior = days[1:-1]
    if not interior:
        return None, None, None
    boundary_consistent = 0
    for day in interior:
        mins = by_day[day]
        if mins and min(mins) <= 10 * 60 and max(mins) >= 15 * 60 and all(9 * 60 + 30 <= m < 16 * 60 for m in mins):
            boundary_consistent += 1
    ratio = boundary_consistent / len(interior)
    if ratio >= 0.98:
        return (
            BZX_REGULAR,
            "OBSERVED_EXPORT_RTH_FINGERPRINT_REVIEWED",
            f"The frozen export has an RTH-only recurring support fingerprint on {boundary_consistent}/{len(interior)} interior weekdays ({ratio:.3%}); no out-of-RTH rows were observed.",
        )
    return None, None, None


EXACT_PROFILES: dict[tuple[str, str], SessionProfile] = {
    ("CME", "ES1!"): CME_EQUITY_23X5,
    ("CME", "NQ1!"): CME_EQUITY_23X5,
    ("CBOT", "YM1!"): CME_EQUITY_23X5,
    ("COMEX", "SI1!"): COMEX_SILVER_23X5,
    ("NYMEX", "PL1!"): NYMEX_PLATINUM_23X5,
    ("NYMEX", "PA1!"): NYMEX_PALLADIUM_23X5,
    ("CME", "BTC1!"): CME_CRYPTO_24X7_2026,
    ("CBOE", "VXN"): CBOE_VXN_RTH,
    ("TVC", "VIX"): CBOE_VIX_GTH_RTH,
    ("TVC", "DXY"): TVC_DXY_FROZEN_EXPORT,
    ("TVC", "TNX"): TVC_TNX_FROZEN_EXPORT,
    ("LSE", "MAG7"): LSE_MAG7_ETP,
    ("BITSTAMP", "BTCUSD"): BITSTAMP_CRYPTO_24X7,
}

FAMILY_PROFILES: dict[tuple[str, str], SessionProfile] = {}

# Reviewed CME Globex holiday evidence for the currently observed daily-bar period.
# These dates are local 17:00 CT session-anchor dates on which the next trade-date
# session does not begin in the ordinary nightly slot. The set is deliberately
# bounded rather than presented as a complete perpetual holiday calendar.
CME_EQUITY_REVIEWED_NO_REOPEN_ANCHORS = frozenset({
    date(2025, 12, 24),  # Christmas schedule
    date(2025, 12, 31),  # New Year's schedule
})


def _candidate_dict(candidate: Any) -> dict[str, Any]:
    if isinstance(candidate, Mapping):
        return dict(candidate)
    if hasattr(candidate, "to_dict"):
        return dict(candidate.to_dict())
    raise TypeError(f"unsupported candidate type: {type(candidate)!r}")


def _to_event_ns(raw: str) -> int | None:
    try:
        return int(Decimal(raw.strip()) * Decimal(1_000_000_000))
    except (InvalidOperation, ValueError, AttributeError):
        return None


def _load_times(zf: zipfile.ZipFile, member: str) -> list[int]:
    out: list[int] = []
    with zf.open(member, "r") as raw, io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline="") as text:
        reader = csv.reader(text)
        header = next(reader, [])
        lower = [str(x).strip().lower() for x in header]
        time_idx = next((i for i, c in enumerate(lower) if c == "time"), None)
        if time_idx is None:
            return out
        for row in reader:
            try:
                value = _to_event_ns(row[time_idx])
            except IndexError:
                value = None
            if value is not None:
                out.append(value)
    return out


def _local_day_bounds(day: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time(0, 0), tzinfo=tz)
    return start, start + timedelta(days=1)


def _profile_open_intervals(profile: SessionProfile, start_ns: int, end_ns: int) -> list[tuple[int, int]]:
    tz = profile.tz
    start_local = datetime.fromtimestamp(start_ns / 1e9, timezone.utc).astimezone(tz)
    end_local = datetime.fromtimestamp(end_ns / 1e9, timezone.utc).astimezone(tz)
    day = start_local.date() - timedelta(days=1)
    last = end_local.date() + timedelta(days=1)
    out: list[tuple[int, int]] = []
    while day <= last:
        day_start, _ = _local_day_bounds(day, tz)
        for window in profile.windows_for_weekday(day.weekday()):
            wstart = day_start + timedelta(minutes=window.start_minute)
            wend = day_start + timedelta(minutes=window.end_minute)
            a = _ns_from_local(wstart)
            b = _ns_from_local(wend)
            if b > start_ns and a < end_ns:
                out.append((max(a, start_ns), min(b, end_ns)))
        day += timedelta(days=1)
    return out


def _intersects_open(profile: SessionProfile, start_ns: int, end_ns: int) -> bool:
    if end_ns <= start_ns:
        return False
    return any(b > a for a, b in _profile_open_intervals(profile, start_ns, end_ns))


def _assess_gap(profile: SessionProfile, previous_ns: int, next_ns: int, cadence_ns: int) -> GapAssessment:
    gap_ns = next_ns - previous_ns
    # Remove one nominal bar interval from each edge. This deliberately avoids
    # claiming bar-open vs bar-close semantics while still detecting whether the
    # *interior* missing span intersects a known open session.
    inner_start = previous_ns + cadence_ns
    inner_end = next_ns - cadence_ns
    if inner_end <= inner_start:
        mid = previous_ns + gap_ns // 2
        inner_start = mid
        inner_end = mid + 1

    if not profile.supports_interval(previous_ns, next_ns):
        classification = "UNSUPPORTED_PROFILE_EFFECTIVE_PERIOD"
    elif cadence_ns >= 6 * 60 * 60 * 1_000_000_000:
        # Coarse bars require a business-day/holiday calendar and chart-session
        # evidence; weekly windows alone are not sufficient for authoritative review.
        classification = "COARSE_BAR_CALENDAR_REVIEW_REQUIRED"
    elif _intersects_open(profile, inner_start, inner_end):
        classification = "RESIDUAL_OPEN_SESSION_GAP"
    else:
        classification = "EXPLAINED_BY_RECURRING_SESSION_CLOSURE"
    return GapAssessment(previous_ns, next_ns, gap_ns, classification)


def _candidate_manifest(candidate: Mapping[str, Any], by_stream: Mapping[str, list[StreamManifest]]) -> StreamManifest | None:
    scope = [str(x) for x in candidate.get("scope", [])]
    if len(scope) != 1:
        return None
    rows = by_stream.get(scope[0], [])
    if not rows:
        return None
    return sorted(rows, key=lambda m: m.identity.source_path)[0]


def _best_intraday_sibling(manifest: StreamManifest, manifests: Iterable[StreamManifest]) -> StreamManifest | None:
    candidates: list[StreamManifest] = []
    for row in manifests:
        if row.identity.stream_id == manifest.identity.stream_id:
            continue
        if row.identity.venue != manifest.identity.venue or row.identity.symbol != manifest.identity.symbol:
            continue
        cadence = int(row.observed_cadence_ns or 0)
        if cadence <= 0 or cadence >= 6 * 60 * 60 * 1_000_000_000:
            continue
        if row.first_event_ns is None or row.last_event_ns is None:
            continue
        candidates.append(row)
    if not candidates:
        return None
    target_start = int(manifest.first_event_ns or 0)
    target_end = int(manifest.last_event_ns or 0)
    return max(
        candidates,
        key=lambda row: (
            int(row.first_event_ns <= target_start and row.last_event_ns >= target_end),
            int(row.last_event_ns or 0) - int(row.first_event_ns or 0),
            int(row.row_count),
        ),
    )


def _count_events(times: list[int], start_ns: int, end_ns: int) -> int:
    if not times or end_ns <= start_ns:
        return 0
    a = bisect_left(times, start_ns)
    b = bisect_left(times, end_ns)
    return max(0, b - a)


def _assess_cme_equity_daily_gap(
    profile: SessionProfile,
    previous_ns: int,
    next_ns: int,
    sibling_times: list[int],
) -> GapAssessment:
    """Resolve a daily-bar gap without pretending elapsed 24h cadence is a session calendar.

    The daily export is treated as a representation. Missing local 17:00 CT anchors are
    accepted only when they are recurring weekend closures, reviewed holiday no-reopen
    anchors, or when a finer sibling stream directly proves that the underlying session
    traded while the daily export omitted/consolidated that anchor.
    """
    gap_ns = next_ns - previous_ns
    tz = profile.tz
    prev_local = datetime.fromtimestamp(previous_ns / 1e9, timezone.utc).astimezone(tz)
    next_local = datetime.fromtimestamp(next_ns / 1e9, timezone.utc).astimezone(tz)
    if prev_local.hour != 17 or next_local.hour != 17 or prev_local.minute != 0 or next_local.minute != 0:
        return GapAssessment(previous_ns, next_ns, gap_ns, "COARSE_BAR_CALENDAR_REVIEW_REQUIRED")

    unresolved = 0
    cursor = prev_local + timedelta(days=1)
    while cursor < next_local:
        # CME equity index futures have no ordinary Friday- or Saturday-evening reopen.
        if cursor.weekday() in (4, 5):
            cursor += timedelta(days=1)
            continue
        if cursor.date() in CME_EQUITY_REVIEWED_NO_REOPEN_ANCHORS:
            cursor += timedelta(days=1)
            continue

        start_ns = _ns_from_local(cursor)
        end_ns = _ns_from_local(cursor + timedelta(hours=23))
        # Direct cross-resolution evidence: require multiple finer observations in the
        # session represented by the omitted daily anchor. This demonstrates an
        # aggregation/label convention rather than underlying market-data absence.
        if _count_events(sibling_times, start_ns, end_ns) >= 3:
            cursor += timedelta(days=1)
            continue
        unresolved += 1
        cursor += timedelta(days=1)

    classification = (
        "COARSE_BAR_AGGREGATION_SESSION_SEMANTICS_RESOLVED"
        if unresolved == 0
        else "COARSE_BAR_CALENDAR_REVIEW_REQUIRED"
    )
    return GapAssessment(previous_ns, next_ns, gap_ns, classification)


def build_session_gap_resolution(
    corpus_root: str | Path,
    manifests: Iterable[StreamManifest],
    candidates: Iterable[Any],
) -> dict[str, Any]:
    root = Path(corpus_root)
    manifest_rows = list(manifests)
    by_stream: dict[str, list[StreamManifest]] = {}
    for m in manifest_rows:
        by_stream.setdefault(m.identity.stream_id, []).append(m)

    candidate_rows = [
        _candidate_dict(c) for c in candidates
        if str(_candidate_dict(c).get("family", "")) == "sampling_gap_sensitivity"
    ]

    archive_cache: dict[str, zipfile.ZipFile] = {}
    time_cache: dict[str, list[int]] = {}
    resolutions: list[SessionGapCandidateResolution] = []
    try:
        for candidate in candidate_rows:
            cid = str(candidate.get("candidate_id") or "")
            manifest = _candidate_manifest(candidate, by_stream)
            if manifest is None:
                resolutions.append(SessionGapCandidateResolution(
                    cid, None, None, None, None, "NO_SINGLE_STREAM_MANIFEST", 0, 0, 0, 0, 0,
                    False, False, "Candidate cannot be tied to one reviewed stream manifest.", None, None, (),
                ))
                continue

            key = (str(manifest.identity.venue or ""), manifest.identity.symbol)
            exact = EXACT_PROFILES.get(key)
            family = FAMILY_PROFILES.get(key)
            possible_profiles: tuple[SessionProfile, ...] = ()
            profile_status = "NO_REVIEWED_PROFILE"
            profile = exact or family
            if exact is not None:
                if exact.confidence == "UNDERLYING_INDEX_PROFILE_PROVIDER_WRAPPER":
                    profile_status = "UNDERLYING_INDEX_PROFILE_REVIEWED_PROVIDER_WRAPPER"
                elif exact.confidence == "FROZEN_EXPORT_SUPPORT_PROFILE":
                    profile_status = "FROZEN_EXPORT_SUPPORT_PROFILE_REVIEWED"
                else:
                    profile_status = "EXACT_PROFILE_REVIEWED"
            elif family is not None:
                profile_status = "FAMILY_PROFILE_REQUIRES_CONTRACT_EVIDENCE"
            elif manifest.identity.venue == "BATS":
                possible_profiles = (BZX_REGULAR, BZX_EXTENDED)
                profile_status = "POSSIBLE_CHART_SESSION_SET_REQUIRES_EXPORT_SETTING_EVIDENCE"

            archive_rel = str(manifest.metadata.get("archive_path") or "")
            member = str(manifest.metadata.get("archive_member") or "")
            times: list[int] = []
            if archive_rel and member:
                cache_key = f"{archive_rel}!{member}"
                if cache_key in time_cache:
                    times = time_cache[cache_key]
                else:
                    zf = archive_cache.get(archive_rel)
                    if zf is None:
                        zf = zipfile.ZipFile(root / archive_rel)
                        archive_cache[archive_rel] = zf
                    times = _load_times(zf, member)
                    time_cache[cache_key] = times

            cadence_ns = int(manifest.observed_cadence_ns or 0)
            gaps = [(a, b) for a, b in zip(times, times[1:]) if cadence_ns > 0 and b > a and (b - a) > cadence_ns * 1.5]
            assessments: list[GapAssessment] = []
            observed_profile_resolved = False
            observed_profile_reason: str | None = None
            if possible_profiles and manifest.identity.venue == "BATS":
                inferred_profile, inferred_status, inferred_reason = _infer_bzx_export_profile(times)
                if inferred_profile is not None:
                    profile = inferred_profile
                    profile_status = str(inferred_status)
                    observed_profile_resolved = True
                    observed_profile_reason = inferred_reason
                    possible_profiles = ()

            coarse_resolution_method: str | None = None
            coarse_evidence_stream_id: str | None = None
            if profile is not None:
                is_cme_equity_daily = (
                    key in {("CME", "ES1!"), ("CME", "NQ1!"), ("CBOT", "YM1!")}
                    and 20 * 60 * 60 * 1_000_000_000 <= cadence_ns <= 28 * 60 * 60 * 1_000_000_000
                )
                if is_cme_equity_daily:
                    sibling = _best_intraday_sibling(manifest, manifest_rows)
                    sibling_times: list[int] = []
                    if sibling is not None:
                        sib_archive = str(sibling.metadata.get("archive_path") or "")
                        sib_member = str(sibling.metadata.get("archive_member") or "")
                        if sib_archive and sib_member:
                            sib_cache_key = f"{sib_archive}!{sib_member}"
                            if sib_cache_key in time_cache:
                                sibling_times = time_cache[sib_cache_key]
                            else:
                                sib_zf = archive_cache.get(sib_archive)
                                if sib_zf is None:
                                    sib_zf = zipfile.ZipFile(root / sib_archive)
                                    archive_cache[sib_archive] = sib_zf
                                sibling_times = _load_times(sib_zf, sib_member)
                                time_cache[sib_cache_key] = sibling_times
                            coarse_evidence_stream_id = sibling.identity.stream_id
                    assessments = [_assess_cme_equity_daily_gap(profile, a, b, sibling_times) for a, b in gaps]
                    if assessments and all(x.classification == "COARSE_BAR_AGGREGATION_SESSION_SEMANTICS_RESOLVED" for x in assessments):
                        coarse_resolution_method = "REVIEWED_HOLIDAY_PLUS_CROSS_RESOLUTION_SIBLING"
                else:
                    assessments = [_assess_gap(profile, a, b, cadence_ns) for a, b in gaps]
            elif possible_profiles:
                # Only call a BZX gap definitely session-explained if it lies in a
                # closure under both official regular and extended-session possibilities.
                for a, b in gaps:
                    if cadence_ns >= 6 * 60 * 60 * 1_000_000_000:
                        cls = "COARSE_BAR_CALENDAR_REVIEW_REQUIRED"
                    else:
                        inner_start = a + cadence_ns
                        inner_end = b - cadence_ns
                        if inner_end <= inner_start:
                            mid = a + (b - a) // 2
                            inner_start, inner_end = mid, mid + 1
                        intersects = [_intersects_open(p, inner_start, inner_end) for p in possible_profiles]
                        if not any(intersects):
                            cls = "EXPLAINED_UNDER_ALL_OFFICIAL_BZX_SESSION_CHOICES"
                        elif all(intersects):
                            cls = "RESIDUAL_OPEN_SESSION_GAP_UNDER_ALL_BZX_CHOICES"
                        else:
                            cls = "AMBIGUOUS_CHART_SESSION_SETTING"
                    assessments.append(GapAssessment(a, b, b - a, cls))

            explained = sum(x.classification in {
                "EXPLAINED_BY_RECURRING_SESSION_CLOSURE",
                "EXPLAINED_UNDER_ALL_OFFICIAL_BZX_SESSION_CHOICES",
            } for x in assessments)
            residual = sum(x.classification in {
                "RESIDUAL_OPEN_SESSION_GAP",
                "RESIDUAL_OPEN_SESSION_GAP_UNDER_ALL_BZX_CHOICES",
            } for x in assessments)
            unsupported = sum(x.classification == "UNSUPPORTED_PROFILE_EFFECTIVE_PERIOD" for x in assessments)
            coarse = sum(x.classification == "COARSE_BAR_CALENDAR_REVIEW_REQUIRED" for x in assessments)
            coarse_resolved = sum(x.classification == "COARSE_BAR_AGGREGATION_SESSION_SEMANTICS_RESOLVED" for x in assessments)
            ambiguous = sum(x.classification == "AMBIGUOUS_CHART_SESSION_SETTING" for x in assessments)

            profile_resolved = bool(
                (exact is not None or observed_profile_resolved)
                and gaps
                and unsupported == 0
                and coarse == 0
            )
            if profile_resolved:
                prefix = observed_profile_reason or "A reviewed recurring session profile was applied."
                if coarse_resolved:
                    reason = (
                        f"{prefix} All {coarse_resolved} coarse daily gaps were resolved using reviewed CME holiday/no-reopen "
                        "anchors plus direct finer-sibling coverage where the underlying session traded but the daily export "
                        "omitted or consolidated a session anchor. This is representation/session canonicalization, not a data-loss claim."
                    )
                else:
                    reason = (
                        f"{prefix} Across {len(gaps)} observed gaps, {explained} are explained by recurring closures "
                        f"and {residual} occur inside the selected support/session window. Open-session residuals remain "
                        "data-quality/no-trade diagnostics and are not automatically labeled missing data."
                    )
            elif exact is not None and coarse > 0:
                reason = (
                    "An exact recurring session profile is reviewed, but coarse daily/multi-hour bars cannot be interpreted "
                    "from elapsed cadence alone. Holiday/early-close behavior and the vendor's bar-aggregation convention "
                    "must be reviewed before these gaps are classified."
                )
            elif exact is not None and unsupported > 0:
                reason = (
                    "A reviewed session profile exists, but one or more gaps fall outside the profile's attested effective period."
                )
            elif family is not None:
                reason = (
                    "A reviewed exchange-family schedule is available, but exact contract evidence is still required before "
                    "session semantics are considered resolved."
                )
            elif possible_profiles:
                reason = (
                    f"Official BZX regular and extended sessions were both evaluated: {explained} gaps are closed under both, "
                    f"{residual} are open under both, and {ambiguous} depend on the unknown TradingView chart-session setting."
                )
            else:
                reason = "No sufficiently reviewed session profile is registered for this stream; keep calendar/session interpretation blocked."

            resolutions.append(SessionGapCandidateResolution(
                candidate_id=cid,
                stream_id=manifest.identity.stream_id,
                venue=manifest.identity.venue,
                symbol=manifest.identity.symbol,
                profile_id=profile.profile_id if profile else None,
                profile_status=profile_status,
                gap_count=len(gaps),
                session_explained_gap_count=explained,
                residual_open_session_gap_count=residual,
                unsupported_effective_period_gap_count=unsupported,
                coarse_calendar_gap_count=coarse,
                session_semantics_resolved=profile_resolved,
                residual_data_quality_diagnostic_required=bool(profile_resolved and residual > 0),
                reason=reason,
                evidence_authority=profile.evidence_authority if profile else ("Cboe BZX" if possible_profiles else None),
                evidence_summary=profile.evidence_summary if profile else (
                    "BZX has official regular 09:30-16:00 ET and executable extended sessions through 20:00 ET; exported chart session setting remains unknown."
                    if possible_profiles else None
                ),
                gap_assessments=tuple(assessments),
                coarse_resolution_method=coarse_resolution_method,
                coarse_evidence_stream_id=coarse_evidence_stream_id,
            ))
    finally:
        for zf in archive_cache.values():
            zf.close()

    rows = [r.to_dict() for r in sorted(resolutions, key=lambda r: r.candidate_id)]
    body = {
        "schema": SCHEMA,
        "candidate_count": len(rows),
        "session_semantics_resolved_count": sum(bool(r["session_semantics_resolved"]) for r in rows),
        "residual_diagnostic_count": sum(bool(r["residual_data_quality_diagnostic_required"]) for r in rows),
        "still_session_blocked_count": sum(not bool(r["session_semantics_resolved"]) for r in rows),
        "resolutions": rows,
        "data_loss_asserted": False,
        "production_authorized": False,
    }
    body["resolution_hash"] = hashlib.sha256(
        json.dumps(body,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return body


def verify_session_gap_resolution(payload: Mapping[str, Any] | None) -> bool:
    if not isinstance(payload,Mapping) or payload.get("schema") != SCHEMA:
        return False
    supplied=payload.get("resolution_hash")
    if not isinstance(supplied,str) or len(supplied)!=64:
        return False
    try:
        int(supplied,16)
    except ValueError:
        return False
    body=dict(payload);body.pop("resolution_hash",None)
    try:
        expected=hashlib.sha256(
            json.dumps(body,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
        ).hexdigest()
    except (TypeError,ValueError):
        return False
    if supplied != expected:
        return False
    if body.get("production_authorized") is not False or body.get("data_loss_asserted") is not False:
        return False
    rows=body.get("resolutions")
    if not isinstance(rows,list):
        return False

    explained_classes={
        "EXPLAINED_BY_RECURRING_SESSION_CLOSURE",
        "EXPLAINED_UNDER_ALL_OFFICIAL_BZX_SESSION_CHOICES",
    }
    residual_classes={
        "RESIDUAL_OPEN_SESSION_GAP",
        "RESIDUAL_OPEN_SESSION_GAP_UNDER_ALL_BZX_CHOICES",
    }
    ids=[];resolved_count=0;diagnostics=0
    for row in rows:
        if not isinstance(row,Mapping):
            return False
        cid=str(row.get("candidate_id") or "")
        if not cid:
            return False
        ids.append(cid)

        counts={}
        for name in (
            "gap_count","session_explained_gap_count","residual_open_session_gap_count",
            "unsupported_effective_period_gap_count","coarse_calendar_gap_count",
        ):
            value=row.get(name)
            if type(value) is not int or value < 0:
                return False
            counts[name]=value
        if any(v>counts["gap_count"] for k,v in counts.items() if k!="gap_count"):
            return False

        is_resolved=row.get("session_semantics_resolved")
        diagnostic=row.get("residual_data_quality_diagnostic_required")
        if type(is_resolved) is not bool or type(diagnostic) is not bool:
            return False

        assessments=row.get("gap_assessments")
        if not isinstance(assessments,list):
            return False
        computed_explained=computed_residual=computed_unsupported=computed_coarse=0
        for assessment in assessments:
            if not isinstance(assessment,Mapping):
                return False
            a=assessment.get("previous_event_ns")
            b=assessment.get("next_event_ns")
            gap=assessment.get("gap_ns")
            cls=str(assessment.get("classification") or "")
            if (
                type(a) is not int or type(b) is not int or type(gap) is not int
                or a < 0 or b <= a or gap != b-a or not cls
            ):
                return False
            computed_explained += int(cls in explained_classes)
            computed_residual += int(cls in residual_classes)
            computed_unsupported += int(cls=="UNSUPPORTED_PROFILE_EFFECTIVE_PERIOD")
            computed_coarse += int(cls=="COARSE_BAR_CALENDAR_REVIEW_REQUIRED")

        if (
            counts["session_explained_gap_count"] != computed_explained
            or counts["residual_open_session_gap_count"] != computed_residual
            or counts["unsupported_effective_period_gap_count"] != computed_unsupported
            or counts["coarse_calendar_gap_count"] != computed_coarse
        ):
            return False
        if len(assessments) > counts["gap_count"]:
            return False
        if diagnostic != bool(is_resolved and computed_residual>0):
            return False

        if is_resolved:
            resolved_count += 1
            if (
                counts["gap_count"] <= 0
                or len(assessments) != counts["gap_count"]
                or computed_unsupported != 0
                or computed_coarse != 0
                or not row.get("stream_id")
                or not row.get("profile_id")
                or not row.get("evidence_authority")
                or not row.get("evidence_summary")
            ):
                return False
        if diagnostic:
            diagnostics += 1

    if len(set(ids)) != len(ids):
        return False
    return (
        type(body.get("candidate_count")) is int
        and type(body.get("session_semantics_resolved_count")) is int
        and type(body.get("residual_diagnostic_count")) is int
        and type(body.get("still_session_blocked_count")) is int
        and body["candidate_count"]==len(rows)
        and body["session_semantics_resolved_count"]==resolved_count
        and body["residual_diagnostic_count"]==diagnostics
        and body["still_session_blocked_count"]==len(rows)-resolved_count
    )


def build_session_semantic_blocker_report(session_gap_resolution: Mapping[str, Any]) -> dict[str, Any]:
    """Convert unresolved session rows into a compact evidence-acquisition queue."""
    if not verify_session_gap_resolution(session_gap_resolution):
        raise ValueError("invalid or tampered session-gap resolution artifact")
    rows: list[dict[str, Any]] = []
    for raw in session_gap_resolution.get("resolutions", []):
        if not isinstance(raw, Mapping) or bool(raw.get("session_semantics_resolved")):
            continue
        r = dict(raw)
        venue = str(r.get("venue") or "")
        symbol = str(r.get("symbol") or "")
        coarse = int(r.get("coarse_calendar_gap_count") or 0)
        if coarse > 0:
            blocker_class = "COARSE_BAR_HOLIDAY_AGGREGATION_SEMANTICS"
            required = (
                "Review the exchange holiday/early-close calendar over the candidate period and the vendor's daily-bar "
                "aggregation/label convention. Do not infer missing data from 24-hour elapsed cadence."
            )
        elif venue == "TVC":
            blocker_class = "PROVIDER_WRAPPER_UNDERLYING_SESSION_IDENTITY"
            required = (
                "Establish the authoritative underlying index/instrument and its dissemination/trading schedule, then verify "
                "how the TVC/TradingView wrapper maps or filters that schedule for this export."
            )
        elif venue == "LSE":
            blocker_class = "SYMBOL_VENUE_CONTRACT_IDENTITY"
            required = (
                "Identify the exact MAG7 instrument/security represented by the export and obtain authoritative venue trading "
                "hours plus the chart-session/aggregation convention."
            )
        else:
            blocker_class = "SESSION_PROFILE_EVIDENCE_MISSING"
            required = "Obtain authoritative contract/index session evidence and representation-specific chart-session semantics."
        rows.append({
            "candidate_id": str(r.get("candidate_id") or ""),
            "stream_id": r.get("stream_id"),
            "venue": venue or None,
            "symbol": symbol or None,
            "blocker_class": blocker_class,
            "required_evidence": required,
            "profile_status": r.get("profile_status"),
            "gap_count": int(r.get("gap_count") or 0),
            "coarse_calendar_gap_count": coarse,
            "production_authorized": False,
        })
    rows.sort(key=lambda x: (x["blocker_class"], x["venue"] or "", x["symbol"] or "", x["candidate_id"]))
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["blocker_class"]] = counts.get(row["blocker_class"], 0) + 1
    return {
        "schema": "nexus.session-semantic-blocker-report.v1",
        "unresolved_candidate_count": len(rows),
        "blocker_class_counts": dict(sorted(counts.items())),
        "blockers": rows,
        "data_loss_asserted": False,
        "production_authorized": False,
    }
