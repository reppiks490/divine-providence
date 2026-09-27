from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Iterable, Iterator

import numpy as np

from .contracts import BarEvent


COLUMNS=(
    "event_ns","available_ns","source_sequence","open","high","low","close","volume",
    "revision","source_timestamp_ns","stream_id","source_path","data_plane","availability_basis","quality_flags",
)


def _safe_partition(stream_id:str)->str:
    prefix=re.sub(r"[^A-Za-z0-9_.-]+","_",stream_id)[:80].strip("_") or "stream"
    suffix=hashlib.sha256(stream_id.encode()).hexdigest()[:12]
    return f"{prefix}__{suffix}"


def _digest_arrays(columns:dict[str,np.ndarray])->str:
    h=hashlib.sha256()
    for name in sorted(columns):
        arr=columns[name]
        h.update(name.encode()+b"\0")
        h.update(str(arr.dtype).encode()+b"\0")
        h.update(str(arr.shape).encode()+b"\0")
        if arr.dtype.kind in "OUSU":
            for value in arr.tolist():
                h.update(str(value).encode("utf-8",errors="replace")+b"\0")
        else:
            h.update(np.ascontiguousarray(arr).tobytes())
    return h.hexdigest()


@dataclass(frozen=True, slots=True)
class ColumnarPartitionManifest:
    stream_id:str
    partition:str
    rows:int
    first_visible_ns:int|None
    last_visible_ns:int|None
    content_sha256:str


@dataclass(frozen=True, slots=True)
class ColumnarStoreManifest:
    version:str
    backend:str
    partitions:tuple[ColumnarPartitionManifest,...]
    rows:int
    content_sha256:str

    def to_dict(self)->dict:
        return {
            "version":self.version,"backend":self.backend,
            "partitions":[asdict(x) for x in self.partitions],"rows":self.rows,
            "content_sha256":self.content_sha256,
        }


