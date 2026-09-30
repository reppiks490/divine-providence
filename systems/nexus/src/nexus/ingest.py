from __future__ import annotations
import csv
from dataclasses import dataclass
from pathlib import Path
from .contracts import BarEvent, StreamManifest, QualityFlag
from .timeutil import timestamp_to_ns
from .columns import profile_header, resolve_columns


@dataclass(frozen=True)
class BarClockPolicy:
    """Convert a source bar stamp into conservative completion/availability semantics.

    Modes:
    - ``open``: source timestamp is known bar-open; cadence is required.
    - ``close``: source timestamp is known bar-close.
    - ``conservative_next``: timestamp semantics are not proven. The row becomes
      available only at the next *strictly later* source timestamp in source order.
      This intentionally delays close-stamped bars by one observed update, but avoids
      leaking a still-forming bar when the provider actually stamps opens.
    - ``unknown``: preserves legacy/raw timing and marks availability unverified.

    ``conservative_next`` is the CSV-safe default for NEXUS because historical exports
    rarely prove whether timestamps denote open or close. The final unsealed rows are
    withheld by ``iter_bars`` unless explicitly requested.
    """
    source_stamp: str = "conservative_next"  # open | close | conservative_next | unknown
    cadence_ns: int | None = None
    availability_delay_ns: int = 0
    basis: str = "unknown"
    extra_quality_flags: tuple[str, ...] = ()

    def resolve(
        self,
        source_timestamp_ns: int,
        *,
        next_strictly_later_ns: int | None = None,
    ) -> tuple[int, int | None, tuple[str, ...], str]:
        delay = max(0, int(self.availability_delay_ns))
        if self.source_stamp == "open":
            if not self.cadence_ns or self.cadence_ns <= 0:
                raise ValueError("open-stamped bars require positive cadence_ns")
            event_ns = source_timestamp_ns + int(self.cadence_ns)
            return event_ns, event_ns + delay, self.extra_quality_flags, self.basis or "verified_bar_close"
        if self.source_stamp == "close":
            event_ns = source_timestamp_ns
            return event_ns, event_ns + delay, self.extra_quality_flags, self.basis or "verified_bar_close"
        if self.source_stamp == "conservative_next":
            if next_strictly_later_ns is None:
                return source_timestamp_ns, None, tuple(dict.fromkeys((*self.extra_quality_flags,
                    QualityFlag.STAMP_SEMANTICS_UNKNOWN.value,
                    QualityFlag.AVAILABILITY_UNKNOWN.value,
                ))), "unsealed_terminal_unknown_stamp"
            return source_timestamp_ns, int(next_strictly_later_ns) + delay, tuple(dict.fromkeys((*self.extra_quality_flags,
                QualityFlag.STAMP_SEMANTICS_UNKNOWN.value,
            ))), "conservative_next_strictly_later_source_stamp"
        if self.source_stamp == "unknown":
            return source_timestamp_ns, None, tuple(dict.fromkeys((*self.extra_quality_flags,
                QualityFlag.STAMP_SEMANTICS_UNKNOWN.value,
                QualityFlag.AVAILABILITY_UNKNOWN.value,
            ))), "unknown"
        raise ValueError(f"unknown source_stamp policy: {self.source_stamp}")


def policy_from_manifest(
    manifest: StreamManifest,
    *,
    source_stamp: str = "conservative_next",
    availability_delay_ns: int = 0,
) -> BarClockPolicy:
    return BarClockPolicy(
        source_stamp=source_stamp,
        cadence_ns=manifest.observed_cadence_ns,
        availability_delay_ns=availability_delay_ns,
        basis="verified_bar_close" if source_stamp in {"open", "close"} else "unknown",
    )


def _f(v: str | None) -> float | None:
    if v is None or str(v).strip() == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _next_strictly_greater(values: list[int]) -> list[int | None]:
    """Next strictly greater value to the right in source order, O(n)."""
    out: list[int | None] = [None] * len(values)
    stack: list[int] = []
    for i, value in enumerate(values):
        while stack and value > values[stack[-1]]:
            out[stack.pop()] = value
        stack.append(i)
    return out


