from __future__ import annotations

from typing import Any, Mapping
import json
import math

from .contracts import BarEvent, DataPlane, StreamManifest


CONTRACT_VERSION="nexus.market-state.v2"
_AION_AVAILABILITY_BASES={
    "observed_receipt","attested_release","verified_bar_close",
    "reviewed_event_completion","synthetic",
}


def _nonnegative_int(name:str,value:int|None,*,allow_none:bool=False)->int|None:
    if value is None and allow_none:
        return None
    if type(value) is not int or value < 0:
        suffix=" or None" if allow_none else ""
        raise ValueError(f"{name} must be a non-negative integer{suffix}")
    return value


def _nonempty(name:str,value:Any)->str:
    if not isinstance(value,str) or not value.strip() or value != value.strip():
        raise ValueError(f"{name} must be a non-empty trimmed string")
    return value


def _sha256(name:str,value:Any)->str:
    if not isinstance(value,str) or len(value)!=64:
        raise ValueError(f"{name} must be a SHA-256 hex digest")
    try:
        int(value,16)
    except ValueError as exc:
        raise ValueError(f"{name} must be a SHA-256 hex digest") from exc
    return value.lower()


def _finite_mapping(name:str,value:Mapping[str,Any])->dict[str,float]:
    if not isinstance(value,Mapping):
        raise TypeError(f"{name} must be a mapping")
    out={}
    for key,raw in value.items():
        key=_nonempty(f"{name} key",key)
        try:
            number=float(raw)
        except (TypeError,ValueError) as exc:
            raise ValueError(f"{name}[{key!r}] must be numeric") from exc
        if not math.isfinite(number):
            raise ValueError(f"{name}[{key!r}] must be finite")
        out[key]=number
    return out


def _canonical_jsonish(name:str,value:Any)->Any:
    try:
        raw=json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)
        return json.loads(raw)
    except (TypeError,ValueError) as exc:
        raise ValueError(f"{name} must be finite JSON-compatible data") from exc


def _ingestion_time(available_ns:int,ingested_ns:int|None)->int:
    _nonnegative_int("available_ns",available_ns)
    ing=_nonnegative_int("ingested_ns",ingested_ns,allow_none=True)
    if ing is None:
        return available_ns
    if ing < available_ns:
        raise ValueError("ingested_ns cannot precede available_ns")
    return ing


def _aion_basis(value:str|None,fallback:str)->str:
    basis=value or fallback
    if basis not in _AION_AVAILABILITY_BASES:
        raise ValueError(f"AION export requires an AION-attested availability basis; got {basis!r}")
    return basis


def market_state_packet(
    *,
    decision_ns:int,
    factors:dict[str,float],
    topology:dict[str,Any],
    quality:dict[str,float],
    lineage:list[dict[str,Any]],
    plane:str="research",
    frame_hash:str|None=None,
    ood:dict[str,float]|None=None,
)->dict[str,Any]:
    decision=_nonnegative_int("decision_ns",decision_ns)
    if plane not in {x.value for x in DataPlane}:
        raise ValueError("unsupported data plane")
    if frame_hash is not None and (not isinstance(frame_hash,str) or not frame_hash):
        raise ValueError("frame_hash must be a non-empty string or None")
    if not isinstance(lineage,list):
        raise TypeError("lineage must be a list")
    clean_lineage=_canonical_jsonish("lineage",lineage)
    clean_topology=_canonical_jsonish("topology",topology)
    return {
        "contract":CONTRACT_VERSION,
        "decision_ns":decision,
        "data_plane":plane,
        "production_authorized":False,
        "frame_hash":frame_hash,
        "factors":_finite_mapping("factors",factors),
        "topology":clean_topology,
        "quality":_finite_mapping("quality",quality),
        "ood":_finite_mapping("ood",ood or {}),
        "lineage":clean_lineage,
    }


def for_argus(packet:dict[str,Any])->dict[str,Any]:
    _canonical_jsonish("market-state packet",packet)
    return {**packet,"consumer":"ARGUS","evidence_tier":"CANDLE_PROXY","microstructure_truth":False}


