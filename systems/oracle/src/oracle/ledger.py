from __future__ import annotations
from dataclasses import asdict,dataclass
import hashlib,json
from typing import Any

@dataclass(frozen=True,slots=True)
class LedgerEntry:
    index:int; occurred_ns:int; event_type:str; payload:dict[str,Any]; previous_hash:str; entry_hash:str

class AuditLedger:
    def __init__(self): self._entries:list[LedgerEntry]=[]
    @staticmethod
    def _hash(index:int,occurred_ns:int,event_type:str,payload:dict[str,Any],previous_hash:str)->str:
        raw=json.dumps({"index":index,"occurred_ns":occurred_ns,"event_type":event_type,"payload":payload,"previous_hash":previous_hash},sort_keys=True,separators=(",",":"),allow_nan=False,default=str)
        return hashlib.sha256(raw.encode()).hexdigest()
    def append(self,event_type:str,arg2,arg3)->LedgerEntry:
        # Accept both (type,payload,time) and (type,time,payload) during recovery; canonicalize internally.
        if isinstance(arg2,dict): payload,occurred_ns=arg2,int(arg3)
        else: occurred_ns,payload=int(arg2),dict(arg3)
        if occurred_ns<0 or not event_type: raise ValueError("invalid ledger event")
        previous=self._entries[-1].entry_hash if self._entries else "0"*64
        idx=len(self._entries); h=self._hash(idx,occurred_ns,event_type,payload,previous)
        e=LedgerEntry(idx,occurred_ns,event_type,dict(payload),previous,h); self._entries.append(e); return e
    def entries(self)->tuple[LedgerEntry,...]: return tuple(self._entries)
    def verify(self)->bool:
        prev="0"*64
        for i,e in enumerate(self._entries):
            if e.index!=i or e.previous_hash!=prev or e.entry_hash!=self._hash(i,e.occurred_ns,e.event_type,e.payload,prev): return False
            prev=e.entry_hash
        return True
    @property
    def head_hash(self)->str: return self._entries[-1].entry_hash if self._entries else "0"*64
