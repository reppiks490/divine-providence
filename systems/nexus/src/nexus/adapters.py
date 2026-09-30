from __future__ import annotations
from dataclasses import asdict
from typing import Any
from .contracts import BarEvent, StreamManifest

CONTRACT_VERSION="nexus.market-state.v2"

def market_state_packet(*, decision_ns:int, factors:dict[str,float], topology:dict[str,Any], quality:dict[str,float], lineage:list[dict[str,Any]], plane:str="research", frame_hash:str|None=None, ood:dict[str,float]|None=None) -> dict[str,Any]:
    return {
        "contract": CONTRACT_VERSION,
        "decision_ns": int(decision_ns),
        "data_plane": plane,
        "production_authorized": False,
        "frame_hash":frame_hash,
        "factors": factors,
        "topology": topology,
        "quality": quality,
        "ood":ood or {},
        "lineage": lineage,
    }

def for_argus(packet: dict[str,Any]) -> dict[str,Any]:
    return {**packet,"consumer":"ARGUS","evidence_tier":"CANDLE_PROXY","microstructure_truth":False}

def for_athena(packet: dict[str,Any]) -> dict[str,Any]:
    return {**packet,"consumer":"ATHENA","purpose":"state_input","advisory_only":True}

def for_aion(packet: dict[str,Any]) -> dict[str,Any]:
    return {**packet,"consumer":"AION","purpose":"observation_and_replay"}

def for_daedalus(packet: dict[str,Any]) -> dict[str,Any]:
    return {**packet,"consumer":"DAEDALUS","purpose":"research_feature_candidate","protected_evidence":False}

# Concrete sibling-schema builders. Kept as plain dicts so NEXUS does not import sibling source trees.
def aion_source_spec(manifest:StreamManifest,representation_id:str|None=None)->dict[str,Any]:
    ident=manifest.identity
    return {
        "source_id":ident.stream_id,
        "representation_id":representation_id or ident.representation,
        "symbol":ident.symbol,
        "capabilities":["bar"],
        "max_evidence_tier":1,
        "source_sha256":ident.raw_sha256,
        "sequence_policy":"monotone",
        "origin":"historical_csv",
        "license_reference":"requires_source_review",
        "evidence_reference":ident.source_path,
    }

def aion_bar_observation(event:BarEvent,*,ingested_ns:int|None=None,availability_basis:str|None=None)->dict[str,Any]:
    if event.available_ns is None:
        raise ValueError("AION strict observation requires explicit available_ns")
    basis=availability_basis or event.availability_basis
    allowed={"observed_receipt","attested_release","verified_bar_close","reviewed_event_completion","synthetic"}
    if basis not in allowed:
        raise ValueError(f"AION export requires an AION-attested availability basis; got {basis!r}")
    if int(event.available_ns) < int(event.event_ns):
        raise ValueError("AION export rejects available_ns before event_ns")
    if event.source_timestamp_ns is not None and int(event.event_ns) < int(event.source_timestamp_ns):
        raise ValueError("AION export rejects event_ns before source_timestamp_ns")
    ingested_ns=max(event.available_ns,int(ingested_ns if ingested_ns is not None else event.available_ns))
    return {
        "source_id":event.stream_id,
        "source_event_id":f"bar:{event.source_sequence}",
        "revision":max(1,event.revision+1),
        "kind":"bar",
        "event_ns":int(event.event_ns),
        "available_ns":int(event.available_ns),
        "ingested_ns":ingested_ns,
        "evidence_tier":1,
        "payload":{"open":event.open,"high":event.high,"low":event.low,"close":event.close,**({"volume":event.volume} if event.volume is not None else {})},
        "plane":"research" if event.data_plane=="research" else ("shadow" if event.data_plane=="shadow" else "production_observation"),
        "published_ns":None,
        "sequence":event.source_sequence,
        "quality_flags":list(event.quality_flags),
        "availability_basis":basis,
    }

def argus_candle_proxy_feature(*,name:str,value:float,event_ns:int,source_id:str,reason:str)->dict[str,Any]:
    return {"name":name,"value":float(value),"evidence_tier":1,"event_time_ns":int(event_ns),"source_id":source_id,"reason":reason}

def athena_provenance(*,event_time_ns:int,ingestion_time_ns:int,source_id:str,representation_id:str,version:str,lineage_id:str,plane:str="research",quality_flags:tuple[str,...]=())->dict[str,Any]:
    return {
        "event_time_ns":int(event_time_ns),"ingestion_time_ns":int(ingestion_time_ns),"source_id":source_id,
        "representation_id":representation_id,"version":version,"plane":plane,"lineage_id":lineage_id,
        "quality_flags":list(quality_flags),
    }

def daedalus_candidate(candidate:dict[str,Any])->dict[str,Any]:
    return {"schema":"icarus-candidate-v1","status":"RESEARCH_CANDIDATE_ONLY","production_authorized":False,"candidate":candidate}

def aion_context_source_spec(*,source_id:str,representation_id:str,symbol:str,source_sha256:str,evidence_reference:str)->dict[str,Any]:
    return {"source_id":source_id,"representation_id":representation_id,"symbol":symbol,"capabilities":["context"],
            "max_evidence_tier":1,"source_sha256":source_sha256,"sequence_policy":"monotone","origin":"historical_csv",
            "license_reference":"requires_source_review","evidence_reference":evidence_reference}

