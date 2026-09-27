import unittest
from collision_detector_v0_2_1 import analyze_ecosystem


def manifest(name, owned=(), mutate=(), requires=(), forbids=(), interfaces=(), shared=(), coordination=()):
    return {
        "system": name,
        "owned_domains": list(owned),
        "mutation_rights": list(mutate),
        "requires": list(requires),
        "forbids": list(forbids),
        "interfaces": [{"name": n, "version": v} for n, v in interfaces],
        "shared_state": list(shared),
        "coordination_contracts": list(coordination),
    }


class CollisionDetectorTests(unittest.TestCase):
    def setUp(self):
        self.base = {
            "A": manifest("A", owned=["eval"], mutate=["a-state"]),
            "B": manifest("B", owned=["trend"], mutate=["b-state"]),
            "C": manifest("C", owned=["infra"], mutate=["c-state"]),
        }

    def test_detects_dependency_cycle_with_path(self):
        r = analyze_ecosystem(self.base, {"A": ["B"], "B": ["A"]})
        cycles = [f for f in r["findings"] if f["code"] == "DEPENDENCY_CYCLE"]
        self.assertTrue(cycles)
        self.assertGreaterEqual(len(cycles[0]["path"]), 3)
        self.assertEqual(cycles[0]["path"][0], cycles[0]["path"][-1])

    def test_detects_multihop_mutation_collision_and_preserves_path(self):
        m = {k: dict(v) for k, v in self.base.items()}
        m["C"] = dict(m["C"], mutation_rights=["a-state"])
        r = analyze_ecosystem(m, {"A": ["B"], "B": ["C"]})
        hit = [f for f in r["findings"] if f["code"] == "TRANSITIVE_MUTATION_COLLISION"]
        self.assertTrue(hit)
        self.assertEqual(hit[0]["path"], ["A", "B", "C"])
        self.assertFalse(r["safe"])

    def test_missing_manifest_is_policy_warning_by_default(self):
        r = analyze_ecosystem(self.base, {"A": ["D"]})
        self.assertTrue(any(f["code"] == "MISSING_DEPENDENCY_MANIFEST" for f in r["findings"]))
        self.assertTrue(r["safe"])

    def test_missing_manifest_can_be_configured_blocking(self):
        r = analyze_ecosystem(self.base, {"A": ["D"]}, policy={"missing_manifest": "critical"})
        self.assertFalse(r["safe"])

    def test_direct_interface_version_conflict(self):
        m = {
            "A": manifest("A", interfaces=[("packet", "1")]),
            "B": manifest("B", interfaces=[("packet", "2")]),
        }
        r = analyze_ecosystem(m, {})
        self.assertTrue(any(f["code"] == "INTERFACE_VERSION_CONFLICT" for f in r["findings"]))

    def test_coordinated_shared_state_not_flagged(self):
        m = {
            "A": manifest("A", shared=["registry"], coordination=["registry"]),
            "B": manifest("B", shared=["registry"], coordination=["registry"]),
        }
        r = analyze_ecosystem(m, {})
        self.assertFalse(any(f["code"] == "UNCOORDINATED_SHARED_STATE" for f in r["findings"]))

    def test_uncoordinated_shared_state_flagged(self):
        m = {
            "A": manifest("A", shared=["registry"]),
            "B": manifest("B", shared=["registry"]),
        }
        r = analyze_ecosystem(m, {})
        self.assertTrue(any(f["code"] == "UNCOORDINATED_SHARED_STATE" for f in r["findings"]))


if __name__ == "__main__":
    unittest.main()
