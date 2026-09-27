from __future__ import annotations
from .contracts import StreamManifest, BarEvent

def aion_source_spec(m:StreamManifest)->dict:
    """AION SourceSpec-compatible dictionary for candle CSVs."""
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

def aion_bar_observation(event:BarEvent,*,available_ns:int|None=None,ingested_ns:int|None=None,availability_basis:str|None=None)->dict:
    """Build AION Observation-compatible bar payload only when availability is explicit.

    Historical CSV bar timestamps are not automatically proof of first-known availability.
    """
    avail=available_ns if available_ns is not None else event.available_ns
    if avail is None:
        raise ValueError('AION export requires explicit verified/attested/observed availability_ns')
    ing=ingested_ns if ingested_ns is not None else avail
    basis=availability_basis or 'observed_receipt'
    return {
        'source_id':event.stream_id,
        'source_event_id':f'{event.stream_id}:{event.source_sequence}:{event.revision}',
        'revision':event.revision+1,
        'kind':'bar',
        'event_ns':event.event_ns,
        'available_ns':int(avail),
        'ingested_ns':int(ing),
        'evidence_tier':1,
        'payload':{'open':event.open,'high':event.high,'low':event.low,'close':event.close,**({'volume':event.volume} if event.volume is not None else {})},
        'plane':'research' if event.data_plane=='research' else ('shadow' if event.data_plane=='shadow' else 'production_observation'),
        'published_ns':None,
        'sequence':event.source_sequence,
        'quality_flags':list(event.quality_flags),
        'availability_basis':basis,
    }

def athena_provenance(*,event_ns:int,ingestion_ns:int,source_id:str,representation_id:str,version:str,lineage_id:str,plane:str='research',quality_flags=())->dict:
    return {'event_time_ns':event_ns,'ingestion_time_ns':ingestion_ns,'source_id':source_id,'representation_id':representation_id,'version':version,'plane':plane,'lineage_id':lineage_id,'quality_flags':list(quality_flags)}

def daedalus_feature_manifest(*,name:str,version:str,lineage:list[dict],definition:dict)->dict:
    return {'schema':'nexus-daedalus-feature-v1','status':'RESEARCH_FEATURE_ONLY','production_authorized':False,'name':name,'version':version,'definition':definition,'lineage':lineage}

def argus_candle_proxy_feature(*,name:str,value:float,event_ns:int,source_id:str,reason:str)->dict:
    return {'name':name,'value':float(value),'evidence_tier':1,'event_time_ns':int(event_ns),'source_id':source_id,'reason':reason}
