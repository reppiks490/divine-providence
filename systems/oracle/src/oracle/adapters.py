from __future__ import annotations
from dataclasses import asdict
from typing import Any
from .contracts import FinancialState,Hypothesis,ResearchJob,EvidenceRecord
from .firewall import research_envelope


def to_athena_research_request(job:ResearchJob)->dict[str,Any]:
    return {"hypothesis_family":job.task_type,"expected_information_gain":job.expected_information_gain,"strategic_relevance":job.strategic_relevance,"evidence_deficit":job.evidence_deficit,"estimated_compute_cost":job.estimated_compute_cost,"required_states":list(job.required_states)}

def to_daedalus_candidate(h:Hypothesis,evidence:list[EvidenceRecord])->dict[str,Any]:
    payload={"hypothesis":asdict(h),"evidence_ids":[e.evidence_id for e in evidence],"evidence_hashes":[e.immutable_hash for e in evidence]}
    return research_envelope(payload,schema="icarus-candidate-v1",purpose="DAEDALUS_RESEARCH_CANDIDATE")

def to_aion_context(*,record_id:str,event_ns:int,available_ns:int,ingested_ns:int,payload:dict[str,Any],lineage_hash:str)->dict[str,Any]:
    body={"source_id":"ORACLE","source_event_id":record_id,"revision":1,"kind":"context","event_ns":int(event_ns),"available_ns":int(available_ns),"ingested_ns":int(ingested_ns),"evidence_tier":1,"payload":payload,"plane":"research","published_ns":None,"sequence":None,"quality_flags":[],"availability_basis":"observed_receipt"}
    return research_envelope(body,schema="aion.observation.context.v1",purpose="AION_EVIDENCE_MEMORY")

def to_argus_context(state:FinancialState)->dict[str,Any]:
    return research_envelope({"state_id":state.state_id,"decision_ns":state.decision_ns,"features":dict(state.features),"evidence_tier":"CANDLE_PROXY","microstructure_truth":False},schema="oracle.argus.context.v1",purpose="ARGUS_CONTEXT_ONLY")

def to_nexus_research_request(h:Hypothesis)->dict[str,Any]:
    return research_envelope({"hypothesis_id":h.hypothesis_id,"target":h.target,"horizon":h.horizon,"family":h.family,"requested_products":["aligned_state","factor_context","topology","source_health"]},schema="oracle.nexus.request.v1",purpose="NEXUS_RESEARCH_INPUT")


def aion_source_spec(*,lineage_hash:str)->dict[str,Any]:
    return {"source_id":"ORACLE","representation_id":"oracle.context.v1","symbol":"ORACLE","capabilities":["context"],"max_evidence_tier":1,"source_sha256":__import__("hashlib").sha256(("ORACLE|oracle.context.v1|"+lineage_hash).encode()).hexdigest(),"sequence_policy":"none","origin":"oracle_derived","license_reference":"inherits_inputs","evidence_reference":f"lineage:{lineage_hash}"}

def to_athena_provenance(state:FinancialState)->dict[str,Any]:
    flags=tuple(sorted({f for p in state.provenance for f in p.quality_flags}))
    try:
        from athena.contracts import DataPlane
        plane=DataPlane.RESEARCH
    except Exception:
        plane="research"
    return {"event_time_ns":state.decision_ns,"ingestion_time_ns":state.decision_ns,"source_id":"ORACLE","representation_id":"oracle.financial-state.v1","version":"oracle-v0.1","plane":plane,"lineage_id":state.state_hash,"quality_flags":flags}

def to_argus_proxy_features(state:FinancialState)->list[dict[str,Any]]:
    return [{"name":f"oracle.{name}","value":float(value),"evidence_tier":1,"event_time_ns":state.decision_ns,"source_id":"ORACLE","reason":"ORACLE financial/research context; candle-proxy tier only"} for name,value in sorted(state.features.items())]
