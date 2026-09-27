from __future__ import annotations
import hashlib, heapq, json
from typing import Iterable, Iterator
from .contracts import BarEvent, ReplayBatch, ReplayInstant, StatePacket

class ReplayAvailabilityError(ValueError):
    pass

class ReplayBus:
    """Causal deterministic merge with optional batch-atomic same-availability replay."""
    def merge(self, streams: dict[str, Iterable[BarEvent]], *, require_available: bool=False) -> Iterator[BarEvent]:
        heap=[]; its={k:iter(v) for k,v in streams.items()}
        def checked(event:BarEvent)->BarEvent:
            if require_available and event.available_ns is None:
                raise ReplayAvailabilityError(f"stream {event.stream_id} sequence {event.source_sequence} has unknown availability")
            return event
        for sid,it in its.items():
            try:
                e=checked(next(it)); heapq.heappush(heap,(e.ordering_key,sid,e))
            except StopIteration: pass
        while heap:
            _,sid,e=heapq.heappop(heap)
            yield e
            try:
                n=checked(next(its[sid])); heapq.heappush(heap,(n.ordering_key,sid,n))
            except StopIteration: pass

    def merge_batches(self, streams: dict[str, Iterable[BarEvent]], *, require_available: bool=False) -> Iterator[ReplayBatch]:
        current_ns=None; bucket=[]
        for event in self.merge(streams, require_available=require_available):
            if current_ns is None: current_ns=event.visible_ns
            if event.visible_ns != current_ns:
                yield ReplayBatch(current_ns, tuple(bucket))
                current_ns=event.visible_ns; bucket=[]
            bucket.append(event)
        if bucket:
            yield ReplayBatch(current_ns, tuple(bucket))

    @staticmethod
    def _frame_hash(decision_ns:int, latest:dict[str,BarEvent], values:dict[str,float]) -> str:
        payload={
            "decision_ns":int(decision_ns),
            "streams":{
                sid:{"close":values[sid],"sequence":latest[sid].source_sequence,"revision":latest[sid].revision,
                     "event_ns":latest[sid].event_ns,"available_ns":latest[sid].available_ns,
                    "visible_ns":latest[sid].visible_ns,"source_path":latest[sid].source_path,
                    "source_timestamp_ns":latest[sid].source_timestamp_ns,
                    "availability_basis":latest[sid].availability_basis,
                    "quality_flags":list(latest[sid].quality_flags),
                    "data_plane":latest[sid].data_plane}
                for sid in sorted(values)
            },
        }
        raw=json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
        return hashlib.sha256(raw).hexdigest()

    def _packet(self, decision_ns:int, latest:dict[str,BarEvent], required_streams:set[str], max_age_ns:int|None, batch_size:int) -> StatePacket:
        missing=tuple(sorted(required_streams-set(latest)))
        values={sid:e.close for sid,e in latest.items() if max_age_ns is None or decision_ns-e.event_ns <= max_age_ns}
        ages={sid:max(0,decision_ns-e.event_ns) for sid,e in latest.items() if sid in values}
        stale=set(latest)-set(values)
        all_missing=tuple(sorted(set(missing)|stale))
        return StatePacket(
            decision_ns=decision_ns, values=values, ages_ns=ages, missing=all_missing,
            source_sequences={sid:e.source_sequence for sid,e in latest.items() if sid in values},
            lineage={sid:e.source_path for sid,e in latest.items() if sid in values},
            batch_size=batch_size, frame_hash=self._frame_hash(decision_ns,latest,values),
        )

    def states(self, merged: Iterable[BarEvent], required_streams: set[str] | None=None, max_age_ns: int | None=None):
        latest: dict[str,BarEvent]={}; required_streams=required_streams or set()
        for event in merged:
            latest[event.stream_id]=event
            yield self._packet(event.visible_ns,latest,required_streams,max_age_ns,1)

    def states_batches(self, batches: Iterable[ReplayBatch], required_streams:set[str]|None=None, max_age_ns:int|None=None):
        """Emit exactly one state per visibility instant after all simultaneous events are applied."""
        latest:dict[str,BarEvent]={}; required_streams=required_streams or set()
        for batch in batches:
            for event in batch.events:
                latest[event.stream_id]=event
            yield self._packet(batch.visible_ns,latest,required_streams,max_age_ns,len(batch.events))

    def instants(
        self,
        streams: dict[str, Iterable[BarEvent]],
        *,
        required_streams: set[str] | None = None,
        max_age_ns: int | None = None,
        require_available: bool = False,
    ) -> Iterator[ReplayInstant]:
        """Canonical atomic replay path: one batch and exactly one post-batch state.

        Consumers that need same-instant sibling routing should use this method rather
        than independently zipping ``merge_batches`` and ``states_batches``.
        """
        latest: dict[str, BarEvent] = {}
        required = required_streams or set()
        for batch in self.merge_batches(streams, require_available=require_available):
            for event in batch.events:
                latest[event.stream_id] = event
            state = self._packet(batch.visible_ns, latest, required, max_age_ns, len(batch.events))
            yield ReplayInstant(batch=batch, state=state)
