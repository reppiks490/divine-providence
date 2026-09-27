import pytest
from athena.contracts import *
from athena.firewall import *
from athena.router import route_experts
from athena.risk import govern
from athena.uncertainty import Uncertainty
from athena.scheduler import rank_requests


def test_firewall_blocks_research_direct_to_production():
    p=Provenance(1,2,"s","r","v",DataPlane.RESEARCH,"l")
    with pytest.raises(PlaneViolation): forbid_research_to_production_direct(p)

def test_router_and_governor_abstention():
    s=WorldState("trend",0.9,0.1,0.2,20,{})
    e=[ExpertEvidence("a",0.9,0.05,0.1,0.95,("trend",))]
    w=route_experts(s,e)
    assert w["a"] == pytest.approx(1.0)
    adv=govern(s,Uncertainty(0.1,0.1,0.1,0.1),w,evidence_version="x")
    assert not adv.abstain and not adv.production_authorized and 0 < adv.risk_multiplier <= 1
    bad=govern(WorldState("x",0.2,0.9,1,1,{}),Uncertainty(.9,.9,.9,.9),w,evidence_version="x")
    assert bad.abstain and bad.risk_multiplier == 0

def test_scheduler_prefers_information_value_per_cost():
    a=ResearchRequest("a",1,1,1,10)
    b=ResearchRequest("b",.8,1,1,1)
    assert rank_requests([a,b])[0].hypothesis_family == "b"
