from __future__ import annotations
import csv, hashlib, io, math, zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable
from .catalog import _infer_cadence_counts
from .columns import profile_header
from .contracts import QualityFlag, StreamIdentity, StreamManifest
from .filename import parse_market_filename, timeframe_claim_to_ns
from .timeutil import timestamp_to_ns


def _member_sha(zf:zipfile.ZipFile,info:zipfile.ZipInfo)->str:
    h=hashlib.sha256()
    with zf.open(info,'r') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def _file_sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


class ZipCorpusCatalog:
    """Profile CSV members directly inside ZIP archives without extraction."""
    def __init__(self,root:str|Path):self.root=Path(root)

    def discover_archives(self)->list[Path]:
        return sorted(p for p in self.root.rglob('*.zip') if p.is_file())

    def _profile_member(self,archive:Path,zf:zipfile.ZipFile,info:zipfile.ZipInfo,archive_sha:str)->StreamManifest:
        member=PurePosixPath(info.filename); rel_archive=str(archive.relative_to(self.root)); source_path=f'{rel_archive}!{info.filename}'
        flags=[]
        if member.name.startswith('._') or '__MACOSX' in member.parts:flags.append(QualityFlag.APPLEDOUBLE.value)
        raw_hash=_member_sha(zf,info)
        parsed=parse_market_filename(Path(member.name)); ident=StreamIdentity('zipcsv',parsed.venue,parsed.symbol,parsed.timeframe_claim,'csv_export',source_path,raw_hash)
        base_meta={'filename_claim_is_authoritative':False,'archive_path':rel_archive,'archive_sha256':archive_sha,'archive_member':info.filename,'compressed_size':info.compress_size,'uncompressed_size':info.file_size}
        if QualityFlag.APPLEDOUBLE.value in flags:
            return StreamManifest(ident,0,[],None,None,None,0.0,0,0,0,None,flags,base_meta)
        frac=rows=usable=bad_ts=bad_num=bad_geom=0; min_ns=max_ns=prev=None; repeats=backwards=0; diffs=Counter(); columns=[]
        logical=hashlib.sha256();has_logical=False;duplicate_positions={}
        try:
            with zf.open(info,'r') as raw, io.TextIOWrapper(raw,encoding='utf-8-sig',errors='replace',newline='') as text:
                r=csv.reader(text);columns=next(r,[]);lower=[c.strip().lower() for c in columns]
                hp=profile_header(columns);duplicate_positions={k:list(v) for k,v in hp.duplicates.items()}
                if duplicate_positions:flags.append(QualityFlag.DUPLICATE_HEADER.value)
                logical.update(b'HEADER|');logical.update('|'.join(f'{i}:{str(c).strip().lower()}' for i,c in enumerate(columns)).encode());logical.update(b'\n')
                ti=next((i for i,c in enumerate(lower) if c=='time'),None);required=('open','high','low','close')
                idx={k:next((i for i,c in enumerate(lower) if c==k),None) for k in ('time',*required,'volume')}
                if not set(required).issubset(set(lower)):flags.append(QualityFlag.MISSING_OHLC.value)
                if ti is None:flags.append(QualityFlag.BAD_HEADER.value)
                else:
                    for row in r:
                        if not row or ti>=len(row):continue
                        try:ns,is_frac=timestamp_to_ns(row[ti])
                        except ValueError:bad_ts+=1;continue
                        min_ns=ns if min_ns is None else min(min_ns,ns);max_ns=ns if max_ns is None else max(max_ns,ns)
                        if prev is not None:
                            d=ns-prev
                            if d==0:repeats+=1
                            elif d<0:backwards+=1
                            else:diffs[d]+=1
                        prev=ns;frac+=int(is_frac);rows+=1
                        width=max(len(columns),len(row));norm=[]
                        for i in range(width):
                            cell=row[i].strip() if i<len(row) else '';norm.append(str(ns) if i==ti else cell)
                        logical.update('|'.join(norm).encode('utf-8',errors='replace'));logical.update(b'\n');has_logical=True
                        if all(idx[k] is not None and idx[k]<len(row) for k in required):
                            try:
                                o,h,lo,c=(float(row[idx[k]]) for k in required)
                                if not all(math.isfinite(v) for v in (o,h,lo,c)):raise ValueError
                                if h<max(o,c) or lo>min(o,c) or h<lo:
                                    bad_geom+=1
                                else:
                                    usable+=1
                            except (ValueError,TypeError):bad_num+=1
        except (OSError,UnicodeError,csv.Error):flags.append(QualityFlag.EMPTY.value)
        cadence,conf,repeats,backwards=_infer_cadence_counts(diffs,repeats,backwards)
        if repeats:flags.append(QualityFlag.REPEATED_TIME.value)
        if backwards:flags.append(QualityFlag.BACKWARD_TIME.value)
        if frac:flags.append(QualityFlag.FRACTIONAL_TIME.value)
        if bad_num:flags.append(QualityFlag.NON_NUMERIC.value)
        if bad_geom:flags.append(QualityFlag.OHLC_INCONSISTENT.value)
        if cadence is None or conf<.5:flags.append(QualityFlag.CADENCE_AMBIGUOUS.value)
        claim_ns=timeframe_claim_to_ns(parsed.timeframe_claim)
        if claim_ns and cadence and abs(cadence-claim_ns)/claim_ns>.05:flags.append(QualityFlag.CLAIM_MISMATCH.value)
        meta={**base_meta,'raw_filename_claim':parsed.raw_claim,'download_copy_ordinal':parsed.copy_ordinal,'claim_cadence_ns':claim_ns,
              'logical_sha256':logical.hexdigest() if has_logical else None,'duplicate_header_positions':duplicate_positions,
              'usable_ohlc_rows':usable,'invalid_timestamp_rows':bad_ts,'nonnumeric_ohlc_rows':bad_num,'inconsistent_ohlc_rows':bad_geom}
        manifest=StreamManifest(ident,rows,columns,min_ns,max_ns,cadence,conf,repeats,backwards,frac,None,sorted(set(flags)),meta)
        from .representation import infer_representation_claim, infer_representation_hypothesis
        rep=infer_representation_claim(manifest)
        manifest.metadata['representation_claim']=rep.to_dict()
        hyp=infer_representation_hypothesis(manifest)
        manifest.metadata['representation_hypothesis']={'kind':hyp.kind,'confidence':hyp.confidence,'reasons':list(hyp.reasons),'authoritative':False}
        return manifest

    @staticmethod
    def _annotate(manifests:list[StreamManifest])->list[StreamManifest]:
        raw_seen={};logical_seen={}
        for m in manifests:
            rh=m.identity.raw_sha256;path=m.identity.source_path
            if rh in raw_seen:
                m.byte_duplicate_of=raw_seen[rh];m.quality_flags=sorted(set(m.quality_flags+[QualityFlag.EXACT_BYTE_DUPLICATE.value]))
            else:raw_seen[rh]=path
            lh=m.metadata.get('logical_sha256')
            if lh:
                if lh in logical_seen and m.byte_duplicate_of is None:
                    m.metadata['logical_duplicate_of']=logical_seen[lh];m.quality_flags=sorted(set(m.quality_flags+[QualityFlag.LOGICAL_DUPLICATE.value]))
                else:logical_seen.setdefault(lh,path)
        return manifests

    def build(self)->list[StreamManifest]:
        out=[]
        for archive in self.discover_archives():
            archive_sha=_file_sha(archive)
            with zipfile.ZipFile(archive) as zf:
                for info in sorted(zf.infolist(),key=lambda x:x.filename):
                    if info.is_dir() or not info.filename.lower().endswith('.csv'):continue
                    out.append(self._profile_member(archive,zf,info,archive_sha))
        return self._annotate(out)
