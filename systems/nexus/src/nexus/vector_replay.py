from __future__ import annotations
import hashlib,heapq,json
from typing import Iterable,Iterator
from .contracts import VectorEvent,VectorStatePacket
from .replay import ReplayAvailabilityError, ReplayOrderingError


class VectorReplayBus:
    """Batch-atomic deterministic replay for generic numeric/context events."""
    def merge(self,streams:dict[str,Iterable[VectorEvent]],*,require_available:bool=True)->Iterator[VectorEvent]:
        heap=[];its={k:iter(v) for k,v in streams.items()};last_keys={}
        def checked(expected_sid:str,e:VectorEvent)->VectorEvent:
            if e.stream_id!=expected_sid:
                raise ReplayOrderingError(
                    f"stream mapping key {expected_sid!r} does not match event stream_id {e.stream_id!r}"
                )
            if e.available_ns is not None and int(e.available_ns)<int(e.event_ns):
                raise ReplayAvailabilityError(f"stream {e.stream_id} sequence {e.source_sequence} is available before its event")
            if e.source_timestamp_ns is not None and int(e.event_ns)<int(e.source_timestamp_ns):
                raise ReplayAvailabilityError(f"stream {e.stream_id} sequence {e.source_sequence} event precedes source timestamp")
            if require_available and e.available_ns is None:
                raise ReplayAvailabilityError(f"stream {e.stream_id} sequence {e.source_sequence} has unknown availability")
            key=e.ordering_key;prev=last_keys.get(expected_sid)
            if prev is not None and key<=prev:
                raise ReplayOrderingError(
                    f"stream {e.stream_id} ordering key did not strictly increase: {key} <= {prev}"
                )
            last_keys[expected_sid]=key
            return e
        for sid,it in its.items():
            try:
                e=checked(sid,next(it));heapq.heappush(heap,(e.ordering_key,sid,e))
            except StopIteration:pass
        while heap:
            _,sid,e=heapq.heappop(heap);yield e
            try:
                n=checked(sid,next(its[sid]));heapq.heappush(heap,(n.ordering_key,sid,n))
            except StopIteration:pass

    def states(
        self,
        streams:dict[str,Iterable[VectorEvent]],
        *,
        required_streams:set[str]|None=None,
        require_available:bool=True,
        max_age_ns:int|None=None,
    )->Iterator[VectorStatePacket]:
        if max_age_ns is not None and max_age_ns<0:
            raise ValueError("max_age_ns must be non-negative or None")
        latest={}; required_streams=required_streams or set(); current=None;bucket=[]
        def packet(decision_ns:int,batch:list[VectorEvent]):
            for e in batch:latest[e.stream_id]=e
            visible={
                sid:e for sid,e in latest.items()
                if max_age_ns is None or decision_ns-int(e.event_ns)<=max_age_ns
            }
            values={sid:e.values() for sid,e in visible.items()}
            ages={sid:decision_ns-int(e.event_ns) for sid,e in visible.items()}
            stale=set(latest)-set(visible)
            missing=tuple(sorted((required_streams-set(visible))|stale))
            payload={"decision_ns":decision_ns,"streams":{sid:{"fields":values[sid],"sequence":visible[sid].source_sequence,
                "event_ns":visible[sid].event_ns,"available_ns":visible[sid].available_ns,"basis":visible[sid].availability_basis}
                for sid in sorted(values)}}
            h=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
            return VectorStatePacket(decision_ns,values,ages,missing,{sid:e.source_sequence for sid,e in visible.items()},
                {sid:e.source_path for sid,e in visible.items()},batch_size=len(batch),frame_hash=h)
        for e in self.merge(streams,require_available=require_available):
            if current is None:current=e.visible_ns
            if e.visible_ns!=current:
                yield packet(current,bucket);current=e.visible_ns;bucket=[]
            bucket.append(e)
        if bucket:yield packet(current,bucket)
