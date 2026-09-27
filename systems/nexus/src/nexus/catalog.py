from __future__ import annotations
import csv, hashlib, math
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import median
from .contracts import StreamIdentity, StreamManifest, QualityFlag
from .timeutil import timestamp_to_ns
from .filename import parse_market_filename, timeframe_claim_to_ns
from .columns import profile_header

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def parse_filename(path: Path) -> tuple[str | None, str, str | None]:
    parsed = parse_market_filename(path)
    return parsed.venue, parsed.symbol, parsed.timeframe_claim

def _weighted_median(counts: Counter[int]) -> int | None:
    total=sum(counts.values())
    if total<=0: return None
    # Match statistics.median semantics for integer samples.
    left_rank=(total-1)//2; right_rank=total//2
    seen=0; left=None; right=None
    for value,n in sorted(counts.items()):
        nxt=seen+n
        if left is None and left_rank < nxt: left=value
        if right is None and right_rank < nxt:
            right=value; break
        seen=nxt
    if left is None or right is None: return None
    return int((left+right)/2)

def _infer_cadence_counts(pos_counts:Counter[int], repeats:int=0, backwards:int=0) -> tuple[int | None,float,int,int]:
    total_pos=sum(pos_counts.values())
    if total_pos<=0: return None,0.0,repeats,backwards
    med=_weighted_median(pos_counts)
    if med is None: return None,0.0,repeats,backwards
    tol=max(1,int(med*0.02))
    buckets=Counter()
    by_bucket:dict[int,Counter[int]]={}
    for d,n in pos_counts.items():
        b=int(round(d/tol)); buckets[b]+=n; by_bucket.setdefault(b,Counter())[d]+=n
    winning,n=buckets.most_common(1)[0]
    cadence=_weighted_median(by_bucket[winning])
    return cadence,float(n/total_pos),repeats,backwards

def infer_cadence_ns(times: list[int]) -> tuple[int | None, float, int, int]:
    if len(times)<2: return None,0.0,0,0
    pos=Counter(); repeats=0; backwards=0
    for a,b in zip(times,times[1:]):
        d=b-a
        if d==0: repeats+=1
        elif d<0: backwards+=1
        else: pos[d]+=1
    return _infer_cadence_counts(pos,repeats,backwards)

def _logical_digest(rows:list[tuple[str,...]]) -> str:
    h=hashlib.sha256()
    for row in rows:
        h.update("|".join(row).encode("utf-8",errors="replace")); h.update(b"\n")
    return h.hexdigest()