def for_athena(packet:dict[str,Any])->dict[str,Any]:
    _canonical_jsonish("market-state packet",packet)
    return {**packet,"consumer":"ATHENA","purpose":"state_input","advisory_only":True}


def for_aion(packet:dict[str,Any])->dict[str,Any]:
    _canonical_jsonish("market-state packet",packet)
    return {**packet,"consumer":"AION","purpose":"observation_and_replay"}


def for_daedalus(packet:dict[str,Any])->dict[str,Any]:
    _canonical_jsonish("market-state packet",packet)
    return {**packet,"consumer":"DAEDALUS","purpose":"research_feature_candidate","protected_evidence":False}


# Concrete sibling-schema builders. Kept as plain dicts so NEXUS does not import
# sibling source trees.
def aion_source_spec(manifest:StreamManifest,representation_id:str|None=None)->dict[str,Any]:
    if not isinstance(manifest,StreamManifest):
        raise TypeError("manifest must be StreamManifest")
    ident=manifest.identity
    rep=representation_id if representation_id is not None else ident.representation
    _nonempty("representation_id",rep)
    return {
        "source_id":ident.stream_id,
        "representation_id":rep,
        "symbol":ident.symbol,
        "capabilities":["bar"],
        "max_evidence_tier":1,
        "source_sha256":_sha256("source_sha256",ident.raw_sha256),
        "sequence_policy":"monotone",
        "origin":"historical_csv",
        "license_reference":"requires_source_review",
        "evidence_reference":ident.source_path,
    }


def aion_bar_observation(
    event:BarEvent,*,ingested_ns:int|None=None,availability_basis:str|None=None
)->dict[str,Any]:
    if not isinstance(event,BarEvent):
        raise TypeError("event must be BarEvent")
    if event.available_ns is None:
        raise ValueError("AION strict observation requires explicit available_ns")
    basis=_aion_basis(availability_basis,event.availability_basis)
    if event.available_ns < event.event_ns:
        raise ValueError("AION export rejects available_ns before event_ns")
    if event.source_timestamp_ns is not None and event.event_ns < event.source_timestamp_ns:
        raise ValueError("AION export rejects event_ns before source_timestamp_ns")
    ing=_ingestion_time(event.available_ns,ingested_ns)
    return {
        "source_id":event.stream_id,
        "source_event_id":f"bar:{event.source_sequence}",
        "revision":max(1,event.revision+1),
        "kind":"bar",
        "event_ns":event.event_ns,
        "available_ns":event.available_ns,
        "ingested_ns":ing,
        "evidence_tier":1,
        "payload":{
            "open":event.open,"high":event.high,"low":event.low,"close":event.close,
            **({"volume":event.volume} if event.volume is not None else {}),
        },
        "plane":"research" if event.data_plane=="research" else (
            "shadow" if event.data_plane=="shadow" else "production_observation"
        ),
        "published_ns":None,
        "sequence":event.source_sequence,
        "quality_flags":list(event.quality_flags),
        "availability_basis":basis,
    }


