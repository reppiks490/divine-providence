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

    def __post_init__(self)->None:
        if not isinstance(self.stream_id,str) or not self.stream_id:
            raise ValueError("stream_id is required")
        if type(self.present) is not bool or type(self.stale) is not bool:
            raise TypeError("present and stale must be bool")
        if self.age_ns is not None and (type(self.age_ns) is not int or self.age_ns < 0):
            raise ValueError("age_ns must be a non-negative integer or None")
        if self.present and self.age_ns is None:
            raise ValueError("present quality state requires age_ns")
        if self.cadence_ns is not None and (type(self.cadence_ns) is not int or self.cadence_ns <= 0):
            raise ValueError("cadence_ns must be a positive integer or None")
        for name,value in (("base_quality",self.base_quality),("dynamic_quality",self.dynamic_quality)):
            v=float(value)
            if not math.isfinite(v) or not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be finite and in [0,1]")
        if self.stale_ratio is not None and (
            not math.isfinite(float(self.stale_ratio)) or float(self.stale_ratio) < 0
        ):
            raise ValueError("stale_ratio must be finite and non-negative or None")
        if type(self.clock_uncertainty_ns) is not int or self.clock_uncertainty_ns < 0:
            raise ValueError("clock_uncertainty_ns must be a non-negative integer")
        if (
            not isinstance(self.quality_flags,tuple)
            or any(not isinstance(x,str) for x in self.quality_flags)
        ):
            raise TypeError("quality_flags must be a tuple of strings")

@dataclass(frozen=True)
class QualityPlane:
    decision_ns:int;streams:Mapping[str,StreamQualityState];coverage:float;mean_quality:float;min_quality:float
    missing_count:int;stale_fraction:float=0.0;uncertain_clock_fraction:float=0.0;missingness_pattern_id:str=""

    def __post_init__(self)->None:
        if type(self.decision_ns) is not int or self.decision_ns < 0:
            raise ValueError("decision_ns must be a non-negative integer")
        if not isinstance(self.streams,Mapping):
            raise TypeError("streams must be a mapping")
        for sid,state in self.streams.items():
            if not isinstance(state,StreamQualityState) or sid != state.stream_id:
                raise ValueError("quality-plane stream mapping must match state stream_id")
        n=len(self.streams)
        present=sum(int(x.present) for x in self.streams.values())
        stale=sum(int(x.stale) for x in self.streams.values())
        uncertain=sum(
            int(x.clock_uncertainty_ns>0 or "stamp_semantics_unknown" in x.quality_flags)
            for x in self.streams.values()
        )
        vals=[x.dynamic_quality for x in self.streams.values()]
        expected=(
            present/n if n else 0.0,
            sum(vals)/n if n else 0.0,
            min(vals) if vals else 0.0,
            n-present,
            stale/n if n else 0.0,
            uncertain/n if n else 0.0,
        )
        actual=(
            float(self.coverage),float(self.mean_quality),float(self.min_quality),
            self.missing_count,float(self.stale_fraction),float(self.uncertain_clock_fraction),
        )
        if type(self.missing_count) is not int or self.missing_count < 0:
            raise ValueError("missing_count must be a non-negative integer")
        if any(not math.isfinite(float(x)) for x in actual if not isinstance(x,int)):
            raise ValueError("quality-plane aggregate metrics must be finite")
        for got,want in zip(actual[:3],expected[:3]):
            if abs(float(got)-float(want)) > 1e-12:
                raise ValueError("quality-plane aggregate metrics are inconsistent with stream states")
        if actual[3] != expected[3]:
            raise ValueError("quality-plane missing_count is inconsistent with stream states")
        for got,want in zip(actual[4:],expected[4:]):
            if abs(float(got)-float(want)) > 1e-12:
                raise ValueError("quality-plane fractions are inconsistent with stream states")
        if not isinstance(self.missingness_pattern_id,str) or len(self.missingness_pattern_id)!=20:
            raise ValueError("missingness_pattern_id must be a 20-character digest prefix")
        try:
            int(self.missingness_pattern_id,16)
        except ValueError as exc:
            raise ValueError("missingness_pattern_id must be hexadecimal") from exc

class QualityStateEngine:
    """Time-varying data-health plane; missingness remains telemetry, never imputed truth."""
    def build(self,packet:StatePacket,manifests:Mapping[str,StreamManifest],*,clock_uncertainty_ns:Mapping[str,int]|None=None,stale_after_multiples:float=2.0)->QualityPlane:
        if not isinstance(packet,StatePacket):
            raise TypeError("packet must be StatePacket")
        if not isinstance(manifests,Mapping):
            raise TypeError("manifests must be a mapping")
        for sid,manifest in manifests.items():
            if not isinstance(sid,str) or not sid:
                raise ValueError("manifest mapping keys must be non-empty stream ids")
            if not isinstance(manifest,StreamManifest):
                raise TypeError(f"manifest for {sid!r} must be StreamManifest")
            if manifest.identity.stream_id != sid:
                raise ValueError(
                    f"manifest mapping key {sid!r} does not match manifest stream_id "
                    f"{manifest.identity.stream_id!r}"
                )
        stale=float(stale_after_multiples)
        if not math.isfinite(stale) or stale<=0:
            raise ValueError("stale_after_multiples must be finite and positive")
        if clock_uncertainty_ns is not None and not isinstance(clock_uncertainty_ns,Mapping):
            raise TypeError("clock_uncertainty_ns must be a mapping or None")
        clock_uncertainty_ns=clock_uncertainty_ns or {}
        unknown_uncertainty=set(clock_uncertainty_ns)-(
            set(manifests)|set(packet.values)|set(packet.missing)
        )
        if unknown_uncertainty:
            raise ValueError(
                "clock_uncertainty_ns contains unknown stream ids: "
                + ", ".join(sorted(unknown_uncertainty))
            )
        all_ids=sorted(set(manifests)|set(packet.values)|set(packet.missing));states={};stale_ids=[];uncertain=0
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
