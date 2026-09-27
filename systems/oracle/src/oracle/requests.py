from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .contracts import FinancialState,Hypothesis,ResearchJob,digest
from .adapters import to_athena_research_request,to_nexus_research_request
from .firewall import research_envelope,assert_no_execution_authority

@dataclass(frozen=True,slots=True)
class OutboundResearchRequest:
    request_id:str
    job_id:str
    hypothesis_id:str
    target_system:str
    emitted_ns:int
    schema:str
    payload:dict[str,Any]
    production_authorized:bool=False
    def __post_init__(self):
        if not all((self.request_id,self.job_id,self.hypothesis_id,self.target_system,self.schema)) or self.emitted_ns<0: raise ValueError("invalid outbound request")
        if self.production_authorized: raise ValueError("ORACLE cannot authorize production")
        assert_no_execution_authority(self.payload)


def build_request(job:ResearchJob,h:Hypothesis,*,emitted_ns:int,state:FinancialState|None=None,task_payload:dict[str,Any]|None=None)->OutboundResearchRequest:
    if len(job.required_systems)!=1: raise ValueError("one target system per dispatch request")
    target=job.required_systems[0].upper()
    common={"job_id":job.job_id,"hypothesis_id":h.hypothesis_id,"task_type":job.task_type,"target":h.target,"horizon":h.horizon,"falsification_criteria":list(h.falsification_criteria),"required_states":list(job.required_states),"task_payload":dict(task_payload or {})}
    if state is not None: common["financial_state"]={"state_id":state.state_id,"decision_ns":state.decision_ns,"confidence":state.confidence,"ood_score":state.ood_score,"state_hash":state.state_hash}
    if target=="NEXUS": body={**common,"nexus_request":to_nexus_research_request(h)}; schema="oracle.nexus.research-request.v1"
    elif target=="ATHENA": body={**common,"athena_request":to_athena_research_request(job)}; schema="oracle.athena.research-request.v1"
    elif target=="AION": body={**common,"query":{"mode":"historical_analogue","as_of_ns":emitted_ns,"causal_only":True}}; schema="oracle.aion.research-query.v1"
    elif target=="ARGUS": body={**common,"query":{"mode":"microstructure_context","max_evidence_tier":"CANDLE_PROXY","truth_claim":False}}; schema="oracle.argus.research-query.v1"
    elif target=="DAEDALUS": body={**common,"candidate_status":"RESEARCH_CANDIDATE_ONLY","production_authorized":False}; schema="oracle.daedalus.research-request.v1"
    else: body=common; schema=f"oracle.{target.lower()}.research-request.v1"
    env=research_envelope(body,schema=schema,purpose=f"{target}_RESEARCH_REQUEST")
    rid="REQ-"+digest({"job":job.job_id,"target":target,"emitted_ns":emitted_ns,"payload":env})[:20]
    return OutboundResearchRequest(rid,job.job_id,h.hypothesis_id,target,emitted_ns,schema,env,False)
