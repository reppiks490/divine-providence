import copy, unittest
from collision_detector_v0_3 import analyze_ecosystem
def M(**kw):
 d={"owned_domains":[],"mutation_rights":[],"interfaces":[],"requires":[],"forbids":[],"shared_state":[],"coordination_contracts":[]}; d.update(kw); return d
class T(unittest.TestCase):
 def test_clean(self): self.assertTrue(analyze_ecosystem({"A":M(),"B":M()},{})["collision_free"])
 def test_semantic_contract(self):
  i1={"name":"handoff","version":"1","required_inputs":["manifest"],"emitted_outputs":["packet"],"assumptions":["signed"],"invariants":["read-only"]}
  i2=copy.deepcopy(i1);i2["invariants"]=["may mutate"]
  r=analyze_ecosystem({"A":M(interfaces=[i1]),"B":M(interfaces=[i2])},{})
  self.assertIn("SEMANTIC_INTERFACE_CONTRACT_CONFLICT",[x["code"] for x in r["findings"]])
 def test_same_contract_ok(self):
  i={"name":"x","version":"1","required_inputs":["a"],"emitted_outputs":["b"],"assumptions":[],"invariants":["read-only"]}
  self.assertNotIn("SEMANTIC_INTERFACE_CONTRACT_CONFLICT",[x["code"] for x in analyze_ecosystem({"A":M(interfaces=[i]),"B":M(interfaces=[copy.deepcopy(i)])},{})["findings"]])
 def test_version_conflict(self):
  self.assertIn("INTERFACE_VERSION_CONFLICT",[x["code"] for x in analyze_ecosystem({"A":M(interfaces=[{"name":"x","version":"1"}]),"B":M(interfaces=[{"name":"x","version":"2"}])},{})["findings"]])
 def test_all_paths(self):
  ms={x:M(mutation_rights=["R"] if x in ("A","D") else []) for x in "ABCD"}
  r=analyze_ecosystem(ms,{"A":["B","C"],"B":["D"],"C":["D"]})
  ps=[tuple(x["path"]) for x in r["findings"] if x["code"]=="TRANSITIVE_MUTATION_COLLISION" and x["origin"]=="A" and x["dependency"]=="D"]
  self.assertEqual(set(ps),{("A","B","D"),("A","C","D")})
 def test_cycle(self): self.assertIn("DEPENDENCY_CYCLE",[x["code"] for x in analyze_ecosystem({"A":M(),"B":M()},{"A":["B"],"B":["A"]})["findings"]])
 def test_missing_path(self):
  r=analyze_ecosystem({"A":M()},{"A":["X"]}); self.assertIn("MISSING_DEPENDENCY_MANIFEST",[x["code"] for x in r["findings"]])
 def test_immutable(self):
  ms={"A":M(),"B":M()};g={"A":["B"]};a=copy.deepcopy(ms);b=copy.deepcopy(g);analyze_ecosystem(ms,g);self.assertEqual(ms,a);self.assertEqual(g,b)
 def test_invalid_policy(self):
  with self.assertRaises(ValueError): analyze_ecosystem({"A":M()},{"A":["X"]},{"missing_manifest":"mega"})
if __name__=="__main__":unittest.main()