class CorpusCatalog:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def discover(self) -> list[Path]:
        return sorted(p for p in self.root.rglob("*.csv") if p.is_file())

    def _profile_raw(self, path:Path) -> StreamManifest:
        rel = str(path.relative_to(self.root)); flags:list[str]=[]
        if path.name.startswith("._") or "__MACOSX" in path.parts:
            flags.append(QualityFlag.APPLEDOUBLE.value)
        raw_hash=_sha256(path)
        parsed_name=parse_market_filename(path)
        venue,symbol,claim=parsed_name.venue,parsed_name.symbol,parsed_name.timeframe_claim
        identity=StreamIdentity("csv",venue,symbol,claim,"csv_export",rel,raw_hash)
        if QualityFlag.APPLEDOUBLE.value in flags:
            return StreamManifest(identity,0,[],None,None,None,0.0,0,0,0,None,flags,{"filename_claim_is_authoritative":False})
        frac=0; columns=[]; rows=0; usable_ohlc_rows=0
        invalid_timestamp_rows=0; nonnumeric_ohlc_rows=0; inconsistent_ohlc_rows=0
        logical_hasher=hashlib.sha256(); has_logical=False
        min_ns=None; max_ns=None; prev_ns=None
        repeats=0; backwards=0; positive_diffs=Counter()
        try:
            with path.open("r",encoding="utf-8-sig",errors="replace",newline="") as f:
                reader=csv.reader(f); columns=next(reader,[])
                if not columns: flags.append(QualityFlag.EMPTY.value)
                lower=[c.strip().lower() for c in columns]
                # Include positional header identity in the logical digest; duplicate names remain distinct by position.
                logical_hasher.update("HEADER|".encode())
                logical_hasher.update("|".join(f"{i}:{str(c).strip().lower()}" for i,c in enumerate(columns)).encode("utf-8",errors="replace"))
                logical_hasher.update(b"\n")
                header_profile=profile_header(columns)
                duplicate_positions={k:list(v) for k,v in header_profile.duplicates.items()}
                if duplicate_positions: flags.append(QualityFlag.DUPLICATE_HEADER.value)
                time_idx=next((i for i,c in enumerate(lower) if c=="time"),None)
                required=("open","high","low","close")
                idx={k:next((i for i,c in enumerate(lower) if c==k),None) for k in ("time",*required,"volume")}
                if not set(required).issubset(set(lower)): flags.append(QualityFlag.MISSING_OHLC.value)
                if time_idx is None: flags.append(QualityFlag.BAD_HEADER.value)
                else:
                    for row in reader:
                        if not row or time_idx>=len(row): continue
                        try: ns,is_frac=timestamp_to_ns(row[time_idx])
                        except ValueError:
                            invalid_timestamp_rows+=1
                            continue
                        min_ns=ns if min_ns is None else min(min_ns,ns)
                        max_ns=ns if max_ns is None else max(max_ns,ns)
                        if prev_ns is not None:
                            d=ns-prev_ns
                            if d==0: repeats+=1
                            elif d<0: backwards+=1
                            else: positive_diffs[d]+=1
                        prev_ns=ns
                        frac+=int(is_frac); rows+=1
                        width=max(len(columns),len(row)); normalized=[]
                        for i in range(width):
                            cell=row[i].strip() if i<len(row) else ""
                            normalized.append(str(ns) if i==time_idx else cell)
                        logical_hasher.update("|".join(normalized).encode("utf-8",errors="replace")); logical_hasher.update(b"\n"); has_logical=True
                        if all(idx[k] is not None and idx[k] < len(row) for k in required):
                            try:
                                o,h,lo,c=(float(row[idx[k]]) for k in required)
                                if not all(math.isfinite(v) for v in (o,h,lo,c)): raise ValueError
                                if h < max(o,c) or lo > min(o,c) or h < lo: inconsistent_ohlc_rows+=1
                                else: usable_ohlc_rows+=1
                            except (ValueError,TypeError):
                                nonnumeric_ohlc_rows+=1
        except OSError:
            flags.append(QualityFlag.EMPTY.value)
        cadence,confidence,repeats,backwards=_infer_cadence_counts(positive_diffs,repeats,backwards)
        if repeats: flags.append(QualityFlag.REPEATED_TIME.value)
        if backwards: flags.append(QualityFlag.BACKWARD_TIME.value)
        if frac: flags.append(QualityFlag.FRACTIONAL_TIME.value)
        if nonnumeric_ohlc_rows: flags.append(QualityFlag.NON_NUMERIC.value)
        if inconsistent_ohlc_rows: flags.append(QualityFlag.OHLC_INCONSISTENT.value)
        if cadence is None or confidence<0.5: flags.append(QualityFlag.CADENCE_AMBIGUOUS.value)
        claim_ns=timeframe_claim_to_ns(claim)
        if claim_ns and cadence and abs(cadence-claim_ns)/claim_ns > 0.05:
            flags.append(QualityFlag.CLAIM_MISMATCH.value)
        logical_hash=logical_hasher.hexdigest() if has_logical else None
        manifest=StreamManifest(
            identity,row_count=rows,columns=columns,first_event_ns=min_ns,last_event_ns=max_ns,
            observed_cadence_ns=cadence,cadence_confidence=confidence,repeated_timestamp_count=repeats,backward_timestamp_count=backwards,
            fractional_timestamp_count=frac,quality_flags=sorted(set(flags)),
            metadata={
                "filename_claim_is_authoritative":False,
                "raw_filename_claim":parsed_name.raw_claim,
                "download_copy_ordinal":parsed_name.copy_ordinal,
                "claim_cadence_ns":claim_ns,
                "logical_sha256":logical_hash,
                "header_sha256":hashlib.sha256("|".join(f"{i}:{str(c).strip().lower()}" for i,c in enumerate(columns)).encode("utf-8",errors="replace")).hexdigest() if columns else None,
                "duplicate_header_positions":duplicate_positions if columns else {},
                "usable_ohlc_rows":usable_ohlc_rows,
                "invalid_timestamp_rows":invalid_timestamp_rows,
                "nonnumeric_ohlc_rows":nonnumeric_ohlc_rows,
                "inconsistent_ohlc_rows":inconsistent_ohlc_rows,
            },
        )
        from .representation import infer_representation_hypothesis
        hyp=infer_representation_hypothesis(manifest)
        manifest.metadata["representation_hypothesis"]={"kind":hyp.kind,"confidence":hyp.confidence,"reasons":list(hyp.reasons),"authoritative":False}
        return manifest

    def _annotate_duplicates(self, manifests:list[StreamManifest]) -> list[StreamManifest]:
        seen_raw={}; seen_logical={}
        for m in manifests:
            rel=m.identity.source_path
            rh=m.identity.raw_sha256
            if rh in seen_raw:
                m.byte_duplicate_of=seen_raw[rh]; m.quality_flags=sorted(set(m.quality_flags+[QualityFlag.EXACT_BYTE_DUPLICATE.value]))
            else: seen_raw[rh]=rel
            lh=m.metadata.get("logical_sha256")
            if lh:
                if lh in seen_logical and m.byte_duplicate_of is None:
                    m.metadata["logical_duplicate_of"]=seen_logical[lh]
                    m.quality_flags=sorted(set(m.quality_flags+[QualityFlag.LOGICAL_DUPLICATE.value]))
                else: seen_logical.setdefault(lh,rel)
        return manifests

    def profile(self, path: Path, seen_hashes: dict[str, str] | None = None) -> StreamManifest:
        # Backward-compatible single-file entry point.
        m=self._profile_raw(path)
        if seen_hashes is not None:
            rh=m.identity.raw_sha256; rel=m.identity.source_path
            if rh in seen_hashes:
                m.byte_duplicate_of=seen_hashes[rh]
                m.quality_flags=sorted(set(m.quality_flags+[QualityFlag.EXACT_BYTE_DUPLICATE.value]))
            else: seen_hashes[rh]=rel
        return m

    def build(self) -> list[StreamManifest]:
        return self._annotate_duplicates([self._profile_raw(p) for p in self.discover()])

    def build_parallel(self, workers:int=4) -> list[StreamManifest]:
        paths=self.discover()
        with ThreadPoolExecutor(max_workers=max(1,int(workers))) as ex:
            manifests=list(ex.map(self._profile_raw,paths))
        manifests.sort(key=lambda m:m.identity.source_path)
        return self._annotate_duplicates(manifests)
