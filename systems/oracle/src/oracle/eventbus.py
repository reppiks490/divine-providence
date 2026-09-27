from __future__ import annotations
from dataclasses import dataclass
from typing import Any,Callable
from .contracts import digest
@dataclass(frozen=True,slots=True)
class EventEnvelope: event_id:str; topic:str; event_ns:int; payload:dict[str,Any]; lineage_hash:str
class DeterministicEventBus:
    def __init__(self): self._handlers={}; self._seen=set()
    def subscribe(self,topic,handler_id,fn):
        rows=self._handlers.setdefault(topic,[])
        if any(x[0]==handler_id for x in rows): raise ValueError("duplicate handler")
        rows.append((handler_id,fn)); rows.sort(key=lambda x:x[0])
    def publish(self,topic,event_ns,payload,lineage_hash):
        eid="EV-"+digest({"topic":topic,"event_ns":event_ns,"payload":payload,"lineage_hash":lineage_hash})[:24]; env=EventEnvelope(eid,topic,event_ns,payload,lineage_hash)
        if eid in self._seen: return env
        self._seen.add(eid)
        for _,fn in self._handlers.get(topic,()): fn(env)
        return env
