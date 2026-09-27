import copy, random, unittest
from collision_detector_v0_2_1 import analyze_ecosystem


def m(name):
    return {"system":name,"owned_domains":[],"mutation_rights":[],"requires":[],"forbids":[],"interfaces":[],"shared_state":[],"coordination_contracts":[]}


def reference_has_cycle(graph, nodes):
    WHITE, GRAY, BLACK = 0,1,2
    state={n:WHITE for n in nodes}
    def dfs(n):
        state[n]=GRAY
        for x in graph.get(n,[]):
            if x not in state:
                continue
            if state[x]==GRAY:return True
            if state[x]==WHITE and dfs(x):return True
        state[n]=BLACK
        return False
    return any(state[n]==WHITE and dfs(n) for n in nodes)

class AdversarialTests(unittest.TestCase):
    def test_inputs_are_not_mutated(self):
        manifests={"A":m("A"),"B":m("B")}; graph={"A":["B"]}
        before_m=copy.deepcopy(manifests); before_g=copy.deepcopy(graph)
        analyze_ecosystem(manifests,graph)
        self.assertEqual(manifests,before_m); self.assertEqual(graph,before_g)

    def test_diamond_dag_is_not_cycle(self):
        manifests={x:m(x) for x in "ABCD"}
        r=analyze_ecosystem(manifests,{"A":["B","C"],"B":["D"],"C":["D"]})
        self.assertFalse(any(f["code"]=="DEPENDENCY_CYCLE" for f in r["findings"]))

    def test_self_loop_is_cycle(self):
        r=analyze_ecosystem({"A":m("A")},{"A":["A"]})
        self.assertTrue(any(f["code"]=="DEPENDENCY_CYCLE" for f in r["findings"]))

    def test_disconnected_cycle_detected(self):
        manifests={x:m(x) for x in "ABCD"}
        r=analyze_ecosystem(manifests,{"A":["B"],"C":["D"],"D":["C"]})
        self.assertTrue(any(f["code"]=="DEPENDENCY_CYCLE" for f in r["findings"]))

    def test_500_random_graphs_match_independent_cycle_oracle(self):
        rng=random.Random(20260924)
        nodes=list("ABCDEF")
        manifests={n:m(n) for n in nodes}
        for _ in range(500):
            graph={n:[x for x in nodes if rng.random()<0.15] for n in nodes}
            expected=reference_has_cycle(graph,nodes)
            r=analyze_ecosystem(manifests,graph)
            got=any(f["code"]=="DEPENDENCY_CYCLE" for f in r["findings"])
            self.assertEqual(got,expected,graph)

    def test_300_transitive_collisions_fail_safe(self):
        rng=random.Random(7)
        for _ in range(300):
            manifests={x:m(x) for x in "ABC"}
            resource=f"r{rng.randrange(20)}"
            manifests["A"]["mutation_rights"]=[resource]
            manifests["C"]["mutation_rights"]=[resource]
            r=analyze_ecosystem(manifests,{"A":["B"],"B":["C"]})
            self.assertFalse(r["safe"])
            self.assertTrue(any(f["code"]=="TRANSITIVE_MUTATION_COLLISION" for f in r["findings"]))

if __name__=='__main__':unittest.main()
