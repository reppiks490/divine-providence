from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable,Iterator,Protocol,runtime_checkable
from .contracts import BarEvent,StreamManifest
from .ingest import BarClockPolicy,iter_bars,iter_bars_streaming

@runtime_checkable
class MarketSource(Protocol):
    @property
    def manifest(self)->StreamManifest: ...
    def events(self)->Iterable[BarEvent]: ...

@dataclass
class CSVMarketSource:
    _manifest:StreamManifest;clock_policy:BarClockPolicy;emit_unsealed_terminal:bool=False;root:Path|None=None;streaming:bool=True
    @property
    def manifest(self)->StreamManifest:return self._manifest
    def events(self)->Iterable[BarEvent]:
        p=Path(self._manifest.identity.source_path)
        if self.root is not None and not p.is_absolute():p=self.root/p
        reader=iter_bars_streaming if self.streaming and self._manifest.backward_timestamp_count==0 else iter_bars
        return reader(p,self._manifest.identity.stream_id,clock_policy=self.clock_policy,emit_unsealed_terminal=self.emit_unsealed_terminal)

@dataclass
class IterableMarketSource:
    _manifest:StreamManifest;_events:Iterable[BarEvent]
    @property
    def manifest(self)->StreamManifest:return self._manifest
    def events(self)->Iterator[BarEvent]:yield from self._events

@dataclass
class SQLiteMarketSource:
    """MarketSource adapter over an appendable SQLiteBarStore."""
    _manifest:StreamManifest
    store_path:Path
    @property
    def manifest(self)->StreamManifest:return self._manifest
    def events(self)->Iterable[BarEvent]:
        from .storage import SQLiteBarStore
        return SQLiteBarStore(self.store_path).iter_stream(self._manifest.identity.stream_id)

@dataclass
class NpyMarketSource:
    """MarketSource adapter over a deterministic NPY columnar store."""
    _manifest:StreamManifest
    store_root:Path
    @property
    def manifest(self)->StreamManifest:return self._manifest
    def events(self)->Iterable[BarEvent]:
        from .storage import NpyColumnarBarStore
        return NpyColumnarBarStore(self.store_root).iter_stream(self._manifest.identity.stream_id)
