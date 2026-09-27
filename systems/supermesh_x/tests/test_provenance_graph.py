import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from provenance_graph import build_graph, lineage_for


def test_graph_deduplicates_source_nodes_and_tracks_derivation():
    records=[
      {'id':'e1','source':'https://a','content_hash':'h1','parents':[]},
      {'id':'e2','source':'https://a','content_hash':'h1','parents':['e1']},
      {'id':'e3','source':'https://b','content_hash':'h2','parents':['e2']},
    ]
    graph=build_graph(records)
    assert graph['source_nodes']==2
    assert graph['evidence_nodes']==3
    assert graph['acyclic'] is True
    assert lineage_for(graph,'e3')==['e1','e2','e3']


def test_cycle_is_detected():
    records=[
      {'id':'a','source':'s1','content_hash':'x','parents':['b']},
      {'id':'b','source':'s2','content_hash':'y','parents':['a']},
    ]
    graph=build_graph(records)
    assert graph['acyclic'] is False