class NpyColumnarBarStore:
    """Dependency-light partitioned column store using mmap-friendly NPY arrays.

    This is the deterministic staging backend when Arrow/Parquet is unavailable.
    It does not replace the planned Parquet backend; it gives NEXUS a real
    columnar, partitioned, content-addressed persistence layer now.
    """
    VERSION="nexus.columnar.npy.v1"

    def __init__(self, root:str|Path):
        self.root=Path(root)

    @staticmethod
    def _arrays(events:list[BarEvent])->dict[str,np.ndarray]:
        q=[json.dumps(list(e.quality_flags),separators=(",",":")) for e in events]
        return {
            "event_ns":np.asarray([e.event_ns for e in events],dtype=np.int64),
            "available_ns":np.asarray([e.available_ns if e.available_ns is not None else -1 for e in events],dtype=np.int64),
            "source_sequence":np.asarray([e.source_sequence for e in events],dtype=np.int64),
            "open":np.asarray([e.open for e in events],dtype=np.float64),
            "high":np.asarray([e.high for e in events],dtype=np.float64),
            "low":np.asarray([e.low for e in events],dtype=np.float64),
            "close":np.asarray([e.close for e in events],dtype=np.float64),
            "volume":np.asarray([np.nan if e.volume is None else e.volume for e in events],dtype=np.float64),
            "revision":np.asarray([e.revision for e in events],dtype=np.int32),
            "source_timestamp_ns":np.asarray([e.source_timestamp_ns if e.source_timestamp_ns is not None else -1 for e in events],dtype=np.int64),
            "stream_id":np.asarray([e.stream_id for e in events],dtype=np.str_),
            "source_path":np.asarray([e.source_path for e in events],dtype=np.str_),
            "data_plane":np.asarray([e.data_plane for e in events],dtype=np.str_),
            "availability_basis":np.asarray([e.availability_basis for e in events],dtype=np.str_),
            "quality_flags":np.asarray(q,dtype=np.str_),
        }

    def write(self, events:Iterable[BarEvent]) -> ColumnarStoreManifest:
        grouped:dict[str,list[BarEvent]]={}
        for e in events: grouped.setdefault(e.stream_id,[]).append(e)
        self.root.mkdir(parents=True,exist_ok=True)
        manifests=[]
        for sid in sorted(grouped):
            evs=sorted(grouped[sid],key=lambda e:e.ordering_key)
            arrays=self._arrays(evs); part=_safe_partition(sid); d=self.root/part; d.mkdir(parents=True,exist_ok=True)
            for name,arr in arrays.items(): np.save(d/f"{name}.npy",arr,allow_pickle=False)
            digest=_digest_arrays(arrays)
            visible=[e.visible_ns for e in evs]
            pm=ColumnarPartitionManifest(sid,part,len(evs),min(visible) if visible else None,max(visible) if visible else None,digest)
            (d/"partition.json").write_text(json.dumps(asdict(pm),sort_keys=True,indent=2),encoding="utf-8")
            manifests.append(pm)
        canonical=json.dumps([asdict(x) for x in manifests],sort_keys=True,separators=(",",":")).encode()
        manifest=ColumnarStoreManifest(self.VERSION,"npy",tuple(manifests),sum(x.rows for x in manifests),hashlib.sha256(canonical).hexdigest())
        (self.root/"manifest.json").write_text(json.dumps(manifest.to_dict(),sort_keys=True,indent=2),encoding="utf-8")
        return manifest

    def write_streams(self, streams:dict[str,Iterable[BarEvent]]) -> ColumnarStoreManifest:
        """Persist one stream at a time so memory does not scale with total corpus rows."""
        self.root.mkdir(parents=True,exist_ok=True);manifests=[]
        for sid in sorted(streams):
            evs=list(streams[sid])
            if any(e.stream_id!=sid for e in evs):raise ValueError(f"stream mapping key {sid!r} does not match event stream_id")
            evs.sort(key=lambda e:e.ordering_key);arrays=self._arrays(evs);part=_safe_partition(sid);d=self.root/part;d.mkdir(parents=True,exist_ok=True)
            for name,arr in arrays.items():np.save(d/f"{name}.npy",arr,allow_pickle=False)
            digest=_digest_arrays(arrays);visible=[e.visible_ns for e in evs]
            pm=ColumnarPartitionManifest(sid,part,len(evs),min(visible) if visible else None,max(visible) if visible else None,digest)
            (d/"partition.json").write_text(json.dumps(asdict(pm),sort_keys=True,indent=2),encoding="utf-8");manifests.append(pm)
        canonical=json.dumps([asdict(x) for x in manifests],sort_keys=True,separators=(",",":")).encode()
        manifest=ColumnarStoreManifest(self.VERSION,"npy",tuple(manifests),sum(x.rows for x in manifests),hashlib.sha256(canonical).hexdigest())
        (self.root/"manifest.json").write_text(json.dumps(manifest.to_dict(),sort_keys=True,indent=2),encoding="utf-8")
        return manifest

    def iter_stream(self, stream_id:str, *, mmap:bool=True) -> Iterator[BarEvent]:
        manifest=json.loads((self.root/"manifest.json").read_text(encoding="utf-8"))
        entry=next((x for x in manifest["partitions"] if x["stream_id"]==stream_id),None)
        if entry is None: raise KeyError(stream_id)
        d=self.root/entry["partition"]; mode="r" if mmap else None
        a={name:np.load(d/f"{name}.npy",mmap_mode=mode,allow_pickle=False) for name in COLUMNS}
        for i in range(entry["rows"]):
            vol=float(a["volume"][i]); available=int(a["available_ns"][i]); source_ts=int(a["source_timestamp_ns"][i])
            yield BarEvent(
                str(a["stream_id"][i]),int(a["event_ns"][i]),int(a["source_sequence"][i]),
                float(a["open"][i]),float(a["high"][i]),float(a["low"][i]),float(a["close"][i]),
                None if np.isnan(vol) else vol,str(a["source_path"][i]),str(a["data_plane"][i]),
                tuple(json.loads(str(a["quality_flags"][i]))),None if available<0 else available,
                int(a["revision"][i]),None if source_ts<0 else source_ts,str(a["availability_basis"][i]),
            )

    def verify(self)->bool:
        manifest=json.loads((self.root/"manifest.json").read_text(encoding="utf-8"))
        parts=[]
        for entry in manifest["partitions"]:
            d=self.root/entry["partition"]
            arrays={name:np.load(d/f"{name}.npy",allow_pickle=False) for name in COLUMNS}
            if _digest_arrays(arrays)!=entry["content_sha256"]: return False
            parts.append({k:entry[k] for k in ("stream_id","partition","rows","first_visible_ns","last_visible_ns","content_sha256")})
        canonical=json.dumps(parts,sort_keys=True,separators=(",",":")).encode()
        return hashlib.sha256(canonical).hexdigest()==manifest["content_sha256"]


