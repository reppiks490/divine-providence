"""Crash-resilient framed proof journal for Infrastructure Supervisory V16.

Persistence/recovery only. Corrupt or partial evidence is quarantined from proof/learning;
this module never grants mutation authority.
"""
from __future__ import annotations
import hashlib, json, os, struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Tuple

MAGIC=b"ISJ16\x00"
HEADER=struct.Struct(">6sQ32s")
MAX_FRAME_BYTES=16*1024*1024


def _canonical(payload: Mapping[str,Any])->bytes:
    return json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")

@dataclass(frozen=True)
class DurableRecord:
    offset:int
    end_offset:int
    payload:Mapping[str,Any]
    payload_hash:str

@dataclass(frozen=True)
class RecoveryReport:
    records:Tuple[DurableRecord,...]
    last_good_offset:int
    file_size:int
    tail_status:str
    reason:str
    duplicate_interventions:Tuple[str,...]

    @property
    def clean(self)->bool:
        return self.tail_status=="clean" and not self.duplicate_interventions

class DurableProofJournal:
    def __init__(self,path:str|os.PathLike[str]): self.path=Path(path)

    def append(self,payload:Mapping[str,Any],*,fsync:bool=True)->DurableRecord:
        raw=_canonical(payload)
        if len(raw)>MAX_FRAME_BYTES: raise ValueError("journal frame too large")
        digest=hashlib.sha256(raw).digest()
        frame=HEADER.pack(MAGIC,len(raw),digest)+raw
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.open("ab",buffering=0) as f:
            offset=f.tell(); f.write(frame); f.flush()
            if fsync: os.fsync(f.fileno())
            end=f.tell()
        return DurableRecord(offset,end,dict(payload),digest.hex())

    def recover(self)->RecoveryReport:
        if not self.path.exists(): return RecoveryReport((),0,0,"clean","empty",())
        data=self.path.read_bytes(); size=len(data); pos=0; out=[]; seen=set(); dup=[]
        while pos<size:
            start=pos
            if size-pos<HEADER.size:
                return RecoveryReport(tuple(out),start,size,"truncated","partial frame header",tuple(dup))
            magic,length,digest=HEADER.unpack(data[pos:pos+HEADER.size]); pos+=HEADER.size
            if magic!=MAGIC:
                return RecoveryReport(tuple(out),start,size,"corrupt","frame magic mismatch",tuple(dup))
            if length>MAX_FRAME_BYTES:
                return RecoveryReport(tuple(out),start,size,"corrupt","frame length exceeds limit",tuple(dup))
            if size-pos<length:
                return RecoveryReport(tuple(out),start,size,"truncated","partial frame payload",tuple(dup))
            raw=data[pos:pos+length]; pos+=length
            if hashlib.sha256(raw).digest()!=digest:
                return RecoveryReport(tuple(out),start,size,"corrupt","frame checksum mismatch",tuple(dup))
            try: payload=json.loads(raw.decode("utf-8"))
            except Exception:
                return RecoveryReport(tuple(out),start,size,"corrupt","invalid frame json",tuple(dup))
            if not isinstance(payload,dict):
                return RecoveryReport(tuple(out),start,size,"corrupt","frame payload not object",tuple(dup))
            iid=payload.get("intervention_id")
            if iid:
                if iid in seen and iid not in dup: dup.append(iid)
                seen.add(iid)
            out.append(DurableRecord(start,pos,payload,digest.hex()))
        reason="verified" if not dup else "duplicate intervention records"
        return RecoveryReport(tuple(out),pos,size,"clean",reason,tuple(dup))

    def quarantine_tail(self,report:RecoveryReport,quarantine_path:str|os.PathLike[str])->int:
        """Copy corrupt/truncated tail aside and truncate to last verified boundary."""
        if report.tail_status=="clean": return 0
        data=self.path.read_bytes(); tail=data[report.last_good_offset:]
        qp=Path(quarantine_path); qp.parent.mkdir(parents=True,exist_ok=True); qp.write_bytes(tail)
        with self.path.open("r+b") as f:
            f.truncate(report.last_good_offset); f.flush(); os.fsync(f.fileno())
        return len(tail)