def iter_bars(
    path: str | Path,
    stream_id: str,
    data_plane: str = "research",
    clock_policy: BarClockPolicy | None = None,
    *,
    emit_unsealed_terminal: bool = False,
    column_positions: dict[str, int] | None = None,
):
    """Yield source-order bars with causal availability semantics.

    Under the default conservative policy, terminal unsealed rows are withheld. Set
    ``emit_unsealed_terminal=True`` only for forensic inspection; those rows retain
    ``available_ns=None`` and are not decision-time eligible.
    """
    path = Path(path)
    clock_policy = clock_policy or BarClockPolicy()
    parsed: list[tuple[int, int, dict[str, float], float | None]] = []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        r = csv.reader(f)
        header = next(r)
        try:
            idx = resolve_columns(profile_header(header), explicit_positions=column_positions)
        except ValueError as exc:
            raise type(exc)(f"{path}: {exc}") from exc
        for seq, row in enumerate(r):
            try:
                raw_ns, _ = timestamp_to_ns(row[idx["time"]])
                vals = {k: _f(row[idx[k]]) for k in ("open", "high", "low", "close")}
                if any(vals[k] is None for k in vals):
                    continue
                vol = _f(row[idx["volume"]]) if "volume" in idx and idx["volume"] < len(row) else None
                parsed.append((seq, raw_ns, vals, vol))
            except (IndexError, ValueError):
                continue

    raw_times=[x[1] for x in parsed]
    for i,(a,b) in enumerate(zip(raw_times,raw_times[1:]),start=1):
        if b<a:
            raise BackwardSourceTimeError(
                f"{path}: source time moved backward at parsed row {i}: {b} < {a}"
            )
    next_greater = _next_strictly_greater(raw_times)
    has_any_sealed = any(x is not None for x in next_greater)
    for (seq, raw_ns, vals, vol), next_ns in zip(parsed, next_greater):
        event_ns, available_ns, qflags, basis = clock_policy.resolve(
            raw_ns,
            next_strictly_later_ns=next_ns,
        )
        if (clock_policy.source_stamp == "conservative_next" and available_ns is None
                and not emit_unsealed_terminal and has_any_sealed):
            continue
        yield BarEvent(
            stream_id,
            event_ns,
            seq,
            vals["open"],
            vals["high"],
            vals["low"],
            vals["close"],
            vol,
            str(path),
            data_plane,
            qflags,
            available_ns,
            0,
            raw_ns,
            basis,
        )

class BackwardSourceTimeError(ValueError):
    pass


def iter_bars_streaming(
    path: str | Path,
    stream_id: str,
    data_plane: str = "research",
    clock_policy: BarClockPolicy | None = None,
    *,
    column_positions: dict[str,int] | None = None,
    emit_unsealed_terminal: bool = False,
):
    """Memory-bounded CSV bar reader for non-decreasing source timestamps.

    Under ``conservative_next`` only the current repeated-timestamp group is buffered;
    the next strictly greater timestamp seals the group. Backward source time is rejected
    rather than silently sorted. This makes memory scale with the largest equal-time group,
    not file length.
    """
    path=Path(path);clock_policy=clock_policy or BarClockPolicy()

    def emit(group,next_ns):
        for seq,raw_ns,vals,vol in group:
            event_ns,available_ns,qflags,basis=clock_policy.resolve(raw_ns,next_strictly_later_ns=next_ns)
            if clock_policy.source_stamp=="conservative_next" and available_ns is None and not emit_unsealed_terminal:
                continue
            yield BarEvent(stream_id,event_ns,seq,vals["open"],vals["high"],vals["low"],vals["close"],vol,str(path),data_plane,qflags,available_ns,0,raw_ns,basis)

    with path.open("r",encoding="utf-8-sig",errors="replace",newline="") as f:
        r=csv.reader(f);header=next(r,[])
        idx=resolve_columns(profile_header(header),explicit_positions=column_positions)
        pending=[];pending_ts=None;last_raw_ns=None
        for seq,row in enumerate(r):
            try:
                raw_ns,_=timestamp_to_ns(row[idx["time"]])
                vals={k:_f(row[idx[k]]) for k in ("open","high","low","close")}
                if any(vals[k] is None for k in vals):continue
                vol=_f(row[idx["volume"]]) if "volume" in idx and idx["volume"]<len(row) else None
            except (IndexError,ValueError):
                continue
            if last_raw_ns is not None and raw_ns<last_raw_ns:
                raise BackwardSourceTimeError(
                    f"{path}: source time moved backward at sequence {seq}: {raw_ns} < {last_raw_ns}"
                )
            last_raw_ns=raw_ns
            item=(seq,raw_ns,vals,vol)
            if clock_policy.source_stamp!="conservative_next":
                yield from emit([item],None);continue
            if pending_ts is None:
                pending_ts=raw_ns;pending=[item];continue
            if raw_ns<pending_ts:
                raise BackwardSourceTimeError(f"{path}: source time moved backward at sequence {seq}: {raw_ns} < {pending_ts}")
            if raw_ns==pending_ts:
                pending.append(item);continue
            yield from emit(pending,raw_ns)
            pending_ts=raw_ns;pending=[item]
        if pending:
            yield from emit(pending,None)