def aion_context_observation(event,*,ingested_ns:int|None=None,availability_basis:str|None=None)->dict[str,Any]:
    if event.available_ns is None: raise ValueError("AION context export requires explicit available_ns")
    basis=availability_basis or event.availability_basis
    if basis not in {"observed_receipt","attested_release","verified_bar_close","reviewed_event_completion","synthetic"}:
        raise ValueError(f"AION context export requires an AION-attested availability basis; got {basis!r}")
    if int(event.available_ns) < int(event.event_ns):
        raise ValueError("AION context export rejects available_ns before event_ns")
    if event.source_timestamp_ns is not None and int(event.event_ns) < int(event.source_timestamp_ns):
        raise ValueError("AION context export rejects event_ns before source_timestamp_ns")
    ing=max(int(event.available_ns),int(ingested_ns if ingested_ns is not None else event.available_ns))
    return {"source_id":event.stream_id,"source_event_id":f"context:{event.source_sequence}","revision":max(1,event.revision+1),
            "kind":"context","event_ns":int(event.event_ns),"available_ns":int(event.available_ns),"ingested_ns":ing,
            "evidence_tier":1,"payload":event.values(),"plane":"research" if event.data_plane=="research" else ("shadow" if event.data_plane=="shadow" else "production_observation"),
            "published_ns":None,"sequence":event.source_sequence,"quality_flags":list(event.quality_flags),"availability_basis":basis}

def aion_derivation_source_spec(*,product_id:str,product_version:str,spec_hash:str,code_version:str)->dict[str,Any]:
    """AION context-source contract for a versioned NEXUS derived product."""
    import hashlib, json
    raw=json.dumps({"product_id":product_id,"product_version":product_version,"spec_hash":spec_hash,"code_version":code_version},sort_keys=True,separators=(",",":")).encode()
    source_sha=hashlib.sha256(raw).hexdigest()
    source_id=f"nexus-derivation:{product_id}:{product_version}"
    if len(source_id)>160:
        source_id=f"nexus-derivation:{hashlib.sha256(source_id.encode()).hexdigest()}"
    return {
        "source_id":source_id,
        "representation_id":"nexus.derivation.v1",
        "symbol":product_id[:160],
        "capabilities":["context"],
        "max_evidence_tier":1,
        "source_sha256":source_sha,
        "sequence_policy":"none",
        "origin":"nexus_derived",
        "license_reference":"inherits_inputs",
        "evidence_reference":f"spec:{spec_hash}",
    }


def aion_derivation_observation(derivation,*,sequence:int|None=None,quality_flags:tuple[str,...]=())->dict[str,Any]:
    """AION context observation containing the exact NEXUS derivation genealogy."""
    if not derivation.verify():
        raise ValueError("invalid derivation record")
    src=aion_derivation_source_spec(product_id=derivation.product_id,product_version=derivation.product_version,spec_hash=derivation.spec_hash,code_version=derivation.code_version)
    return {
        "source_id":src["source_id"],
        "source_event_id":f"derivation:{derivation.derivation_hash}",
        "revision":1,
        "kind":"context",
        "event_ns":int(derivation.decision_ns),
        "available_ns":int(derivation.decision_ns),
        "ingested_ns":int(derivation.decision_ns),
        "evidence_tier":1,
        "payload":derivation.to_dict(),
        "plane":"research",
        "published_ns":None,
        "sequence":None if sequence is None else int(sequence),
        "quality_flags":list(quality_flags),
        "availability_basis":"synthetic",
    }


def aion_source_health_spec(*,plane_hash:str)->dict[str,Any]:
    """AION context source for a deterministic NEXUS source-health plane."""
    import hashlib
    if not isinstance(plane_hash,str) or len(plane_hash)!=64:
        raise ValueError("plane_hash must be a SHA-256 hex digest")
    try:
        int(plane_hash,16)
    except ValueError as exc:
        raise ValueError("plane_hash must be hexadecimal") from exc
    return {
        "source_id":f"NEXUS:HEALTH:{plane_hash[:20]}",
        "representation_id":"nexus.source-health.v1",
        "symbol":"NEXUS_HEALTH",
        "capabilities":["context"],
        "max_evidence_tier":1,
        "source_sha256":hashlib.sha256(("nexus.source-health.v1|"+plane_hash).encode()).hexdigest(),
        "sequence_policy":"none",
        "origin":"nexus_derived",
        "license_reference":"inherits_inputs",
        "evidence_reference":f"health-plane:{plane_hash}",
    }


def aion_source_health_observation(health_plane,*,ingested_ns:int|None=None)->dict[str,Any]:
    """Persist the exact fleet health plane as low-tier context, never market truth."""
    spec=aion_source_health_spec(plane_hash=health_plane.plane_hash)
    decision_ns=int(health_plane.decision_ns)
    ing=max(decision_ns,int(ingested_ns if ingested_ns is not None else decision_ns))
    return {
        "source_id":spec["source_id"],
        "source_event_id":f"health:{health_plane.plane_hash[:24]}",
        "revision":1,
        "kind":"context",
        "event_ns":decision_ns,
        "available_ns":decision_ns,
        "ingested_ns":ing,
        "evidence_tier":1,
        "payload":health_plane.to_dict(),
        "plane":"research",
        "published_ns":None,
        "sequence":None,
        "quality_flags":["nexus_source_health"],
        "availability_basis":"synthetic",
    }