class ParquetBarStore:
    """Optional streaming Arrow/Parquet backend partitioned by stable stream identity."""
    VERSION="nexus.columnar.parquet.v2"

    @staticmethod
    def available()->bool:
        try:
            import pyarrow  # noqa:F401
            return True
        except ImportError:
            return False

    def __init__(self,root:str|Path):
        self.root=Path(root)

    @staticmethod
    def _require_arrow():
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
            return pa,pq
        except ImportError as exc:
            raise RuntimeError("pyarrow is required for ParquetBarStore; use NpyColumnarBarStore or SQLiteBarStore otherwise") from exc

    def write_streams(self,streams:dict[str,Iterable[BarEvent]],*,chunk_rows:int=100_000)->dict:
        if chunk_rows<=0:raise ValueError("chunk_rows must be positive")
        pa,pq=self._require_arrow();self.root.mkdir(parents=True,exist_ok=True);parts=[]
        for sid in sorted(streams):
            part=_safe_partition(sid);d=self.root/part;d.mkdir(parents=True,exist_ok=True);path=d/"bars.parquet"
            writer=None;buf=[];rows=0;first=None;last=None
            try:
                for e in streams[sid]:
                    if e.stream_id!=sid:raise ValueError(f"stream mapping key {sid!r} does not match event stream_id")
                    v=e.visible_ns;first=v if first is None else min(first,v);last=v if last is None else max(last,v);rows+=1
                    row=asdict(e);row["quality_flags"]=list(e.quality_flags);buf.append(row)
                    if len(buf)>=chunk_rows:
                        table=pa.Table.from_pylist(buf);writer=writer or pq.ParquetWriter(path,table.schema,compression="zstd");writer.write_table(table);buf=[]
                if buf:
                    table=pa.Table.from_pylist(buf);writer=writer or pq.ParquetWriter(path,table.schema,compression="zstd");writer.write_table(table)
            finally:
                if writer is not None:writer.close()
            if rows==0:
                continue
            fh=hashlib.sha256(path.read_bytes()).hexdigest()
            parts.append({"stream_id":sid,"partition":part,"path":f"{part}/bars.parquet","rows":rows,"first_visible_ns":first,"last_visible_ns":last,"file_sha256":fh})
        canonical=json.dumps(parts,sort_keys=True,separators=(",",":")).encode();manifest={"version":self.VERSION,"backend":"parquet","partitions":parts,"rows":sum(x["rows"] for x in parts),"content_sha256":hashlib.sha256(canonical).hexdigest()}
        (self.root/"manifest.json").write_text(json.dumps(manifest,sort_keys=True,indent=2),encoding="utf-8");return manifest

    def write(self,events:Iterable[BarEvent]):
        grouped:dict[str,list[BarEvent]]={}
        for e in events:grouped.setdefault(e.stream_id,[]).append(e)
        return self.write_streams(grouped)

    def iter_stream(self,stream_id:str,*,batch_size:int=65_536)->Iterator[BarEvent]:
        _,pq=self._require_arrow();manifest=json.loads((self.root/"manifest.json").read_text(encoding="utf-8"));entry=next((x for x in manifest["partitions"] if x["stream_id"]==stream_id),None)
        if entry is None:raise KeyError(stream_id)
        pf=pq.ParquetFile(self.root/entry["path"])
        for batch in pf.iter_batches(batch_size=batch_size):
            for r in batch.to_pylist():
                yield BarEvent(r["stream_id"],int(r["event_ns"]),int(r["source_sequence"]),float(r["open"]),float(r["high"]),float(r["low"]),float(r["close"]),
                    None if r["volume"] is None else float(r["volume"]),r["source_path"],r["data_plane"],tuple(r.get("quality_flags") or ()),
                    None if r["available_ns"] is None else int(r["available_ns"]),int(r["revision"]),None if r["source_timestamp_ns"] is None else int(r["source_timestamp_ns"]),r["availability_basis"])

    def verify(self)->bool:
        manifest=json.loads((self.root/"manifest.json").read_text(encoding="utf-8"));parts=[]
        for e in manifest["partitions"]:
            path=self.root/e["path"]
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=e["file_sha256"]:return False
            parts.append(e)
        canonical=json.dumps(parts,sort_keys=True,separators=(",",":")).encode();return hashlib.sha256(canonical).hexdigest()==manifest["content_sha256"]


