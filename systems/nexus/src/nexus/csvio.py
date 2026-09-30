from __future__ import annotations
import pandas as pd
from pathlib import Path
from .ingest import BarClockPolicy, iter_bars


def load_ohlcv(
    path: str | Path,
    *,
    conservative_availability: bool = True,
    keep_unsealed_terminal: bool = False,
    column_positions: dict[str, int] | None = None,
) -> pd.DataFrame:
    """Load OHLCV without silently collapsing duplicate semantic headers.

    ``column_positions`` selects exact zero-based original positions when a required or
    optional semantic header is duplicated. Conservative mode uses the next strictly later
    source stamp as availability and withholds a terminal unsealed group by default.
    """
    if type(conservative_availability) is not bool:
        raise TypeError("conservative_availability must be bool")
    if type(keep_unsealed_terminal) is not bool:
        raise TypeError("keep_unsealed_terminal must be bool")
    # Disabling the conservative-next rule must not invent verified bar-close
    # timing. Unknown timestamp semantics remain explicitly unavailable.
    policy = BarClockPolicy(
        source_stamp="conservative_next" if conservative_availability else "unknown"
    )
    events = list(iter_bars(
        path,
        "csvio",
        clock_policy=policy,
        emit_unsealed_terminal=keep_unsealed_terminal,
        column_positions=column_positions,
    ))
    rows=[]
    for e in events:
        row={
            "event_ns": e.source_timestamp_ns if e.source_timestamp_ns is not None else e.event_ns,
            "open":e.open,"high":e.high,"low":e.low,"close":e.close,
            "source_sequence":e.source_sequence,"available_ns":e.available_ns,
        }
        if e.volume is not None: row["volume"]=e.volume
        rows.append(row)
    out=pd.DataFrame(rows)
    if not len(out):
        return pd.DataFrame(columns=["event_ns","open","high","low","close","source_sequence","available_ns"])
    if out["available_ns"].notna().all(): out["available_ns"]=out["available_ns"].astype("int64")
    else: out["available_ns"]=out["available_ns"].astype("Int64")
    return out.reset_index(drop=True)
