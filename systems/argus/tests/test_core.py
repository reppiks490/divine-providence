import pytest
from argus.contracts import *
from argus.orderflow import flow_stats
from argus.bookmap import book_stats
from argus.execution import walk_book
from argus.proxy import candle_pressure
from argus.fusion import require_true_depth
from argus.orderblocks import score_order_block, composite_score


def book():
    return BookSnapshot(1,(BookLevel(99,10),BookLevel(98,20)),(BookLevel(101,8),BookLevel(102,20)))

def test_true_orderflow_and_depth():
    fs=flow_stats([Trade(1,100,5,1),Trade(2,101,3,1),Trade(3,100,2,-1)])
    assert fs.evidence_tier is EvidenceTier.TRUE_TRADE and fs.signed_volume == 6
    bs=book_stats(book())
    assert bs.evidence_tier is EvidenceTier.TRUE_DEPTH and bs.best_bid==99 and bs.best_ask==101

def test_book_walk_has_positive_slippage_when_sweeping():
    e=walk_book(book(),1,15)
    assert e.filled_size==15 and e.slippage is not None and e.slippage>0

def test_proxy_never_masquerades_as_depth():
    f=candle_pressure(event_time_ns=1,source_id="x",open_=100,high=102,low=99,close=101,volume=100)
    assert all(x.evidence_tier is EvidenceTier.CANDLE_PROXY for x in f)
    with pytest.raises(ValueError): require_true_depth(f)

def test_order_block_evidence_tier_penalty():
    kw=dict(direction=1,lower=99,upper=100,origin_time_ns=1,displacement_atr=2,signed_flow_alignment=.8,depth_vacuum=.8,revisit_rejection=.8)
    proxy=score_order_block(**kw,evidence_tier=EvidenceTier.CANDLE_PROXY)
    l2=score_order_block(**kw,evidence_tier=EvidenceTier.TRUE_DEPTH)
    assert composite_score(l2)>composite_score(proxy)
