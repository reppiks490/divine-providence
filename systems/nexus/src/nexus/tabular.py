from __future__ import annotations
import csv
import math
from pathlib import Path
from .columns import profile_header, AmbiguousColumnError
from .contracts import VectorEvent, QualityFlag
from .ingest import BarClockPolicy, _next_strictly_greater
from .timeutil import timestamp_to_ns


def _field_id(name:str, position:int)->str:
    key=name.strip().lower() or "unnamed"
    return f"{key}#{position}"


def iter_numeric_events(
    path:str|Path,
    stream_id:str,
    *,
    clock_policy:BarClockPolicy|None=None,
    data_plane:str="research",
    time_position:int|None=None,
    selected_positions:tuple[int,...]|None=None,
    emit_unsealed_terminal:bool=False,
):
    """Read non-OHLC numeric CSVs without collapsing duplicate header names.

    Every value field is identified as ``normalized_name#original_position``. The time column
    must be unique unless ``time_position`` explicitly selects one. No resampling or imputation
    occurs here.
    """
    path=Path(path); clock_policy=clock_policy or BarClockPolicy()
    parsed=[]
    with path.open("r",encoding="utf-8-sig",errors="replace",newline="") as f:
        r=csv.reader(f); header=next(r,[]); hp=profile_header(header)
        times=hp.positions.get("time",())
        if time_position is None:
            if not times: raise ValueError(f"{path}: missing time column")
            if len(times)>1: raise AmbiguousColumnError(f"{path}: duplicate time columns at {times}; select time_position")
            ti=times[0]
        else:
            ti=int(time_position)
            if ti<0 or ti>=len(header) or header[ti].strip().lower()!="time":
                raise ValueError(f"{path}: time_position {ti} does not point to a time column")
        positions=tuple(i for i in (selected_positions if selected_positions is not None else range(len(header))) if i!=ti)
        for i in positions:
            if i<0 or i>=len(header): raise ValueError(f"{path}: selected position {i} out of range")
        duplicate_flag=(QualityFlag.DUPLICATE_HEADER.value,) if hp.duplicates else ()
        for seq,row in enumerate(r):
            if ti>=len(row): continue
            try: raw_ns,_=timestamp_to_ns(row[ti])
            except ValueError: continue
            fields=[]
            for i in positions:
                if i>=len(row) or str(row[i]).strip()=="": continue
                try: v=float(row[i])
                except ValueError: continue
                if math.isfinite(v): fields.append((_field_id(header[i],i),v))
            if not fields: continue
            parsed.append((seq,raw_ns,tuple(fields),duplicate_flag))
    next_greater=_next_strictly_greater([x[1] for x in parsed]); has_any_sealed=any(x is not None for x in next_greater)
    for (seq,raw_ns,fields,header_flags),next_ns in zip(parsed,next_greater):
        event_ns,available_ns,qflags,basis=clock_policy.resolve(raw_ns,next_strictly_later_ns=next_ns)
        if (clock_policy.source_stamp=="conservative_next" and available_ns is None
                and not emit_unsealed_terminal and has_any_sealed):
            continue
        flags=tuple(dict.fromkeys((*header_flags,*qflags)))
        yield VectorEvent(stream_id,event_ns,seq,fields,str(path),data_plane,flags,available_ns,0,raw_ns,basis)
