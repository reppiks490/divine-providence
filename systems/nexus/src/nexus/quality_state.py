from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping
import hashlib,json,math
from .contracts import StatePacket, StreamManifest
from .quality import dynamic_state_quality, quality_score

@dataclass(frozen=True)
class StreamQualityState:
    stream_id:str;present:bool;age_ns:int|None;cadence_ns:int|None;base_quality:float;dynamic_quality:float
    stale_ratio:float|None;clock_uncertainty_ns:int;stale:bool;quality_flags:tuple[str,...]=()

@dataclass(frozen=True)
class QualityPlane:
    decision_ns:int;streams:Mapping[str,StreamQualityState];coverage:float;mean_quality:float;min_quality:float
    missing_count:int;stale_fraction:float=0.0;uncertain_clock_fraction:float=0.0;missingness_pattern_id:str=""

class QualityStateEngine:
    """Time-varying data-health plane; missingness remains telemetry, never imputed truth."""
    def build(self,packet:StatePacket,manifests:Mapping[str,StreamManifest],*,clock_uncertainty_ns:Mapping[str,int]|None=None,stale_after_multiples:float=2.0)->QualityPlane:
        if not isinstance(packet,StatePacket):
            raise TypeError("packet must be StatePacket")
        if not isinstance(manifests,Mapping):
            raise TypeError("manifests must be a mapping")
        stale=float(stale_after_multiples)
        if not math.isfinite(stale) or stale<=0:
            raise ValueError("stale_after_multiples must be finite and positive")
        if clock_uncertainty_ns is not None and not isinstance(clock_uncertainty_ns,Mapping):
            raise TypeError("clock_uncertainty_ns must be a mapping or None")
        clock_uncertainty_ns=clock_uncertainty_ns or {};all_ids=sorted(set(manifests)|set(packet.values)|set(packet.missing));states={};stale_ids=[];uncertain=0
        for sid in all_ids:
            m=manifests.get(sid);base=quality_score(m) if m is not None else 0.0;cadence=m.observed_cadence_ns if m is not None else None
            age=packet.ages_ns.get(sid);present=sid in packet.values and age is not None
            raw_unc=clock_uncertainty_ns.get(sid,0)
            if type(raw_unc) is not int or raw_unc < 0:
                raise ValueError(f"clock_uncertainty_ns[{sid!r}] must be a non-negative integer")
            unc=raw_unc
            flags=tuple(m.quality_flags) if m is not None else ();uncertain+=int(unc>0 or "stamp_semantics_unknown" in flags)
            dq=dynamic_state_quality(base_score=base,age_ns=0 if age is None else age,cadence_ns=cadence,missing=not present,clock_uncertainty_ns=unc)
            ratio=(age/cadence) if present and cadence and cadence>0 else None;stale=bool(ratio is not None and ratio>stale)
            if stale:stale_ids.append(sid)
            states[sid]=StreamQualityState(sid,present,age,cadence,base,dq,ratio,unc,stale,flags)
        vals=[x.dynamic_quality for x in states.values()];n=len(states);present_n=sum(x.present for x in states.values())
        pattern={"universe":all_ids,"missing":sorted(set(all_ids)-{s for s,x in states.items() if x.present}),"stale":sorted(stale_ids)}
        pid=hashlib.sha256(json.dumps(pattern,sort_keys=True,separators=(",",":")).encode()).hexdigest()[:20]
        return QualityPlane(packet.decision_ns,states,present_n/n if n else 0.0,sum(vals)/n if n else 0.0,min(vals) if vals else 0.0,n-present_n,len(stale_ids)/n if n else 0.0,uncertain/n if n else 0.0,pid)