def argus_candle_proxy_feature(
    *,name:str,value:float,event_ns:int,source_id:str,reason:str
)->dict[str,Any]:
    _nonempty("name",name);_nonempty("source_id",source_id);_nonempty("reason",reason)
    event=_nonnegative_int("event_ns",event_ns)
    try:
        number=float(value)
    except (TypeError,ValueError) as exc:
        raise ValueError("feature value must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError("feature value must be finite")
    return {
        "name":name,"value":number,"evidence_tier":1,
        "event_time_ns":event,"source_id":source_id,"reason":reason,
    }


def athena_provenance(
    *,event_time_ns:int,ingestion_time_ns:int,source_id:str,
    representation_id:str,version:str,lineage_id:str,plane:str="research",
    quality_flags:tuple[str,...]=(),
)->dict[str,Any]:
    event=_nonnegative_int("event_time_ns",event_time_ns)
    ingestion=_nonnegative_int("ingestion_time_ns",ingestion_time_ns)
    if ingestion < event:
        raise ValueError("ingestion_time_ns cannot precede event_time_ns")
    for name,value in (
        ("source_id",source_id),("representation_id",representation_id),
        ("version",version),("lineage_id",lineage_id),
    ):
        _nonempty(name,value)
    if plane not in {x.value for x in DataPlane}:
        raise ValueError("unsupported data plane")
    if not isinstance(quality_flags,tuple) or any(
        not isinstance(x,str) or not x for x in quality_flags
    ):
        raise TypeError("quality_flags must be a tuple of non-empty strings")
    return {
        "event_time_ns":event,"ingestion_time_ns":ingestion,"source_id":source_id,
        "representation_id":representation_id,"version":version,"plane":plane,
        "lineage_id":lineage_id,"quality_flags":list(quality_flags),
    }


def daedalus_candidate(candidate:dict[str,Any])->dict[str,Any]:
    if not isinstance(candidate,dict):
        raise TypeError("candidate must be a dict")
    clean=_canonical_jsonish("candidate",candidate)
    return {
        "schema":"icarus-candidate-v1","status":"RESEARCH_CANDIDATE_ONLY",
        "production_authorized":False,"candidate":clean,
    }


def aion_context_source_spec(
    *,source_id:str,representation_id:str,symbol:str,
    source_sha256:str,evidence_reference:str,
)->dict[str,Any]:
    for name,value in (
        ("source_id",source_id),("representation_id",representation_id),
        ("symbol",symbol),("evidence_reference",evidence_reference),
    ):
        _nonempty(name,value)
    return {
        "source_id":source_id,"representation_id":representation_id,"symbol":symbol,
        "capabilities":["context"],"max_evidence_tier":1,
        "source_sha256":_sha256("source_sha256",source_sha256),
        "sequence_policy":"monotone","origin":"historical_csv",
        "license_reference":"requires_source_review","evidence_reference":evidence_reference,
    }


def aion_context_observation(
    event,*,ingested_ns:int|None=None,availability_basis:str|None=None
)->dict[str,Any]:
    for name in ("stream_id","event_ns","source_sequence","available_ns","availability_basis","values"):
        if not hasattr(event,name):
            raise TypeError(f"context event missing {name}")
    if event.available_ns is None:
        raise ValueError("AION context export requires explicit available_ns")
    basis=_aion_basis(availability_basis,event.availability_basis)
    event_ns=_nonnegative_int("event_ns",event.event_ns)
    available=_nonnegative_int("available_ns",event.available_ns)
    sequence=_nonnegative_int("source_sequence",event.source_sequence)
    if available < event_ns:
        raise ValueError("AION context export rejects available_ns before event_ns")
    source_ts=getattr(event,"source_timestamp_ns",None)
    if source_ts is not None:
        source_ts=_nonnegative_int("source_timestamp_ns",source_ts)
        if event_ns < source_ts:
            raise ValueError("AION context export rejects event_ns before source_timestamp_ns")
    ing=_ingestion_time(available,ingested_ns)
    payload=_finite_mapping("context payload",event.values())
    data_plane=getattr(event,"data_plane","research")
    if data_plane not in {x.value for x in DataPlane}:
        raise ValueError("unsupported data plane")
    flags=getattr(event,"quality_flags",())
    if not isinstance(flags,tuple) or any(not isinstance(x,str) or not x for x in flags):
        raise TypeError("quality_flags must be a tuple of non-empty strings")
    return {
        "source_id":_nonempty("stream_id",event.stream_id),
        "source_event_id":f"context:{sequence}","revision":max(1,int(getattr(event,"revision",0))+1),
        "kind":"context","event_ns":event_ns,"available_ns":available,"ingested_ns":ing,
        "evidence_tier":1,"payload":payload,
        "plane":"research" if data_plane=="research" else (
            "shadow" if data_plane=="shadow" else "production_observation"
        ),
        "published_ns":None,"sequence":sequence,"quality_flags":list(flags),
        "availability_basis":basis,
    }


def aion_derivation_source_spec(
    *,product_id:str,product_version:str,spec_hash:str,code_version:str
)->dict[str,Any]:
    """AION context-source contract for a versioned NEXUS derived product."""
    import hashlib
    product_id=_nonempty("product_id",product_id)
    product_version=_nonempty("product_version",product_version)
    code_version=_nonempty("code_version",code_version)
    spec_hash=_sha256("spec_hash",spec_hash)
    raw=json.dumps({
        "product_id":product_id,"product_version":product_version,
        "spec_hash":spec_hash,"code_version":code_version,
    },sort_keys=True,separators=(",",":")).encode()
    source_sha=hashlib.sha256(raw).hexdigest()
    source_id=f"nexus-derivation:{product_id}:{product_version}"
    if len(source_id)>160:
        source_id=f"nexus-derivation:{hashlib.sha256(source_id.encode()).hexdigest()}"
    return {
        "source_id":source_id,"representation_id":"nexus.derivation.v1",
        "symbol":product_id[:160],"capabilities":["context"],"max_evidence_tier":1,
        "source_sha256":source_sha,"sequence_policy":"none","origin":"nexus_derived",
        "license_reference":"inherits_inputs","evidence_reference":f"spec:{spec_hash}",
    }


def aion_derivation_observation(
    derivation,*,sequence:int|None=None,quality_flags:tuple[str,...]=(),
    ingested_ns:int|None=None,
)->dict[str,Any]:
    """AION context observation containing the exact NEXUS derivation genealogy."""
    if not hasattr(derivation,"verify") or not derivation.verify():
        raise ValueError("invalid derivation record")
    decision_ns=_nonnegative_int("decision_ns",derivation.decision_ns)
    seq=_nonnegative_int("sequence",sequence,allow_none=True)
    if not isinstance(quality_flags,tuple) or any(
        not isinstance(x,str) or not x for x in quality_flags
    ):
        raise TypeError("quality_flags must be a tuple of non-empty strings")
    ingestion=_ingestion_time(decision_ns,ingested_ns)
    src=aion_derivation_source_spec(
        product_id=derivation.product_id,product_version=derivation.product_version,
        spec_hash=derivation.spec_hash,code_version=derivation.code_version,
    )
    return {
        "source_id":src["source_id"],
        "source_event_id":f"derivation:{derivation.derivation_hash}",
        "revision":1,"kind":"context","event_ns":decision_ns,
        "available_ns":decision_ns,"ingested_ns":ingestion,"evidence_tier":1,
        "payload":derivation.to_dict(),"plane":"research","published_ns":None,
        "sequence":seq,"quality_flags":list(quality_flags),"availability_basis":"synthetic",
    }


def aion_source_health_spec(*,plane_hash:str)->dict[str,Any]:
    """AION context source for a deterministic NEXUS source-health plane."""
    import hashlib
    plane_hash=_sha256("plane_hash",plane_hash)
    return {
        "source_id":f"NEXUS:HEALTH:{plane_hash[:20]}",
        "representation_id":"nexus.source-health.v1","symbol":"NEXUS_HEALTH",
        "capabilities":["context"],"max_evidence_tier":1,
        "source_sha256":hashlib.sha256(("nexus.source-health.v1|"+plane_hash).encode()).hexdigest(),
        "sequence_policy":"none","origin":"nexus_derived",
        "license_reference":"inherits_inputs","evidence_reference":f"health-plane:{plane_hash}",
    }


def aion_source_health_observation(health_plane,*,ingested_ns:int|None=None)->dict[str,Any]:
    """Persist the exact verified fleet health plane as low-tier context."""
    if not hasattr(health_plane,"verify") or not health_plane.verify():
        raise ValueError("invalid source-health plane")
    decision_ns=_nonnegative_int("decision_ns",health_plane.decision_ns)
    spec=aion_source_health_spec(plane_hash=health_plane.plane_hash)
    ing=_ingestion_time(decision_ns,ingested_ns)
    payload=_canonical_jsonish("source-health payload",health_plane.to_dict())
    return {
        "source_id":spec["source_id"],
        "source_event_id":f"health:{health_plane.plane_hash[:24]}",
        "revision":1,"kind":"context","event_ns":decision_ns,
        "available_ns":decision_ns,"ingested_ns":ing,"evidence_tier":1,
        "payload":payload,"plane":"research","published_ns":None,"sequence":None,
        "quality_flags":["nexus_source_health"],"availability_basis":"synthetic",
    }
