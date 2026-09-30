from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

_TIMEFRAME_RE = re.compile(r"^(?P<n>\d+)(?P<unit>S|D|W|M)?$", re.I)
_COPY_RE = re.compile(r"^(?P<tf>\d+(?:S|D|W|M)?)(?:\s+(?P<copy>\d+))?$", re.I)


@dataclass(frozen=True, slots=True)
class ParsedFilename:
    venue: str | None
    symbol: str
    raw_claim: str | None
    timeframe_claim: str | None
    copy_ordinal: int | None


def parse_market_filename(path: str | Path) -> ParsedFilename:
    """Parse TradingView-like `<venue>_<symbol>, <tf> [copy].csv` names safely.

    The trailing integer added by OS/browser duplicate downloads is preserved as
    `copy_ordinal` instead of being mistaken for a market timeframe. Filenames
    remain claims only; they never override observed/reviewed stream semantics.
    """
    p = Path(path)
    stem = p.name[:-4] if p.name.lower().endswith(".csv") else p.stem
    if "," in stem:
        base, raw_claim = stem.rsplit(",", 1)
        raw_claim = raw_claim.strip() or None
    else:
        base, raw_claim = stem, None
    base = base.strip()
    parts = base.split("_")
    venue = parts[0] if len(parts) > 1 else None
    symbol = parts[-1] if parts else base

    tf = None
    copy = None
    if raw_claim:
        m = _COPY_RE.fullmatch(raw_claim)
        if m:
            tf = m.group("tf").upper()
            copy = int(m.group("copy")) if m.group("copy") else None
    return ParsedFilename(venue, symbol, raw_claim, tf, copy)


def timeframe_claim_to_ns(claim: str | None) -> int | None:
    """Convert a fixed TradingView-style timeframe claim to nanoseconds.

    Numeric claims are minutes; `S`, `D`, and `W` are fixed-duration claims.
    Month (`M`) is deliberately not converted because calendar months are not
    fixed-duration intervals. Tick (`T`) and range (`R`) claims are deliberately
    non-time constructions and therefore never convert to nanoseconds.
    """
    if not claim:
        return None
    m = _TIMEFRAME_RE.fullmatch(claim.strip().upper())
    if not m:
        return None
    n = int(m.group("n"))
    unit = (m.group("unit") or "MIN").upper()
    if n <= 0:
        return None
    second = 1_000_000_000
    if unit == "S":
        return n * second
    if unit == "MIN":
        return n * 60 * second
    if unit == "D":
        return n * 86_400 * second
    if unit == "W":
        return n * 7 * 86_400 * second
    return None


def sampling_claim_metadata(claim: str | None) -> dict[str, str | None]:
    """Classify a filename interval/construction claim without granting authority.

    TradingView-style numeric/S/D/W/M claims are time/calendar sampling. T and R
    suffixes denote tick- and range-driven constructions. This is a filename claim
    only; reviewed representation identity remains a separate gate.
    """
    if not claim:
        return {"sampling_domain": "unknown", "construction": "unknown", "setting": None}
    value = claim.strip().upper()
    m = _TIMEFRAME_RE.fullmatch(value)
    if not m:
        return {"sampling_domain": "unknown", "construction": "unknown", "setting": value}
    unit = (m.group("unit") or "MIN").upper()
    if unit == "T":
        return {"sampling_domain": "event", "construction": "tick", "setting": value}
    if unit == "R":
        return {"sampling_domain": "event", "construction": "range", "setting": value}
    return {"sampling_domain": "time", "construction": "time_bar", "setting": value}