class SQLiteBarStore:
    """Appendable deterministic BarEvent store using the standard-library SQLite engine."""

    SCHEMA_VERSION="nexus.sqlite-bars.v1"

    def __init__(self,path:str|Path):
        import sqlite3
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self._sqlite3=sqlite3
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS bars(
                stream_id TEXT NOT NULL,event_ns INTEGER NOT NULL,available_ns INTEGER,
                source_sequence INTEGER NOT NULL,open REAL NOT NULL,high REAL NOT NULL,low REAL NOT NULL,close REAL NOT NULL,
                volume REAL,source_path TEXT NOT NULL,data_plane TEXT NOT NULL,quality_flags TEXT NOT NULL,
                revision INTEGER NOT NULL,source_timestamp_ns INTEGER,availability_basis TEXT NOT NULL,
                PRIMARY KEY(stream_id,source_sequence,revision)
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS bars_visibility ON bars(stream_id,available_ns,event_ns,source_sequence,revision)")

    def _connect(self):
        db=self._sqlite3.connect(self.path)
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        return db

    @staticmethod
    def _row(e:BarEvent):
        return (e.stream_id,int(e.event_ns),None if e.available_ns is None else int(e.available_ns),int(e.source_sequence),
                float(e.open),float(e.high),float(e.low),float(e.close),None if e.volume is None else float(e.volume),
                e.source_path,e.data_plane,json.dumps(list(e.quality_flags),separators=(",",":")),int(e.revision),
                None if e.source_timestamp_ns is None else int(e.source_timestamp_ns),e.availability_basis)

    def append(self,events:Iterable[BarEvent],*,replace_same_revision:bool=False)->int:
        sql=("INSERT OR REPLACE" if replace_same_revision else "INSERT")+" INTO bars VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        n=0
        with self._connect() as db:
            for e in events:
                db.execute(sql,self._row(e));n+=1
        return n

    def iter_stream(self,stream_id:str)->Iterator[BarEvent]:
        sql="""SELECT stream_id,event_ns,source_sequence,open,high,low,close,volume,source_path,data_plane,quality_flags,
                      available_ns,revision,source_timestamp_ns,availability_basis
               FROM bars WHERE stream_id=?
               ORDER BY COALESCE(available_ns,event_ns),stream_id,source_sequence,revision"""
        with self._connect() as db:
            for r in db.execute(sql,(stream_id,)):
                yield BarEvent(r[0],int(r[1]),int(r[2]),float(r[3]),float(r[4]),float(r[5]),float(r[6]),
                    None if r[7] is None else float(r[7]),r[8],r[9],tuple(json.loads(r[10])),
                    None if r[11] is None else int(r[11]),int(r[12]),None if r[13] is None else int(r[13]),r[14])

    def stream_ids(self)->tuple[str,...]:
        with self._connect() as db:
            return tuple(r[0] for r in db.execute("SELECT DISTINCT stream_id FROM bars ORDER BY stream_id"))

    def content_sha256(self,stream_id:str|None=None)->str:
        h=hashlib.sha256();ids=(stream_id,) if stream_id is not None else self.stream_ids()
        for sid in ids:
            for e in self.iter_stream(sid):
                payload={
                    "stream_id":e.stream_id,"event_ns":e.event_ns,"available_ns":e.available_ns,"source_sequence":e.source_sequence,
                    "open":e.open,"high":e.high,"low":e.low,"close":e.close,"volume":e.volume,"source_path":e.source_path,
                    "data_plane":e.data_plane,"quality_flags":list(e.quality_flags),"revision":e.revision,
                    "source_timestamp_ns":e.source_timestamp_ns,"availability_basis":e.availability_basis,
                }
                h.update(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False).encode()+b"\n")
        return h.hexdigest()
