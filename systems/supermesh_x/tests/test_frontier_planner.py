import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from frontier_planner import rank_frontier, should_continue


def test_frontier_prefers_novel_relevant_low_cost_independent_sources():
    items=[
      {'id':'a','relevance':.9,'novelty':.8,'cost':1,'family_seen':False},
      {'id':'b','relevance':.95,'novelty':.2,'cost':1,'family_seen':True},
      {'id':'c','relevance':.7,'novelty':.9,'cost':4,'family_seen':False},
    ]
    ranked=rank_frontier(items)
    assert ranked[0]['id']=='a'


def test_stop_when_recent_novelty_yield_is_too_low_or_budget_exhausted():
    assert should_continue([.01,.02,.01], remaining_budget=10, min_yield=.05, patience=3) is False
    assert should_continue([.2,.01,.01], remaining_budget=10, min_yield=.05, patience=3) is True
    assert should_continue([.5], remaining_budget=0, min_yield=.05, patience=3) is False
