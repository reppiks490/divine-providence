from __future__ import annotations

from dataclasses import replace
from .contracts import StreamManifest, BarEvent
from .adapters import (
    aion_bar_observation as _strict_aion_bar_observation,
    argus_candle_proxy_feature as _strict_argus_candle_proxy_feature,
    athena_provenance as _strict_athena_provenance,
)


def aion_source_spec(m:StreamManifest)->dict:
    """AION SourceSpec-compatible dictionary for candle CSVs."""
    if not isinstance(m,StreamManifest):
        raise TypeError("manifest must be StreamManifest")
    return {
        'source_id':m.identity.stream_id,
        'representation_id':m.identity.representation,
        'symbol':m.identity.symbol,
        'capabilities':['bar'],
        'max_evidence_tier':1,
        'source_sha256':m.identity.raw_sha256,
        'sequence_policy':'monotone',
        'origin':'nexus_csv',
        'license_reference':'unspecified',
        'evidence_reference':m.identity.source_path or 'nexus_catalog',
    }


def aion_bar_observation(
    event:BarEvent,*,available_ns:int|None=None,ingested_ns:int|None=None,
    availability_basis:str|None=None,
)->dict:
    """Legacy AION shape with the canonical adapter's causal validation."""
    if not isinstance(event,BarEvent):
        raise TypeError("event must be BarEvent")
    if available_ns is not None:
        if type(available_ns) is not int or available_ns < 0:
            raise ValueError("available_ns must be a non-negative integer or None")
        event=replace(event,available_ns=available_ns)
    out=_strict_aion_bar_observation(
        event,ingested_ns=ingested_ns,availability_basis=availability_basis
    )
    out['source_event_id']=f'{event.stream_id}:{event.source_sequence}:{event.revision}'
    return out


def athena_provenance(
    *,event_ns:int,ingestion_ns:int,source_id:str,representation_id:str,
    version:str,lineage_id:str,plane:str='research',quality_flags=(),
)->dict:
    if isinstance(quality_flags,str) or not isinstance(quality_flags,(tuple,list)):
        raise TypeError("quality_flags must be a tuple/list of strings, not a scalar string")
    if any(not isinstance(x,str) or not x for x in quality_flags):
        raise ValueError("quality_flags entries must be non-empty strings")
    quality_flags=tuple(quality_flags)
    return _strict_athena_provenance(
        event_time_ns=event_ns,ingestion_time_ns=ingestion_ns,
        source_id=source_id,representation_id=representation_id,version=version,
        lineage_id=lineage_id,plane=plane,quality_flags=quality_flags,
    )


def daedalus_feature_manifest(
    *,name:str,version:str,lineage:list[dict],definition:dict
)->dict:
    if not isinstance(name,str) or not name.strip() or name != name.strip():
        raise ValueError("name must be a non-empty trimmed string")
    if not isinstance(version,str) or not version.strip() or version != version.strip():
        raise ValueError("version must be a non-empty trimmed string")
    if not isinstance(lineage,list) or not isinstance(definition,dict):
        raise TypeError("lineage must be list and definition must be dict")
    import json
    try:
        clean_lineage=json.loads(json.dumps(lineage,sort_keys=True,separators=(',',':'),allow_nan=False))
        clean_definition=json.loads(json.dumps(definition,sort_keys=True,separators=(',',':'),allow_nan=False))
    except (TypeError,ValueError) as exc:
        raise ValueError("DAEDALUS feature metadata must be finite JSON-compatible data") from exc
    return {
        'schema':'nexus-daedalus-feature-v1','status':'RESEARCH_FEATURE_ONLY',
        'production_authorized':False,'name':name,'version':version,
        'definition':clean_definition,'lineage':clean_lineage,
    }


def argus_candle_proxy_feature(
    *,name:str,value:float,event_ns:int,source_id:str,reason:str
)->dict:
    return _strict_argus_candle_proxy_feature(
        name=name,value=value,event_ns=event_ns,source_id=source_id,reason=reason
    )
