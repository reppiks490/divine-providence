import json
import sys
import tempfile
from datetime import datetime, timedelta
import unittest
from pathlib import Path

from janus_infinity.core import JanusTwin, priority_score, sha256_bytes, stable_json


class JanusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "janus.db"
        self.twin = JanusTwin(self.db)

    def tearDown(self):
        self.twin.close()
        self.tmp.cleanup()

    def test_historical_supersession_is_not_false_contradiction(self):
        self.twin.add_fact({
            "subject":"NEXUS.tests","predicate":"passed","value":80,
            "valid_from":"2026-09-23T00:00:00Z","known_at":"2026-09-23T01:00:00Z","source":"old"
        })
        self.twin.add_fact({
            "subject":"NEXUS.tests","predicate":"passed","value":117,
            "valid_from":"2026-09-23T18:00:00Z","known_at":"2026-09-24T00:00:00Z","source":"new"
        })
        self.assertEqual([], self.twin.contradictions())
        current = self.twin.current_facts()
        self.assertEqual(117, current[0]["value"])

    def test_same_valid_boundary_conflict_is_detected(self):
        base = {
            "subject":"X","predicate":"status","valid_from":"2026-01-01T00:00:00Z","known_at":"2026-01-02T00:00:00Z"
        }
        self.twin.add_fact({**base, "value":"green", "source":"a"})
        self.twin.add_fact({**base, "value":"red", "source":"b"})
        c = self.twin.contradictions()
        self.assertEqual(1, len(c))
        self.assertEqual("X", c[0]["subject"])

    def test_as_known_at_prevents_hindsight(self):
        self.twin.add_fact({
            "subject":"X","predicate":"value","value":1,
            "valid_from":"2026-01-01T00:00:00Z","known_at":"2026-01-10T00:00:00Z","source":"late"
        })
        self.assertEqual([], self.twin.facts_as_known_at("2026-01-05T00:00:00Z"))
        self.assertEqual(1, len(self.twin.facts_as_known_at("2026-01-11T00:00:00Z")))

    def test_bitemporal_as_of_respects_validity_and_knowledge(self):
        self.twin.add_fact({
            "subject":"X","predicate":"mode","value":"old",
            "valid_from":"2026-01-01T00:00:00Z","valid_to":"2026-02-01T00:00:00Z",
            "known_at":"2026-01-01T01:00:00Z","source":"a"
        })
        self.twin.add_fact({
            "subject":"X","predicate":"mode","value":"new",
            "valid_from":"2026-02-01T00:00:00Z",
            "known_at":"2026-02-03T00:00:00Z","source":"b"
        })
        # On Feb 2 the new state is valid in project time, but was not learned yet.
        self.assertEqual([], self.twin.facts_as_of(
            "2026-02-02T00:00:00Z", "2026-02-02T00:00:00Z"))
        # Reconstructing Feb 2 after the Feb 3 observation may use the late-known fact.
        rows = self.twin.facts_as_of(
            "2026-02-02T00:00:00Z", "2026-02-04T00:00:00Z")
        self.assertEqual("new", rows[0]["value"])

    def test_current_facts_excludes_explicitly_expired_fact(self):
        self.twin.add_fact({
            "subject":"X","predicate":"flag","value":True,
            "valid_from":"2026-01-01T00:00:00Z","valid_to":"2026-01-02T00:00:00Z",
            "known_at":"2026-01-01T00:00:00Z","source":"a"
        })
        self.assertEqual([], self.twin.current_facts(valid_at="2026-01-03T00:00:00Z"))

    def test_priority_prefers_high_leverage_low_cost(self):
        a = dict(impact=.9, centrality=.9, uncertainty_reduction=.9, reusability=.9, failure_pressure=.9, evidence_gap=.9, cost=.2, regression_risk=.1, duplication_risk=.1)
        b = dict(a); b["cost"] = .8
        self.assertGreater(priority_score(a), priority_score(b))

    def test_snapshot_and_reconcile(self):
        repo = self.root / "repo"
        repo.mkdir()
        (repo / "a.txt").write_text("one")
        snap = self.twin.snapshot(repo, "base")
        self.assertTrue(snap["content_hash"])
        clean = self.twin.reconcile_root(repo)
        self.assertEqual("clean", clean["status"])
        (repo / "a.txt").write_text("two")
        drift = self.twin.reconcile_root(repo)
        self.assertEqual("drift", drift["status"])
        self.assertEqual(["a.txt"], drift["changed"])

    def test_handoff_is_deterministically_structured(self):
        self.twin.add_component("NEXUS", "market_data_fabric")
        self.twin.add_invariant("never invent availability")
        self.twin.add_candidate({
            "id":"C1","title":"round trip","impact":1,"centrality":1,"uncertainty_reduction":1,
            "reusability":1,"failure_pressure":1,"evidence_gap":1,"cost":.2,"regression_risk":.1,"duplication_risk":.1
        })
        out = self.root / "handoff"
        result = self.twin.export_handoff(out)
        self.assertTrue(Path(result["handoff_json"]).exists())
        data = json.loads(Path(result["handoff_json"]).read_text())
        self.assertEqual(self.twin.state_digest(), data["state_digest"])
        self.assertEqual("C1", data["prioritized_candidates"][0]["id"])

    def test_handoff_round_trip_reproduces_state_digest(self):
        self.twin.add_component("NEXUS", "market_data_fabric")
        self.twin.add_component("JANUS", "project_twin")
        self.twin.add_dependency("JANUS", "NEXUS")
        self.twin.add_fact({
            "subject":"NEXUS.tests","predicate":"passed","value":117,
            "valid_from":"2026-09-23T18:00:00Z","known_at":"2026-09-24T00:00:00Z","source":"freeze"
        })
        self.twin.add_invariant("preserve authority")
        self.twin.add_candidate({
            "id":"C1","title":"round trip","impact":1,"centrality":1,"uncertainty_reduction":1,
            "reusability":1,"failure_pressure":1,"evidence_gap":1,"cost":.2,"regression_risk":.1,"duplication_risk":.1
        })
        out = self.root / "handoff_rt"
        exported = self.twin.export_handoff(out)
        fresh = JanusTwin(self.root / "fresh.db")
        try:
            result = fresh.import_handoff(exported["handoff_json"])
            self.assertTrue(result["digest_match"])
            self.assertEqual(self.twin.state_digest(), fresh.state_digest())
        finally:
            fresh.close()


    def test_temporal_overlap_conflict_detected_across_different_valid_from(self):
        self.twin.add_fact({
            "subject":"NEXUS.mode","predicate":"status","value":"green",
            "valid_from":"2026-01-01T00:00:00Z","valid_to":"2026-02-01T00:00:00Z",
            "known_at":"2026-01-01T01:00:00Z","source":"a","authority":"observer"
        })
        self.twin.add_fact({
            "subject":"NEXUS.mode","predicate":"status","value":"red",
            "valid_from":"2026-01-15T00:00:00Z","valid_to":"2026-01-20T00:00:00Z",
            "known_at":"2026-01-15T01:00:00Z","source":"b","authority":"owner"
        })
        conflicts = self.twin.temporal_conflicts()
        self.assertEqual(1, len(conflicts))
        self.assertEqual("overlap_conflict", conflicts[0]["kind"])
        self.assertEqual("quarantined", conflicts[0]["resolution"]["status"])
        self.assertTrue(conflicts[0]["proof_required"])

    def test_authority_policy_resolves_overlap_and_reports_blast_radius(self):
        self.twin.add_component("NEXUS", "market_data_fabric")
        self.twin.add_component("JANUS", "project_twin")
        self.twin.add_component("AION", "decision_intelligence")
        self.twin.add_dependency("JANUS", "NEXUS")
        self.twin.add_dependency("AION", "JANUS")
        self.twin.set_authority_precedence("NEXUS", "status", "owner", 100)
        self.twin.set_authority_precedence("NEXUS", "status", "observer", 10)
        self.twin.add_fact({
            "subject":"NEXUS","predicate":"status","value":"green",
            "valid_from":"2026-01-01T00:00:00Z","valid_to":"2026-02-01T00:00:00Z",
            "known_at":"2026-01-01T01:00:00Z","source":"a","authority":"observer"
        })
        owner_id = self.twin.add_fact({
            "subject":"NEXUS","predicate":"status","value":"red",
            "valid_from":"2026-01-15T00:00:00Z","valid_to":"2026-01-20T00:00:00Z",
            "known_at":"2026-01-15T01:00:00Z","source":"b","authority":"owner"
        })
        conflict = self.twin.temporal_conflicts()[0]
        self.assertEqual("resolved", conflict["resolution"]["status"])
        self.assertEqual(owner_id, conflict["resolution"]["winner_fact_id"])
        self.assertFalse(conflict["proof_required"])
        self.assertEqual(["AION", "JANUS"], conflict["blast_radius"])

    def test_equal_authority_overlap_remains_quarantined(self):
        self.twin.set_authority_precedence("X", "mode", "peer", 50)
        for value, source in [("a", "s1"), ("b", "s2")]:
            self.twin.add_fact({
                "subject":"X","predicate":"mode","value":value,
                "valid_from":"2026-01-01T00:00:00Z","known_at":"2026-01-02T00:00:00Z",
                "source":source,"authority":"peer"
            })
        conflict = self.twin.temporal_conflicts()[0]
        self.assertEqual("quarantined", conflict["resolution"]["status"])
        self.assertEqual("authority_tie", conflict["resolution"]["reason"])

    def test_authority_policy_survives_handoff_round_trip(self):
        self.twin.set_authority_precedence("NEXUS", "status", "owner", 100)
        out = self.root / "authority_handoff"
        exported = self.twin.export_handoff(out)
        fresh = JanusTwin(self.root / "authority_fresh.db")
        try:
            result = fresh.import_handoff(exported["handoff_json"])
            self.assertTrue(result["digest_match"])
            row = fresh.conn.execute(
                "SELECT rank FROM authority_precedence WHERE subject_prefix='NEXUS' AND predicate='status' AND authority='owner'"
            ).fetchone()
            self.assertEqual(100, row[0])
        finally:
            fresh.close()


    def test_evidence_policy_breaks_equal_authority_tie_only_when_explicit(self):
        self.twin.set_authority_precedence("X", "mode", "owner", 100)
        self.twin.set_evidence_precedence("verified", 100)
        self.twin.set_evidence_precedence("reported", 10)
        low = self.twin.add_fact({
            "subject":"X","predicate":"mode","value":"old",
            "valid_from":"2026-01-01T00:00:00Z","known_at":"2026-01-01T01:00:00Z",
            "source":"report","authority":"owner","confidence":"reported"
        })
        high = self.twin.add_fact({
            "subject":"X","predicate":"mode","value":"new",
            "valid_from":"2026-01-02T00:00:00Z","known_at":"2026-01-02T01:00:00Z",
            "source":"proof","authority":"owner","confidence":"verified"
        })
        conflict = self.twin.temporal_conflicts()[0]
        self.assertEqual("resolved", conflict["resolution"]["status"])
        self.assertEqual(high, conflict["resolution"]["winner_fact_id"])
        self.assertEqual("explicit_evidence_precedence", conflict["resolution"]["reason"])
        self.assertNotEqual(low, high)

    def test_missing_evidence_policy_does_not_break_authority_tie(self):
        self.twin.set_authority_precedence("X", "mode", "owner", 100)
        for value, confidence in [("old", "reported"), ("new", "verified")]:
            self.twin.add_fact({
                "subject":"X","predicate":"mode","value":value,
                "valid_from":"2026-01-01T00:00:00Z","known_at":"2026-01-02T00:00:00Z",
                "source":value,"authority":"owner","confidence":confidence
            })
        conflict = self.twin.temporal_conflicts()[0]
        self.assertEqual("quarantined", conflict["resolution"]["status"])
        self.assertEqual("authority_tie", conflict["resolution"]["reason"])

    def test_temporal_normalization_proposes_but_does_not_mutate(self):
        old = self.twin.add_fact({
            "subject":"NEXUS.tests","predicate":"passed","value":80,
            "valid_from":"2026-01-01T00:00:00Z","known_at":"2026-01-01T01:00:00Z",
            "source":"same-lineage","authority":"owner"
        })
        new = self.twin.add_fact({
            "subject":"NEXUS.tests","predicate":"passed","value":117,
            "valid_from":"2026-01-02T00:00:00Z","known_at":"2026-01-02T01:00:00Z",
            "source":"same-lineage","authority":"owner"
        })
        proposals = self.twin.temporal_normalization_proposals()
        self.assertEqual(1, len(proposals))
        self.assertEqual(old, proposals[0]["close_fact_id"])
        self.assertEqual(new, proposals[0]["successor_fact_id"])
        self.assertEqual("2026-01-02T00:00:00Z", proposals[0]["proposed_valid_to"])
        row = self.twin.conn.execute("SELECT valid_to FROM facts WHERE fact_id=?", (old,)).fetchone()
        self.assertIsNone(row[0])

    def test_evidence_policy_survives_handoff_round_trip(self):
        self.twin.set_evidence_precedence("verified", 100)
        out = self.root / "evidence_handoff"
        exported = self.twin.export_handoff(out)
        fresh = JanusTwin(self.root / "evidence_fresh.db")
        try:
            result = fresh.import_handoff(exported["handoff_json"])
            self.assertTrue(result["digest_match"])
            row = fresh.conn.execute("SELECT rank FROM evidence_precedence WHERE confidence='verified'").fetchone()
            self.assertEqual(100, row[0])
        finally:
            fresh.close()

    def test_normalization_approval_creates_immutable_overlay(self):
        old = self.twin.add_fact({
            "subject":"NEXUS.tests","predicate":"passed","value":80,
            "valid_from":"2026-01-01T00:00:00Z","known_at":"2026-01-01T01:00:00Z",
            "source":"same-lineage","authority":"owner"
        })
        new = self.twin.add_fact({
            "subject":"NEXUS.tests","predicate":"passed","value":117,
            "valid_from":"2026-01-02T00:00:00Z","known_at":"2026-01-02T01:00:00Z",
            "source":"same-lineage","authority":"owner"
        })
        proposal = self.twin.temporal_normalization_proposals()[0]
        rec = self.twin.record_normalization_decision(proposal, "approved", "owner", ["proof:abc"], "2026-01-03T00:00:00Z")
        self.assertEqual("approved", rec["decision"])
        overlay = self.twin.normalization_overlays()[0]
        self.assertEqual(old, overlay["close_fact_id"])
        self.assertEqual(new, overlay["successor_fact_id"])
        self.assertEqual("2026-01-02T00:00:00Z", overlay["effective_valid_to"])
        row = self.twin.conn.execute("SELECT valid_to FROM facts WHERE fact_id=?", (old,)).fetchone()
        self.assertIsNone(row[0])

    def test_normalization_rejection_and_revocation_do_not_apply_overlay(self):
        old = self.twin.add_fact({"subject":"X","predicate":"v","value":1,"valid_from":"2026-01-01T00:00:00Z","known_at":"2026-01-01T00:00:00Z","source":"s","authority":"a"})
        self.twin.add_fact({"subject":"X","predicate":"v","value":2,"valid_from":"2026-01-02T00:00:00Z","known_at":"2026-01-02T00:00:00Z","source":"s","authority":"a"})
        p = self.twin.temporal_normalization_proposals()[0]
        rejected = self.twin.record_normalization_decision(p, "rejected", "a", ["proof:no"], "2026-01-03T00:00:00Z")
        self.assertEqual([], self.twin.normalization_overlays())
        approved = self.twin.record_normalization_decision(p, "approved", "a", ["proof:yes"], "2026-01-04T00:00:00Z")
        self.assertEqual(1, len(self.twin.normalization_overlays()))
        self.twin.revoke_normalization_decision(approved["decision_id"], "a", "proof withdrawn", "2026-01-05T00:00:00Z")
        self.assertEqual([], self.twin.normalization_overlays())
        self.assertEqual(old, p["close_fact_id"])

    def test_normalization_ledger_survives_handoff_round_trip(self):
        self.twin.add_fact({"subject":"X","predicate":"v","value":1,"valid_from":"2026-01-01T00:00:00Z","known_at":"2026-01-01T00:00:00Z","source":"s","authority":"a"})
        self.twin.add_fact({"subject":"X","predicate":"v","value":2,"valid_from":"2026-01-02T00:00:00Z","known_at":"2026-01-02T00:00:00Z","source":"s","authority":"a"})
        p = self.twin.temporal_normalization_proposals()[0]
        self.twin.record_normalization_decision(p, "approved", "a", ["proof:yes"], "2026-01-03T00:00:00Z")
        out = self.root / "norm_handoff"
        exported = self.twin.export_handoff(out)
        fresh = JanusTwin(self.root / "norm_fresh.db")
        try:
            result = fresh.import_handoff(exported["handoff_json"])
            self.assertTrue(result["digest_match"])
            self.assertEqual(1, len(fresh.normalization_overlays()))
        finally:
            fresh.close()


    def _proved_bundle_ref(self, change_id="norm-proof"):
        bundle = {
            "change_id": change_id,
            "claim": "approve temporal normalization",
            "precondition_snapshot": "pre",
            "evidence": [{"kind": "test"}],
            "verification": [{"status": "passed"}],
            "rollback": {"kind": "revoke_overlay"},
            "status": "proved",
        }
        h = self.twin.add_proof_bundle(bundle)
        return f"proof:{change_id}:{h}"

    def test_facts_as_of_applies_verified_overlay_only_after_decision_known(self):
        old = self.twin.add_fact({"subject":"X","predicate":"v","value":1,"valid_from":"2026-01-01T00:00:00Z","known_at":"2026-01-01T00:00:00Z","source":"s","authority":"a"})
        self.twin.add_fact({"subject":"X","predicate":"v","value":2,"valid_from":"2026-01-10T00:00:00Z","known_at":"2026-01-10T00:00:00Z","source":"s","authority":"a"})
        p = self.twin.temporal_normalization_proposals()[0]
        ref = self._proved_bundle_ref()
        self.twin.record_normalization_decision(p, "approved", "a", [ref], "2026-01-20T00:00:00Z")
        # Before the approval was known, historical reconstruction keeps original semantics.
        before = self.twin.facts_as_of("2026-01-15T00:00:00Z", "2026-01-15T00:00:00Z")
        self.assertEqual(2, before[0]["value"])
        # After approval is known, the overlay closes the old interval; successor remains authoritative.
        after = self.twin.facts_as_of("2026-01-15T00:00:00Z", "2026-01-21T00:00:00Z")
        self.assertEqual(2, after[0]["value"])
        verified = self.twin.verified_normalization_overlays("2026-01-21T00:00:00Z")
        self.assertEqual(old, verified[0]["close_fact_id"])

    def test_unbound_proof_reference_cannot_change_reconstructed_truth(self):
        self.twin.add_fact({"subject":"X","predicate":"v","value":1,"valid_from":"2026-01-01T00:00:00Z","known_at":"2026-01-01T00:00:00Z","source":"s","authority":"a"})
        self.twin.add_fact({"subject":"X","predicate":"v","value":2,"valid_from":"2026-01-10T00:00:00Z","known_at":"2026-01-10T00:00:00Z","source":"s","authority":"a"})
        p = self.twin.temporal_normalization_proposals()[0]
        self.twin.record_normalization_decision(p, "approved", "a", ["proof:legacy"], "2026-01-20T00:00:00Z")
        self.assertEqual([], self.twin.verified_normalization_overlays("2026-01-21T00:00:00Z"))

    def test_hash_mismatch_blocks_overlay(self):
        self.twin.add_fact({"subject":"X","predicate":"v","value":1,"valid_from":"2026-01-01T00:00:00Z","known_at":"2026-01-01T00:00:00Z","source":"s","authority":"a"})
        self.twin.add_fact({"subject":"X","predicate":"v","value":2,"valid_from":"2026-01-10T00:00:00Z","known_at":"2026-01-10T00:00:00Z","source":"s","authority":"a"})
        p = self.twin.temporal_normalization_proposals()[0]
        self._proved_bundle_ref("p1")
        self.twin.record_normalization_decision(p, "approved", "a", ["proof:p1:" + "0"*64], "2026-01-20T00:00:00Z")
        self.assertEqual([], self.twin.verified_normalization_overlays())

    def test_revocation_is_knowledge_time_aware_for_verified_overlay(self):
        self.twin.add_fact({"subject":"X","predicate":"v","value":1,"valid_from":"2026-01-01T00:00:00Z","known_at":"2026-01-01T00:00:00Z","source":"s","authority":"a"})
        self.twin.add_fact({"subject":"X","predicate":"v","value":2,"valid_from":"2026-01-10T00:00:00Z","known_at":"2026-01-10T00:00:00Z","source":"s","authority":"a"})
        p = self.twin.temporal_normalization_proposals()[0]
        ref = self._proved_bundle_ref("p2")
        d = self.twin.record_normalization_decision(p, "approved", "a", [ref], "2026-01-20T00:00:00Z")
        self.twin.revoke_normalization_decision(d["decision_id"], "a", "proof withdrawn", "2026-01-25T00:00:00Z")
        self.assertEqual(1, len(self.twin.verified_normalization_overlays("2026-01-24T00:00:00Z")))
        self.assertEqual(0, len(self.twin.verified_normalization_overlays("2026-01-26T00:00:00Z")))


    def test_proof_lifecycle_revocation_is_knowledge_time_aware(self):
        ref = self._proved_bundle_ref("life1")
        self.twin.record_proof_lifecycle_event(
            "life1", "revoked", "2026-01-25T00:00:00Z", "owner", "evidence invalidated"
        )
        self.assertTrue(self.twin._verify_proof_ref(ref, "2026-01-24T00:00:00Z")["verified"])
        after = self.twin._verify_proof_ref(ref, "2026-01-26T00:00:00Z")
        self.assertFalse(after["verified"])
        self.assertEqual("proof_status_revoked", after["reason"])

    def test_temporal_conflict_replay_tracks_overlay_and_proof_revocation(self):
        self.twin.add_fact({"subject":"X","predicate":"v","value":1,"valid_from":"2026-01-01T00:00:00Z","known_at":"2026-01-01T00:00:00Z","source":"s","authority":"a"})
        self.twin.add_fact({"subject":"X","predicate":"v","value":2,"valid_from":"2026-01-10T00:00:00Z","known_at":"2026-01-10T00:00:00Z","source":"s","authority":"a"})
        p = self.twin.temporal_normalization_proposals()[0]
        ref = self._proved_bundle_ref("life2")
        self.twin.record_normalization_decision(p, "approved", "a", [ref], "2026-01-20T00:00:00Z")
        before = self.twin.temporal_conflicts_as_of("2026-01-15T00:00:00Z", "2026-01-15T00:00:00Z")
        self.assertEqual(1, len(before))
        after_approval = self.twin.temporal_conflicts_as_of("2026-01-15T00:00:00Z", "2026-01-21T00:00:00Z")
        self.assertEqual([], after_approval)
        self.twin.record_proof_lifecycle_event("life2", "revoked", "2026-01-25T00:00:00Z", "owner", "proof withdrawn")
        after_revocation = self.twin.temporal_conflicts_as_of("2026-01-15T00:00:00Z", "2026-01-26T00:00:00Z")
        self.assertEqual(1, len(after_revocation))

    def test_temporal_conflict_replay_carries_blast_radius_and_lineage(self):
        self.twin.add_component("X", "owner")
        self.twin.add_component("Y", "consumer")
        self.twin.add_dependency("Y", "X")
        self.twin.add_fact({"subject":"X.mode","predicate":"state","value":"a","valid_from":"2026-01-01T00:00:00Z","known_at":"2026-01-01T00:00:00Z","source":"s1","authority":"owner"})
        self.twin.add_fact({"subject":"X.mode","predicate":"state","value":"b","valid_from":"2026-01-02T00:00:00Z","known_at":"2026-01-02T00:00:00Z","source":"s2","authority":"owner"})
        replay = self.twin.temporal_conflicts_as_of("2026-01-03T00:00:00Z", "2026-01-03T00:00:00Z")
        self.assertEqual(["Y"], replay[0]["blast_radius"])
        self.assertEqual([], replay[0]["normalization_lineage"])
        self.assertEqual("2026-01-03T00:00:00Z", replay[0]["replay"]["valid_at"])

    def test_proof_lifecycle_survives_handoff_round_trip(self):
        self._proved_bundle_ref("life3")
        event = self.twin.record_proof_lifecycle_event(
            "life3", "superseded", "2026-02-01T00:00:00Z", "owner", "replacement proof", "life4"
        )
        out = self.root / "life_handoff"
        exported = self.twin.export_handoff(out)
        fresh = JanusTwin(self.root / "life_fresh.db")
        try:
            result = fresh.import_handoff(exported["handoff_json"])
            self.assertTrue(result["digest_match"])
            rows = fresh.proof_lifecycle_events("life3")
            self.assertEqual(1, len(rows))
            self.assertEqual(event["event_id"], rows[0]["event_id"])
            self.assertEqual("life4", rows[0]["superseded_by"])
        finally:
            fresh.close()


    def test_proof_lifecycle_rejects_unknown_proof_target(self):
        with self.assertRaises(KeyError):
            self.twin.record_proof_lifecycle_event(
                "missing-proof", "revoked", "2026-01-25T00:00:00Z", "owner", "invalid target"
            )


    def test_proof_lifecycle_rejects_conflicting_same_knowledge_boundary(self):
        self._proved_bundle_ref("life-conflict")
        self.twin.record_proof_lifecycle_event(
            "life-conflict", "revoked", "2026-03-01T00:00:00Z", "owner", "withdrawn"
        )
        with self.assertRaises(ValueError):
            self.twin.record_proof_lifecycle_event(
                "life-conflict", "integrated", "2026-03-01T00:00:00Z", "owner", "contradictory same-time state"
            )

if __name__ == "__main__":
    unittest.main()

# Run 008 proof provenance DAG + historical archive regressions
class JanusRun008Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name); self.twin = JanusTwin(self.root/'janus8.db')
    def tearDown(self): self.twin.close(); self.tmp.cleanup()
    def _bundle(self, cid):
        b={"change_id":cid,"status":"proved","claim":"proof "+cid}; return self.twin.add_proof_bundle(b)
    def test_proof_provenance_detects_missing_supersession_target(self):
        self._bundle('a')
        self.twin.record_proof_lifecycle_event('a','superseded','2026-01-02T00:00:00Z','owner','replace','missing')
        g=self.twin.proof_provenance_graph('2026-01-03T00:00:00Z')
        self.assertFalse(g['valid'])
        self.assertEqual('missing_target', g['errors'][0]['type'])
    def test_proof_provenance_rejects_supersession_cycle(self):
        self._bundle('a'); self._bundle('b')
        self.twin.record_proof_lifecycle_event('a','superseded','2026-01-02T00:00:00Z','owner','replace','b')
        with self.assertRaises(ValueError):
            self.twin.record_proof_lifecycle_event('b','superseded','2026-01-03T00:00:00Z','owner','cycle','a')
    def test_proof_provenance_chain_reports_terminal_and_validity(self):
        self._bundle('a'); self._bundle('b'); self._bundle('c')
        self.twin.record_proof_lifecycle_event('a','superseded','2026-01-02T00:00:00Z','owner','r','b')
        self.twin.record_proof_lifecycle_event('b','superseded','2026-01-03T00:00:00Z','owner','r','c')
        g=self.twin.proof_provenance_graph('2026-01-04T00:00:00Z')
        self.assertEqual(['a','b','c'], g['chains'][0]['path'])
        self.assertEqual('c', g['chains'][0]['terminal'])
        self.assertTrue(g['valid'])
    def test_historical_archive_roundtrip_replays_old_conflict(self):
        self.twin.add_fact({"subject":"X","predicate":"v","value":1,"valid_from":"2026-01-01T00:00:00Z","known_at":"2026-01-01T00:00:00Z","source":"s1","authority":"a"})
        self.twin.add_fact({"subject":"X","predicate":"v","value":2,"valid_from":"2026-01-02T00:00:00Z","known_at":"2026-01-02T00:00:00Z","source":"s2","authority":"a"})
        out=self.root/'archive'; exp=self.twin.export_historical_archive(out)
        fresh=JanusTwin(self.root/'fresh.db')
        try:
            result=fresh.import_historical_archive(exp['archive_json'])
            self.assertTrue(result['archive_digest_match'])
            self.assertEqual(1,len(fresh.temporal_conflicts_as_of('2026-01-03T00:00:00Z','2026-01-03T00:00:00Z')))
        finally: fresh.close()

class JanusRun009Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.twin=JanusTwin(self.root/'janus9.db')
    def tearDown(self): self.twin.close(); self.tmp.cleanup()
    def _bundle_ref(self,cid='impact-proof'):
        bundle={'change_id':cid,'status':'proved','claim':'normalization proof'}
        h=self.twin.add_proof_bundle(bundle); return f'proof:{cid}:{h}'
    def test_unified_adjudication_kernel_matches_archive_and_replay(self):
        self.twin.set_authority_precedence('X','v','a',10); self.twin.set_authority_precedence('X','v','b',10)
        self.twin.set_evidence_precedence('reported',1); self.twin.set_evidence_precedence('verified',5)
        self.twin.add_fact({'subject':'X','predicate':'v','value':1,'valid_from':'2026-01-01T00:00:00Z','known_at':'2026-01-01T00:00:00Z','source':'s1','authority':'a','confidence':'reported'})
        self.twin.add_fact({'subject':'X','predicate':'v','value':2,'valid_from':'2026-01-02T00:00:00Z','known_at':'2026-01-02T00:00:00Z','source':'s2','authority':'b','confidence':'verified'})
        archival=self.twin.temporal_conflicts()[0]['resolution']
        replay=self.twin.temporal_conflicts_as_of('2026-01-03T00:00:00Z','2026-01-03T00:00:00Z')[0]['resolution']
        self.assertEqual(archival,replay)
        self.assertEqual('explicit_evidence_precedence', replay['reason'])
    def test_proof_impact_graph_traces_revocation_to_conflict_and_blast_radius(self):
        self.twin.add_component('X','owner'); self.twin.add_component('Y','consumer'); self.twin.add_dependency('Y','X')
        self.twin.add_fact({'subject':'X.mode','predicate':'state','value':'old','valid_from':'2026-01-01T00:00:00Z','known_at':'2026-01-01T00:00:00Z','source':'s','authority':'owner'})
        self.twin.add_fact({'subject':'X.mode','predicate':'state','value':'new','valid_from':'2026-01-10T00:00:00Z','known_at':'2026-01-10T00:00:00Z','source':'s','authority':'owner'})
        proposal=self.twin.temporal_normalization_proposals()[0]; ref=self._bundle_ref()
        decision=self.twin.record_normalization_decision(proposal,'approved','owner',[ref],'2026-01-20T00:00:00Z')
        self.twin.record_proof_lifecycle_event('impact-proof','revoked','2026-01-25T00:00:00Z','owner','withdrawn')
        impact=self.twin.proof_impact_graph('impact-proof','2026-01-15T00:00:00Z','2026-01-24T00:00:00Z','2026-01-26T00:00:00Z')
        self.assertEqual([decision['decision_id']], impact['normalization_decision_ids'])
        self.assertEqual(0, impact['before']['conflict_count']); self.assertEqual(1, impact['after']['conflict_count'])
        self.assertEqual(['Y'], impact['blast_radius'])
        self.assertEqual('conflict_reappeared', impact['conflict_delta'][0]['change'])
    def test_proof_impact_graph_rejects_reversed_knowledge_window(self):
        self._bundle_ref('p')
        with self.assertRaises(ValueError):
            self.twin.proof_impact_graph('p','2026-01-01T00:00:00Z','2026-01-03T00:00:00Z','2026-01-02T00:00:00Z')

class JanusRun010Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.twin=JanusTwin(self.root/'janus10.db')
    def tearDown(self): self.twin.close(); self.tmp.cleanup()
    def _scenario(self):
        self.twin.add_component('X','owner'); self.twin.add_component('Y','consumer'); self.twin.add_component('Z','consumer'); self.twin.add_dependency('Y','X'); self.twin.add_dependency('Z','Y')
        self.twin.add_fact({'subject':'X.mode','predicate':'state','value':'old','valid_from':'2026-01-01T00:00:00Z','known_at':'2026-01-01T00:00:00Z','source':'s','authority':'owner'})
        self.twin.add_fact({'subject':'X.mode','predicate':'state','value':'new','valid_from':'2026-01-10T00:00:00Z','known_at':'2026-01-10T00:00:00Z','source':'s','authority':'owner'})
        p=self.twin.temporal_normalization_proposals()[0]
        b={'change_id':'p1','status':'proved','claim':'normalization proof'}; h=self.twin.add_proof_bundle(b); ref=f'proof:p1:{h}'
        self.twin.record_normalization_decision(p,'approved','owner',[ref],'2026-01-20T00:00:00Z')
        self.twin.record_proof_lifecycle_event('p1','revoked','2026-01-25T00:00:00Z','owner','withdrawn')
    def test_automatic_causal_horizon_discovers_interval_and_transition(self):
        self._scenario(); h=self.twin.automatic_causal_horizon('p1')
        self.assertEqual('2026-01-10T00:00:00Z', h['affected_validity_intervals'][0]['start'])
        self.assertIn('2026-01-10T00:00:00Z', h['replay_valid_at'])
        self.assertTrue(any(w['event_status']=='revoked' for w in h['knowledge_transitions']))
    def test_automatic_causal_horizon_finds_conflict_and_transitive_exposure(self):
        self._scenario(); h=self.twin.automatic_causal_horizon('p1')
        self.assertTrue(any(d['change']=='conflict_reappeared' for d in h['conflict_deltas']))
        self.assertEqual(['Y','Z'], h['blast_radius'])
        self.assertGreater(h['exposure']['score'], 0)
    def test_automatic_causal_horizon_follows_connected_proof_chain(self):
        self._scenario(); h2=self.twin.add_proof_bundle({'change_id':'p2','status':'proved','claim':'replacement'})
        self.twin.record_proof_lifecycle_event('p1','superseded','2026-01-30T00:00:00Z','owner','replacement','p2')
        h=self.twin.automatic_causal_horizon('p2')
        self.assertEqual(['p1','p2'], h['proof_chain'])
        self.assertTrue(h['normalization_decision_ids'])
    def test_causal_horizon_preserves_historical_supersession_after_later_status(self):
        self.twin.add_proof_bundle({"change_id":"a","status":"proved","claim":"a"}); self.twin.add_proof_bundle({"change_id":"b","status":"proved","claim":"b"})
        self.twin.record_proof_lifecycle_event("a","superseded","2026-01-02T00:00:00Z","owner","replace","b")
        self.twin.record_proof_lifecycle_event("a","revoked","2026-01-03T00:00:00Z","owner","withdraw old proof")
        h=self.twin.automatic_causal_horizon("b")
        self.assertEqual(["a","b"], h["proof_chain"])

    def test_causal_certificate_is_deterministic(self):
        self._scenario(); a=self.twin.automatic_causal_horizon('p1'); b=self.twin.automatic_causal_horizon('p1')
        self.assertEqual(a['certificate']['digest'], b['certificate']['digest'])

class JanusRun011Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.twin=JanusTwin(self.root/'janus11.db')
    def tearDown(self): self.twin.close(); self.tmp.cleanup()
    def _scenario(self):
        self.twin.add_component('X','owner'); self.twin.add_component('Y','consumer'); self.twin.add_dependency('Y','X')
        self.twin.add_fact({'subject':'X.mode','predicate':'state','value':'old','valid_from':'2026-01-01T00:00:00Z','known_at':'2026-01-01T00:00:00Z','source':'s','authority':'owner'})
        self.twin.add_fact({'subject':'X.mode','predicate':'state','value':'new','valid_from':'2026-01-10T00:00:00Z','known_at':'2026-01-10T00:00:00Z','source':'s','authority':'owner'})
        p=self.twin.temporal_normalization_proposals()[0]
        h=self.twin.add_proof_bundle({'change_id':'p1','status':'proved','claim':'normalization proof'}); ref=f'proof:p1:{h}'
        self.twin.record_normalization_decision(p,'approved','owner',[ref],'2026-01-20T00:00:00Z')
        self.twin.record_proof_lifecycle_event('p1','revoked','2026-01-25T00:00:00Z','owner','withdrawn')
    def test_generalized_truth_delta_detects_non_conflict_value_change(self):
        self._scenario(); report=self.twin.generalized_truth_delta('p1')
        added=[d for d in report['truth_deltas'] if d['change']=='added' and d['subject']=='X.mode']
        self.assertTrue(added)
        self.assertTrue(any(d['after_value']=='old' for d in added))
    def test_truth_delta_carries_lineage_and_blast_radius(self):
        self._scenario(); report=self.twin.generalized_truth_delta('p1')
        self.assertEqual(['p1'], report['proof_chain'])
        self.assertTrue(report['normalization_decision_ids'])
        self.assertEqual(['Y'], report['blast_radius'])
    def test_minimal_causal_certificate_is_deterministic_and_bound_to_deltas(self):
        self._scenario(); a=self.twin.generalized_truth_delta('p1'); b=self.twin.generalized_truth_delta('p1')
        self.assertEqual(a['certificate']['digest'], b['certificate']['digest'])
        self.assertEqual(a['certificate']['truth_delta_count'], len(a['truth_deltas']))
        self.assertEqual('janus-minimal-causal-proof-certificate-v1', a['certificate']['kind'])
    def test_truth_delta_unknown_proof_fails_closed(self):
        with self.assertRaises(KeyError): self.twin.generalized_truth_delta('missing')

class JanusRun012Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.twin=JanusTwin(self.root/'janus12.db')
    def tearDown(self): self.twin.close(); self.tmp.cleanup()
    def _scenario(self):
        self.twin.add_component('X','owner'); self.twin.add_component('Y','consumer'); self.twin.add_dependency('Y','X')
        self.twin.add_fact({'subject':'X.mode','predicate':'state','value':'old','valid_from':'2026-01-01T00:00:00Z','known_at':'2026-01-01T00:00:00Z','source':'s','authority':'owner'})
        self.twin.add_fact({'subject':'X.mode','predicate':'state','value':'new','valid_from':'2026-01-10T00:00:00Z','known_at':'2026-01-10T00:00:00Z','source':'s','authority':'owner'})
        p=self.twin.temporal_normalization_proposals()[0]
        h=self.twin.add_proof_bundle({'change_id':'p1','status':'proved','claim':'normalization proof'}); ref=f'proof:p1:{h}'
        self.twin.record_normalization_decision(p,'approved','owner',[ref],'2026-01-20T00:00:00Z')
        self.twin.record_proof_lifecycle_event('p1','revoked','2026-01-25T00:00:00Z','owner','withdrawn')
    def test_causal_evidence_bundle_is_content_addressed_and_verifiable(self):
        self._scenario(); bundle=self.twin.build_causal_evidence_bundle('p1')
        self.assertEqual('janus-causal-evidence-bundle-v1', bundle['format'])
        self.assertTrue(bundle['chunks']); self.assertTrue(self.twin.verify_causal_evidence_bundle(bundle)['valid'])
    def test_causal_evidence_bundle_tamper_fails_verification(self):
        self._scenario(); bundle=self.twin.build_causal_evidence_bundle('p1')
        first=next(iter(bundle['chunks'])); bundle['chunks'][first]['payload']['tampered']=True
        self.assertFalse(self.twin.verify_causal_evidence_bundle(bundle)['valid'])
    def test_receiver_reproduces_minimal_certificate_from_bundle(self):
        self._scenario(); bundle=self.twin.build_causal_evidence_bundle('p1')
        receiver=JanusTwin(self.root/'receiver.db')
        try:
            result=receiver.import_causal_evidence_bundle(bundle)
            self.assertTrue(result['valid'])
            self.assertEqual(bundle['certificate']['digest'], receiver.generalized_truth_delta('p1')['certificate']['digest'])
        finally: receiver.close()
    def test_bundle_excludes_unrelated_evidence(self):
        self._scenario(); self.twin.add_proof_bundle({'change_id':'unrelated','status':'proved','claim':'other'})
        bundle=self.twin.build_causal_evidence_bundle('p1')
        payloads=[c['payload'] for c in bundle['chunks'].values()]
        self.assertFalse(any(p.get('change_id')=='unrelated' for p in payloads if isinstance(p,dict)))

class JanusRun013Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.twin=JanusTwin(self.root/'janus13.db')
    def tearDown(self): self.twin.close(); self.tmp.cleanup()
    def _scenario(self):
        self.twin.add_component('X','owner'); self.twin.add_component('Y','consumer'); self.twin.add_dependency('Y','X')
        self.twin.add_fact({'subject':'X.mode','predicate':'state','value':'old','valid_from':'2026-01-01T00:00:00Z','known_at':'2026-01-01T00:00:00Z','source':'s','authority':'owner'})
        self.twin.add_fact({'subject':'X.mode','predicate':'state','value':'new','valid_from':'2026-01-10T00:00:00Z','known_at':'2026-01-10T00:00:00Z','source':'s','authority':'owner'})
        p=self.twin.temporal_normalization_proposals()[0]
        h=self.twin.add_proof_bundle({'change_id':'p1','status':'proved','claim':'normalization proof'}); ref=f'proof:p1:{h}'
        self.twin.record_normalization_decision(p,'approved','owner',[ref],'2026-01-20T00:00:00Z')
        self.twin.record_proof_lifecycle_event('p1','revoked','2026-01-25T00:00:00Z','owner','withdrawn')
    def test_merkle_inclusion_proofs_verify_every_chunk(self):
        self._scenario(); b=self.twin.build_causal_evidence_bundle('p1')
        m=self.twin.build_merkle_evidence_manifest(b)
        self.assertEqual('janus-merkle-evidence-manifest-v1',m['format'])
        for h in m['leaves']:
            self.assertTrue(self.twin.verify_merkle_inclusion(h,m['proofs'][h],m['root_digest']))
    def test_merkle_proof_tamper_fails(self):
        self._scenario(); b=self.twin.build_causal_evidence_bundle('p1'); m=self.twin.build_merkle_evidence_manifest(b)
        h=m['leaves'][0]; p=[dict(x) for x in m['proofs'][h]]
        if p: p[0]['hash']='0'*64
        self.assertFalse(self.twin.verify_merkle_inclusion(h,p,m['root_digest']))
    def test_receiver_contract_negotiation_and_missing_chunk_discovery(self):
        self._scenario(); b=self.twin.build_causal_evidence_bundle('p1'); m=self.twin.build_merkle_evidence_manifest(b)
        cap=self.twin.verification_capabilities(); n=self.twin.negotiate_verification_contract(cap,m)
        self.assertTrue(n['compatible']); have=set(m['leaves'][:1]); self.assertEqual(set(m['leaves'][1:]),set(self.twin.missing_evidence_chunks(m,have)))
    def test_incompatible_receiver_fails_closed(self):
        self._scenario(); b=self.twin.build_causal_evidence_bundle('p1'); m=self.twin.build_merkle_evidence_manifest(b)
        bad={'protocol':'janus-verification-contract-v1','bundle_formats':[],'merkle_formats':[],'certificate_kinds':[],'hash_algorithms':['sha256']}
        self.assertFalse(self.twin.negotiate_verification_contract(bad,m)['compatible'])

class JanusRun014Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.twin=JanusTwin(self.root/'janus14.db')
    def tearDown(self): self.twin.close(); self.tmp.cleanup()
    def _scenario(self):
        self.twin.add_component('X','owner'); self.twin.add_component('Y','consumer'); self.twin.add_dependency('Y','X')
        self.twin.add_fact({'subject':'X.mode','predicate':'state','value':'old','valid_from':'2026-01-01T00:00:00Z','known_at':'2026-01-01T00:00:00Z','source':'s','authority':'owner'})
        self.twin.add_fact({'subject':'X.mode','predicate':'state','value':'new','valid_from':'2026-01-10T00:00:00Z','known_at':'2026-01-10T00:00:00Z','source':'s','authority':'owner'})
        p=self.twin.temporal_normalization_proposals()[0]
        h=self.twin.add_proof_bundle({'change_id':'p1','status':'proved','claim':'normalization proof'}); ref=f'proof:p1:{h}'
        self.twin.record_normalization_decision(p,'approved','owner',[ref],'2026-01-20T00:00:00Z')
        self.twin.record_proof_lifecycle_event('p1','revoked','2026-01-25T00:00:00Z','owner','withdrawn')
        b=self.twin.build_causal_evidence_bundle('p1'); return b,self.twin.build_merkle_evidence_manifest(b)
    def test_signed_root_verifies_under_trusted_authority(self):
        b,m=self._scenario(); private,public=self.twin.generate_signing_keypair()
        env=self.twin.sign_merkle_root(m,'NEXUS',private)
        self.assertTrue(self.twin.verify_signed_merkle_root(env,m,{'NEXUS':public})['valid'])
    def test_signed_root_rejects_tampered_root_or_untrusted_authority(self):
        b,m=self._scenario(); private,public=self.twin.generate_signing_keypair(); env=self.twin.sign_merkle_root(m,'NEXUS',private)
        tampered=dict(m); tampered['root_digest']='0'*64
        self.assertFalse(self.twin.verify_signed_merkle_root(env,tampered,{'NEXUS':public})['valid'])
        self.assertFalse(self.twin.verify_signed_merkle_root(env,m,{'AION':public})['valid'])
    def test_incremental_sync_imports_only_missing_chunks_and_reproduces_certificate(self):
        b,m=self._scenario(); receiver=JanusTwin(self.root/'receiver14.db')
        try:
            have=set(m['leaves'][:2]); partial={h:b['chunks'][h] for h in have}
            missing=receiver.missing_evidence_chunks(m,have)
            receipt=receiver.incremental_sync_causal_evidence(b,m,partial,{h:b['chunks'][h] for h in missing})
            self.assertTrue(receipt['verified']); self.assertEqual(len(missing),receipt['fetched_chunk_count'])
            self.assertEqual(b['certificate']['digest'],receiver.generalized_truth_delta('p1')['certificate']['digest'])
        finally: receiver.close()
    def test_incremental_sync_rejects_bad_chunk_inclusion(self):
        b,m=self._scenario(); receiver=JanusTwin(self.root/'receiver_bad.db')
        try:
            missing=receiver.missing_evidence_chunks(m,set()); fetched={h:dict(b['chunks'][h]) for h in missing}
            first=missing[0]; fetched[first]={'sha256':first,'payload':{'tampered':True}}
            with self.assertRaises(ValueError): receiver.incremental_sync_causal_evidence(b,m,{},fetched)
        finally: receiver.close()

class JanusRun015Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.twin=JanusTwin(self.root/'janus15.db')
        self.twin.add_component('X','owner'); self.twin.add_fact({'subject':'X.mode','predicate':'state','value':'old','valid_from':'2026-01-01T00:00:00Z','known_at':'2026-01-01T00:00:00Z','source':'s','authority':'owner'})
        b=self.twin.build_causal_evidence_bundle if False else None
        # Merkle signing tests need only a structurally valid manifest.
        self.manifest={'format':'janus-merkle-evidence-manifest-v1','root_digest':'a'*64,'hash_algorithm':'sha256'}
    def tearDown(self): self.twin.close(); self.tmp.cleanup()
    def _key(self,authority,key_id,known='2026-01-01T00:00:00Z'):
        private,public=self.twin.generate_signing_keypair(); self.twin.record_signing_key(key_id,authority,public,'2026-01-01T00:00:00Z',known); return private
    def test_threshold_quorum_requires_independent_authorities(self):
        a=self._key('NEXUS','n1'); b=self._key('ARGUS','a1')
        self.twin.record_authorization_policy('JANUS','temporal-proof',['NEXUS','ARGUS'],2,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')
        one=self.twin.verify_authorized_merkle_root_at([self.twin.sign_merkle_root(self.manifest,'NEXUS',a)],self.manifest,'JANUS','temporal-proof','2026-01-10T00:00:00Z','2026-01-10T00:00:00Z')
        self.assertFalse(one['authorized'])
        two=self.twin.verify_authorized_merkle_root_at([self.twin.sign_merkle_root(self.manifest,'NEXUS',a),self.twin.sign_merkle_root(self.manifest,'ARGUS',b)],self.manifest,'JANUS','temporal-proof','2026-01-10T00:00:00Z','2026-01-10T00:00:00Z')
        self.assertTrue(two['authorized']); self.assertEqual(['ARGUS','NEXUS'],two['valid_signers'])
    def test_key_revocation_is_knowledge_time_aware(self):
        a=self._key('NEXUS','n1'); self.twin.record_authorization_policy('JANUS','temporal-proof',['NEXUS'],1,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z'); env=self.twin.sign_merkle_root(self.manifest,'NEXUS',a)
        self.twin.revoke_signing_key('n1','2026-01-20T00:00:00Z','compromised')
        self.assertTrue(self.twin.verify_authorized_merkle_root_at([env],self.manifest,'JANUS','temporal-proof','2026-01-10T00:00:00Z','2026-01-19T00:00:00Z')['authorized'])
        self.assertFalse(self.twin.verify_authorized_merkle_root_at([env],self.manifest,'JANUS','temporal-proof','2026-01-10T00:00:00Z','2026-01-21T00:00:00Z')['authorized'])
    def test_policy_scope_preserves_authority_boundaries(self):
        a=self._key('NEXUS','n1'); self.twin.record_authorization_policy('NEXUS','repo-proof',['NEXUS'],1,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z'); env=self.twin.sign_merkle_root(self.manifest,'NEXUS',a)
        self.assertFalse(self.twin.verify_authorized_merkle_root_at([env],self.manifest,'AION','repo-proof','2026-01-10T00:00:00Z','2026-01-10T00:00:00Z')['authorized'])
    def test_future_known_key_cannot_authorize_past_knowledge_boundary(self):
        a=self._key('NEXUS','n1','2026-01-20T00:00:00Z'); self.twin.record_authorization_policy('JANUS','temporal-proof',['NEXUS'],1,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z'); env=self.twin.sign_merkle_root(self.manifest,'NEXUS',a)
        self.assertFalse(self.twin.verify_authorized_merkle_root_at([env],self.manifest,'JANUS','temporal-proof','2026-01-10T00:00:00Z','2026-01-10T00:00:00Z')['authorized'])

class JanusRun016Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.twin=JanusTwin(self.root/'janus16.db')
        self.manifest={'format':'janus-merkle-evidence-manifest-v1','root_digest':'a'*64,'hash_algorithm':'sha256'}
    def tearDown(self): self.twin.close(); self.tmp.cleanup()
    def _key(self,authority,key_id):
        private,public=self.twin.generate_signing_keypair(); self.twin.record_signing_key(key_id,authority,public,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z'); return private
    def test_policy_revocation_is_knowledge_time_aware(self):
        k=self._key('NEXUS','n1'); pid=self.twin.record_authorization_policy('JANUS','temporal-proof',['NEXUS'],1,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z'); env=self.twin.sign_merkle_root(self.manifest,'NEXUS',k)
        self.twin.revoke_authorization_policy(pid,'2026-01-20T00:00:00Z','NEXUS','superseded')
        self.assertTrue(self.twin.verify_authorized_merkle_root_at([env],self.manifest,'JANUS','temporal-proof','2026-01-10T00:00:00Z','2026-01-19T00:00:00Z')['authorized'])
        self.assertFalse(self.twin.verify_authorized_merkle_root_at([env],self.manifest,'JANUS','temporal-proof','2026-01-10T00:00:00Z','2026-01-21T00:00:00Z')['authorized'])
    def test_authorization_decision_digest_is_deterministic(self):
        k=self._key('NEXUS','n1'); self.twin.record_authorization_policy('JANUS','temporal-proof',['NEXUS'],1,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z'); env=self.twin.sign_merkle_root(self.manifest,'NEXUS',k)
        a=self.twin.verify_authorized_merkle_root_at([env],self.manifest,'JANUS','temporal-proof','2026-01-10T00:00:00Z','2026-01-10T00:00:00Z'); b=self.twin.verify_authorized_merkle_root_at([env],self.manifest,'JANUS','temporal-proof','2026-01-10T00:00:00Z','2026-01-10T00:00:00Z')
        self.assertEqual(a['authorization_decision_digest'],b['authorization_decision_digest'])

def test_run016_authorized_sync_fails_before_mutation_without_quorum(tmp_path):
    twin=JanusTwin(tmp_path/'run16sync.db')
    try:
        private,public=twin.generate_signing_keypair(); twin.record_signing_key('n1','NEXUS',public,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')
        twin.record_authorization_policy('JANUS','temporal-proof',['NEXUS','ARGUS'],2,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')
        manifest={'format':'janus-merkle-evidence-manifest-v1','root_digest':'a'*64,'hash_algorithm':'sha256','leaves':[],'proofs':{}}
        env=twin.sign_merkle_root(manifest,'NEXUS',private)
        with unittest.TestCase().assertRaisesRegex(ValueError,'authorization_failed'):
            twin.authorized_incremental_sync({'format':'janus-causal-evidence-bundle-v1'},manifest,{}, {},[env],'JANUS','temporal-proof','2026-01-10T00:00:00Z','2026-01-10T00:00:00Z')
    finally: twin.close()

class JanusRun017Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.twin=JanusTwin(self.root/'janus17.db')
        self.manifest={'format':'janus-merkle-evidence-manifest-v1','root_digest':'b'*64,'hash_algorithm':'sha256'}
    def tearDown(self): self.twin.close(); self.tmp.cleanup()
    def _key(self,a,k):
        private,public=self.twin.generate_signing_keypair(); self.twin.record_signing_key(k,a,public,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z'); return private,public
    def test_scoped_delegation_can_satisfy_principal_without_expanding_scope(self):
        d,_=self._key('DAEDALUS','d1'); self.twin.record_authorization_policy('JANUS','temporal-proof',['NEXUS'],1,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')
        self.twin.record_authority_delegation('NEXUS','DAEDALUS','JANUS','temporal-proof','2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')
        env=self.twin.sign_merkle_root(self.manifest,'DAEDALUS',d)
        ok=self.twin.verify_authorized_merkle_root_at([env],self.manifest,'JANUS','temporal-proof','2026-01-10T00:00:00Z','2026-01-10T00:00:00Z')
        self.assertTrue(ok['authorized']); self.assertEqual(['NEXUS'],ok['satisfied_principals']); self.assertTrue(ok['delegation_lineage'])
        bad=self.twin.verify_authorized_merkle_root_at([env],self.manifest,'AION','temporal-proof','2026-01-10T00:00:00Z','2026-01-10T00:00:00Z')
        self.assertFalse(bad['authorized'])
    def test_delegation_is_non_transitive_by_default(self):
        a,_=self._key('ATHENA','a1'); self.twin.record_authorization_policy('JANUS','temporal-proof',['NEXUS'],1,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')
        self.twin.record_authority_delegation('NEXUS','DAEDALUS','JANUS','temporal-proof','2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')
        self.twin.record_authority_delegation('DAEDALUS','ATHENA','JANUS','temporal-proof','2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')
        env=self.twin.sign_merkle_root(self.manifest,'ATHENA',a)
        self.assertFalse(self.twin.verify_authorized_merkle_root_at([env],self.manifest,'JANUS','temporal-proof','2026-01-10T00:00:00Z','2026-01-10T00:00:00Z')['authorized'])
    def test_rotation_lineage_is_reported_for_successor_key(self):
        old,oldpub=self._key('NEXUS','n1'); new,newpub=self._key('NEXUS','n2')
        self.twin.record_key_rotation('n1','n2','2026-01-05T00:00:00Z','2026-01-05T00:00:00Z')
        self.twin.record_authorization_policy('JANUS','temporal-proof',['NEXUS'],1,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')
        env=self.twin.sign_merkle_root(self.manifest,'NEXUS',new)
        r=self.twin.verify_authorized_merkle_root_at([env],self.manifest,'JANUS','temporal-proof','2026-01-10T00:00:00Z','2026-01-10T00:00:00Z')
        self.assertTrue(r['authorized']); self.assertEqual([{'predecessor_key_id':'n1','successor_key_id':'n2'}],r['key_rotation_lineage'])

class JanusRun018Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.twin=JanusTwin(self.root/'janus18.db')
        self.manifest={'format':'janus-merkle-evidence-manifest-v1','root_digest':'c'*64,'hash_algorithm':'sha256'}
    def tearDown(self): self.twin.close(); self.tmp.cleanup()
    def _key(self,a,k):
        private,public=self.twin.generate_signing_keypair(); self.twin.record_signing_key(k,a,public,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z'); return private
    def test_delegation_revocation_is_knowledge_time_aware(self):
        d=self._key('DAEDALUS','d1'); self.twin.record_authorization_policy('JANUS','temporal-proof',['NEXUS'],1,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')
        did=self.twin.record_authority_delegation('NEXUS','DAEDALUS','JANUS','temporal-proof','2026-01-01T00:00:00Z','2026-01-01T00:00:00Z'); env=self.twin.sign_merkle_root(self.manifest,'DAEDALUS',d)
        self.twin.revoke_authority_delegation(did,'2026-01-20T00:00:00Z','NEXUS','scope withdrawn')
        self.assertTrue(self.twin.verify_authorized_merkle_root_at([env],self.manifest,'JANUS','temporal-proof','2026-01-10T00:00:00Z','2026-01-19T00:00:00Z')['authorized'])
        self.assertFalse(self.twin.verify_authorized_merkle_root_at([env],self.manifest,'JANUS','temporal-proof','2026-01-10T00:00:00Z','2026-01-21T00:00:00Z')['authorized'])
    def test_rotation_cycle_is_rejected(self):
        self._key('NEXUS','n1'); self._key('NEXUS','n2'); self._key('NEXUS','n3')
        self.twin.record_key_rotation('n1','n2','2026-01-02T00:00:00Z','2026-01-02T00:00:00Z'); self.twin.record_key_rotation('n2','n3','2026-01-03T00:00:00Z','2026-01-03T00:00:00Z')
        with self.assertRaisesRegex(ValueError,'rotation_cycle_forbidden'): self.twin.record_key_rotation('n3','n1','2026-01-04T00:00:00Z','2026-01-04T00:00:00Z')
    def test_complete_rotation_predecessor_chain_is_reported(self):
        self._key('NEXUS','n1'); self._key('NEXUS','n2'); newest=self._key('NEXUS','n3')
        self.twin.record_key_rotation('n1','n2','2026-01-02T00:00:00Z','2026-01-02T00:00:00Z'); self.twin.record_key_rotation('n2','n3','2026-01-03T00:00:00Z','2026-01-03T00:00:00Z')
        self.twin.record_authorization_policy('JANUS','temporal-proof',['NEXUS'],1,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z'); env=self.twin.sign_merkle_root(self.manifest,'NEXUS',newest)
        r=self.twin.verify_authorized_merkle_root_at([env],self.manifest,'JANUS','temporal-proof','2026-01-10T00:00:00Z','2026-01-10T00:00:00Z')
        self.assertEqual([{'predecessor_key_id':'n1','successor_key_id':'n2'},{'predecessor_key_id':'n2','successor_key_id':'n3'}],r['key_rotation_lineage'])

class JanusRun019Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.twin=JanusTwin(self.root/'janus19.db')
        self.manifest={'format':'janus-merkle-evidence-manifest-v1','root_digest':'d'*64,'hash_algorithm':'sha256'}
    def tearDown(self): self.twin.close(); self.tmp.cleanup()
    def _key(self,a,k):
        private,public=self.twin.generate_signing_keypair(); self.twin.record_signing_key(k,a,public,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z'); return private
    def test_trust_lineage_bundle_is_content_addressed_and_selective(self):
        d=self._key('DAEDALUS','d1'); self.twin.record_authorization_policy('JANUS','temporal-proof',['NEXUS'],1,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')
        self.twin.record_authority_delegation('NEXUS','DAEDALUS','JANUS','temporal-proof','2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')
        env=self.twin.sign_merkle_root(self.manifest,'DAEDALUS',d)
        bundle=self.twin.build_trust_lineage_bundle([env],self.manifest,'JANUS','temporal-proof','2026-01-10T00:00:00Z','2026-01-10T00:00:00Z')
        self.assertTrue(self.twin.verify_trust_lineage_bundle(bundle)['valid'])
        self.assertTrue(any(c['payload']['kind']=='authority_delegation' for c in bundle['chunks'].values()))
        m=self.twin.build_trust_lineage_merkle_manifest(bundle); held={m['leaves'][0]}
        self.assertEqual(len(m['leaves'])-1,len(self.twin.missing_trust_lineage_chunks(m,held)))
    def test_tampered_trust_object_fails_closed(self):
        n=self._key('NEXUS','n1'); self.twin.record_authorization_policy('JANUS','temporal-proof',['NEXUS'],1,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z'); env=self.twin.sign_merkle_root(self.manifest,'NEXUS',n)
        b=self.twin.build_trust_lineage_bundle([env],self.manifest,'JANUS','temporal-proof','2026-01-10T00:00:00Z','2026-01-10T00:00:00Z')
        h=next(iter(b['chunks'])); b['chunks'][h]['payload']['authority']='TAMPERED'
        self.assertFalse(self.twin.verify_trust_lineage_bundle(b)['valid'])
    def test_receiver_replays_authorization_from_trust_bundle(self):
        old=self._key('NEXUS','n1'); new=self._key('NEXUS','n2'); self.twin.record_key_rotation('n1','n2','2026-01-05T00:00:00Z','2026-01-05T00:00:00Z')
        self.twin.record_authorization_policy('JANUS','temporal-proof',['NEXUS'],1,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z'); env=self.twin.sign_merkle_root(self.manifest,'NEXUS',new)
        sender=self.twin.verify_authorized_merkle_root_at([env],self.manifest,'JANUS','temporal-proof','2026-01-10T00:00:00Z','2026-01-10T00:00:00Z')
        bundle=self.twin.build_trust_lineage_bundle([env],self.manifest,'JANUS','temporal-proof','2026-01-10T00:00:00Z','2026-01-10T00:00:00Z')
        receiver=JanusTwin(self.root/'receiver.db')
        try:
            replay=receiver.import_and_replay_trust_lineage(bundle,[env],self.manifest)
            self.assertTrue(replay['authorized']); self.assertEqual(sender['authorization_decision_digest'],replay['authorization_decision_digest'])
        finally: receiver.close()

class JanusRun020Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.sender=JanusTwin(self.root/'sender20.db')
    def tearDown(self): self.sender.close(); self.tmp.cleanup()
    def _scenario(self):
        t=self.sender
        t.add_component('X','owner'); t.add_component('Y','consumer'); t.add_dependency('Y','X')
        t.add_fact({'subject':'X.mode','predicate':'state','value':'old','valid_from':'2026-01-01T00:00:00Z','known_at':'2026-01-01T00:00:00Z','source':'s','authority':'owner'})
        t.add_fact({'subject':'X.mode','predicate':'state','value':'new','valid_from':'2026-01-10T00:00:00Z','known_at':'2026-01-10T00:00:00Z','source':'s','authority':'owner'})
        p=t.temporal_normalization_proposals()[0]; h=t.add_proof_bundle({'change_id':'p1','status':'proved','claim':'normalization proof'}); ref=f'proof:p1:{h}'
        t.record_normalization_decision(p,'approved','owner',[ref],'2026-01-20T00:00:00Z'); t.record_proof_lifecycle_event('p1','revoked','2026-01-25T00:00:00Z','owner','withdrawn')
        causal=t.build_causal_evidence_bundle('p1'); cm=t.build_merkle_evidence_manifest(causal)
        private,public=t.generate_signing_keypair(); t.record_signing_key('n1','NEXUS',public,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')
        t.record_authorization_policy('JANUS','temporal-proof',['NEXUS'],1,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')
        env=t.sign_merkle_root(cm,'NEXUS',private)
        trust=t.build_trust_lineage_bundle([env],cm,'JANUS','temporal-proof','2026-01-10T00:00:00Z','2026-01-10T00:00:00Z')
        return causal,cm,env,trust
    def test_atomic_joint_sync_replays_trust_and_causal_proofs(self):
        causal,cm,env,trust=self._scenario(); r=JanusTwin(self.root/'receiver20.db')
        try:
            receipt=r.atomic_joint_sync(causal,cm,{},dict(causal['chunks']),trust,[env])
            self.assertTrue(receipt['verified']); self.assertEqual('janus-joint-proof-receipt-v1',receipt['format'])
            self.assertEqual(causal['certificate']['digest'],receipt['causal_certificate_digest'])
            self.assertEqual(trust['authorization_decision_digest'],receipt['authorization_decision_digest'])
            self.assertEqual('completed',r.sync_session(receipt['session_id'])['status'])
        finally: r.close()
    def test_atomic_joint_sync_failure_does_not_promote_domain_state(self):
        causal,cm,env,trust=self._scenario(); r=JanusTwin(self.root/'receiver20bad.db')
        try:
            bad=dict(causal['chunks']); h=next(iter(bad)); bad[h]=dict(bad[h]); bad[h]['payload']=dict(bad[h]['payload']); bad[h]['payload']['tampered']=True
            before=r.state_digest()
            with self.assertRaises(ValueError): r.atomic_joint_sync(causal,cm,{},bad,trust,[env])
            self.assertEqual(before,r.state_digest())
        finally: r.close()
    def test_sync_session_is_deterministic_and_resumable(self):
        causal,cm,env,trust=self._scenario(); r=JanusTwin(self.root/'receiver20session.db')
        try:
            sid1=r.begin_sync_session(causal,cm,trust); sid2=r.begin_sync_session(causal,cm,trust)
            self.assertEqual(sid1,sid2); s=r.sync_session(sid1); self.assertEqual('staged',s['status']); self.assertEqual(cm['root_digest'],s['causal_root'])
        finally: r.close()

class JanusRun021Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.sender=JanusTwin(self.root/'sender21.db')
    def tearDown(self): self.sender.close(); self.tmp.cleanup()
    def _scenario(self):
        t=self.sender
        t.add_component('X','owner'); t.add_component('Y','consumer'); t.add_dependency('Y','X')
        t.add_fact({'subject':'X.mode','predicate':'state','value':'old','valid_from':'2026-01-01T00:00:00Z','known_at':'2026-01-01T00:00:00Z','source':'s','authority':'owner'})
        t.add_fact({'subject':'X.mode','predicate':'state','value':'new','valid_from':'2026-01-10T00:00:00Z','known_at':'2026-01-10T00:00:00Z','source':'s','authority':'owner'})
        p=t.temporal_normalization_proposals()[0]; h=t.add_proof_bundle({'change_id':'p21','status':'proved','claim':'normalization proof'}); ref=f'proof:p21:{h}'
        t.record_normalization_decision(p,'approved','owner',[ref],'2026-01-20T00:00:00Z')
        causal=t.build_causal_evidence_bundle('p21'); cm=t.build_merkle_evidence_manifest(causal)
        private,public=t.generate_signing_keypair(); t.record_signing_key('n21','NEXUS',public,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')
        t.record_authorization_policy('JANUS','temporal-proof',['NEXUS'],1,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')
        env=t.sign_merkle_root(cm,'NEXUS',private); trust=t.build_trust_lineage_bundle([env],cm,'JANUS','temporal-proof','2026-01-10T00:00:00Z','2026-01-10T00:00:00Z')
        return causal,cm,env,trust
    def test_chunk_inventory_survives_restart_and_is_idempotent(self):
        causal,cm,env,trust=self._scenario(); path=self.root/'restart.db'; r=JanusTwin(path)
        sid=r.begin_sync_session(causal,cm,trust); half={h:causal['chunks'][h] for h in cm['leaves'][:2]}; a=r.checkpoint_sync_chunks(sid,'causal',cm['leaves'],half); r.close()
        r=JanusTwin(path)
        try:
            b=r.sync_chunk_inventory(sid,'causal'); self.assertEqual(a['verified'],b['verified']); self.assertGreater(len(b['missing']),0)
            c=r.checkpoint_sync_chunks(sid,'causal',cm['leaves'],half); self.assertEqual(b,c)
        finally: r.close()
    def test_concurrent_receiver_change_blocks_stale_promotion(self):
        causal,cm,env,trust=self._scenario(); r=JanusTwin(self.root/'concurrent.db')
        try:
            r.begin_sync_session(causal,cm,trust); r.add_component('CONCURRENT','other-owner'); before=r.state_digest()
            with self.assertRaisesRegex(ValueError,'concurrent_receiver_state_changed'):
                r.atomic_joint_sync(causal,cm,{},dict(causal['chunks']),trust,[env])
            self.assertEqual(before,r.state_digest())
        finally: r.close()
    def test_joint_receipt_is_signed_and_verifiable(self):
        causal,cm,env,trust=self._scenario(); r=JanusTwin(self.root/'signed.db'); priv,pub=r.generate_signing_keypair()
        try:
            receipt=r.atomic_joint_sync(causal,cm,{},dict(causal['chunks']),trust,[env],receipt_signer=('JANUS-AUDIT',priv))
            self.assertTrue(r.verify_joint_receipt_signature(receipt,{'JANUS-AUDIT':pub})); self.assertIsNone(receipt['previous_receipt_digest'])
            tampered=dict(receipt); tampered['receipt_digest']='0'*64; self.assertFalse(r.verify_joint_receipt_signature(tampered,{'JANUS-AUDIT':pub}))
        finally: r.close()
    def test_receipt_binds_prior_receipt_hash(self):
        causal,cm,env,trust=self._scenario(); r=JanusTwin(self.root/'chain.db')
        try:
            prior='a'*64; r.conn.execute("INSERT INTO joint_receipts(receipt_digest,session_id,receipt_json,created_at) VALUES (?,?,?,?)",(prior,'prior','{}','2026-01-01T00:00:00Z')); r.conn.commit()
            receipt=r.atomic_joint_sync(causal,cm,{},dict(causal['chunks']),trust,[env]); self.assertEqual(prior,receipt['previous_receipt_digest'])
        finally: r.close()

class Run022FencingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def _scenario(self):
        helper=JanusRun021Tests(); helper.root=self.root; helper.sender=JanusTwin(self.root/'sender22.db')
        try: return helper._scenario()
        finally: helper.sender.close()
    def test_newer_fence_rejects_stale_writer(self):
        causal,cm,env,trust=self._scenario(); r=JanusTwin(self.root/'fence.db')
        try:
            sid=r.begin_sync_session(causal,cm,trust); first=r.acquire_promotion_fence(sid)
            newer=r.acquire_promotion_fence('competing-session')
            self.assertGreater(newer['fence_epoch'],first['fence_epoch'])
            with self.assertRaisesRegex(ValueError,'stale_fencing_epoch'):
                r.assert_promotion_guard(sid)
        finally: r.close()
    def test_receipt_head_cas_detects_fork(self):
        causal,cm,env,trust=self._scenario(); r=JanusTwin(self.root/'fork.db')
        try:
            sid=r.begin_sync_session(causal,cm,trust); r.acquire_promotion_fence(sid)
            r.conn.execute("INSERT INTO joint_receipts(receipt_digest,session_id,receipt_json,created_at) VALUES (?,?,?,?)",('b'*64,'other','{}','2026-01-02T00:00:00Z')); r.conn.commit()
            with self.assertRaisesRegex(ValueError,'receipt_head_changed'):
                r.assert_promotion_guard(sid)
        finally: r.close()
    def test_crash_before_promotion_preserves_truth_and_resume_succeeds(self):
        causal,cm,env,trust=self._scenario(); r=JanusTwin(self.root/'crash.db'); before=r.state_digest()
        try:
            with self.assertRaisesRegex(RuntimeError,'injected_crash_before_promotion'):
                r.atomic_joint_sync(causal,cm,{},dict(causal['chunks']),trust,[env],crash_at='before_promotion')
            self.assertEqual(before,r.state_digest())
            inv=r.sync_chunk_inventory(r.begin_sync_session(causal,cm,trust),'causal'); self.assertEqual([],inv['missing'])
            receipt=r.atomic_joint_sync(causal,cm,{},dict(causal['chunks']),trust,[env]); self.assertTrue(receipt['verified'])
        finally: r.close()
    def test_promotion_guard_is_bound_into_receipt(self):
        causal,cm,env,trust=self._scenario(); r=JanusTwin(self.root/'guardreceipt.db')
        try:
            receipt=r.atomic_joint_sync(causal,cm,{},dict(causal['chunks']),trust,[env])
            self.assertGreater(receipt['fence_epoch'],0); self.assertIn('expected_receipt_head',receipt)
        finally: r.close()

class Run023LeaseCrashTests(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def _scenario(self):
        helper=JanusRun021Tests(); helper.root=self.root; helper.sender=JanusTwin(self.root/'sender23.db')
        try: return helper._scenario()
        finally: helper.sender.close()
    def test_lease_renewal_preserves_epoch_and_owner(self):
        causal,cm,env,trust=self._scenario(); r=JanusTwin(self.root/'lease.db')
        try:
            sid=r.begin_sync_session(causal,cm,trust); a=r.acquire_promotion_lease(sid,'worker-a',60); b=r.renew_promotion_lease(sid,'worker-a',120)
            self.assertEqual(a['fence_epoch'],b['fence_epoch']); self.assertEqual('worker-a',b['owner_id']); self.assertGreaterEqual(b['expires_at'],a['expires_at'])
        finally: r.close()
    def test_takeover_invalidates_prior_lease_epoch(self):
        causal,cm,env,trust=self._scenario(); r=JanusTwin(self.root/'takeover.db')
        try:
            sid=r.begin_sync_session(causal,cm,trust); a=r.acquire_promotion_lease(sid,'worker-a',60)
            # Force expiry to exercise deterministic takeover without sleeping.
            r.conn.execute("UPDATE promotion_leases SET expires_at='2000-01-01T00:00:00Z' WHERE session_id=?",(sid,)); r.conn.commit()
            b=r.acquire_promotion_lease(sid,'worker-b',60); self.assertGreater(b['fence_epoch'],a['fence_epoch'])
            with self.assertRaisesRegex(ValueError,'lease_owner_mismatch'): r.assert_promotion_lease(sid,'worker-a')
        finally: r.close()
    def test_receipt_fork_emits_auditable_evidence(self):
        causal,cm,env,trust=self._scenario(); r=JanusTwin(self.root/'forkproof.db')
        try:
            sid=r.begin_sync_session(causal,cm,trust); r.acquire_promotion_fence(sid)
            r.conn.execute("INSERT INTO joint_receipts(receipt_digest,session_id,receipt_json,created_at) VALUES (?,?,?,?)",('c'*64,'racer','{}','2026-01-02T00:00:00Z')); r.conn.commit()
            with self.assertRaisesRegex(ValueError,'receipt_head_changed'): r.assert_promotion_guard(sid)
            ev=r.receipt_fork_evidence(sid); self.assertEqual(1,len(ev)); self.assertEqual('c'*64,ev[0]['observed_head']); self.assertEqual('janus-receipt-fork-evidence-v1',ev[0]['format'])
        finally: r.close()
    def test_atomic_receipt_binds_temporal_lease(self):
        causal,cm,env,trust=self._scenario(); r=JanusTwin(self.root/'atomiclease.db')
        try:
            receipt=r.atomic_joint_sync(causal,cm,{},dict(causal['chunks']),trust,[env]); self.assertEqual('atomic:'+receipt['session_id'],receipt['lease_owner']); self.assertIn('lease_expires_at',receipt)
        finally: r.close()

class Run024PromotionJournalTests(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def _scenario(self):
        helper=JanusRun021Tests(); helper.root=self.root; helper.sender=JanusTwin(self.root/'sender24.db')
        try: return helper._scenario()
        finally: helper.sender.close()
    def test_prepared_crash_aborts_without_domain_promotion_and_is_recoverable(self):
        causal,cm,env,trust=self._scenario(); r=JanusTwin(self.root/'journal.db'); before=r.state_digest()
        try:
            with self.assertRaisesRegex(RuntimeError,'injected_crash_after_prepare'): r.atomic_joint_sync(causal,cm,{},dict(causal['chunks']),trust,[env],crash_at='after_prepare')
            sid=r.begin_sync_session(causal,cm,trust); self.assertEqual(before,r.state_digest()); self.assertEqual('aborted',r.promotion_journal(sid)['status'])
            cert=r.recover_promotion(sid); self.assertEqual('aborted',cert['outcome']); self.assertEqual('janus-promotion-recovery-certificate-v1',cert['format'])
        finally: r.close()
    def test_successful_promotion_journal_commits_and_recovery_is_idempotent(self):
        causal,cm,env,trust=self._scenario(); r=JanusTwin(self.root/'commitjournal.db')
        try:
            receipt=r.atomic_joint_sync(causal,cm,{},dict(causal['chunks']),trust,[env]); sid=receipt['session_id']; self.assertEqual('committed',r.promotion_journal(sid)['status'])
            a=r.recover_promotion(sid); b=r.recover_promotion(sid); self.assertEqual(a['certificate_digest'],b['certificate_digest']); self.assertEqual(receipt['receipt_digest'],a['receipt_digest'])
        finally: r.close()
    def test_clock_skew_policy_bounds_lease_expiration(self):
        causal,cm,env,trust=self._scenario(); r=JanusTwin(self.root/'skew.db')
        try:
            sid=r.begin_sync_session(causal,cm,trust); lease=r.acquire_promotion_lease(sid,'worker',60); r.set_clock_skew_policy(5)
            exp=datetime.fromisoformat(lease['expires_at'].replace('Z','+00:00'))
            within=(exp+timedelta(seconds=4)).isoformat().replace('+00:00','Z'); outside=(exp+timedelta(seconds=6)).isoformat().replace('+00:00','Z')
            self.assertFalse(r._lease_expired_with_skew(lease['expires_at'],within)); self.assertTrue(r._lease_expired_with_skew(lease['expires_at'],outside))
        finally: r.close()
    def test_recovery_certificate_is_content_addressed(self):
        causal,cm,env,trust=self._scenario(); r=JanusTwin(self.root/'cert.db')
        try:
            receipt=r.atomic_joint_sync(causal,cm,{},dict(causal['chunks']),trust,[env]); cert=r.recover_promotion(receipt['session_id']); core={k:v for k,v in cert.items() if k!='certificate_digest'}
            self.assertEqual(cert['certificate_digest'],sha256_bytes(stable_json(core).encode()))
        finally: r.close()

class Run025ProcessCrashTests(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def _run_hard_crash(self, boundary: str, receiver_name: str):
        import os, subprocess, sys
        receiver=self.root/receiver_name
        script=r'''
import sys
from pathlib import Path
sys.path.insert(0, "tests")
from test_janus import JanusRun021Tests
from janus_infinity.core import JanusTwin
root=Path(sys.argv[1]); receiver=Path(sys.argv[2]); boundary=sys.argv[3]
helper=JanusRun021Tests(); helper.root=root; helper.sender=JanusTwin(root/("sender-hard-"+boundary+".db"))
try:
    causal,cm,env,trust=helper._scenario()
finally:
    helper.sender.close()
r=JanusTwin(receiver)
r.atomic_joint_sync(causal,cm,{},dict(causal['chunks']),trust,[env],hard_crash_at=boundary)
'''
        env=dict(os.environ); env['PYTHONPATH']='src'
        p=subprocess.run([sys.executable,'-c',script,str(self.root),str(receiver),boundary],cwd=Path(__file__).parents[1],env=env)
        self.assertEqual(86,p.returncode)
        return receiver
    def test_sigkill_equivalent_after_prepare_recovers_aborted_without_promotion(self):
        path=self._run_hard_crash('after_prepare','hard-prepare.db'); r=JanusTwin(path)
        try:
            self.assertEqual('ok',r.conn.execute('PRAGMA integrity_check').fetchone()[0])
            row=r.conn.execute('SELECT session_id,status FROM promotion_journal').fetchone(); self.assertIsNotNone(row); self.assertEqual('prepared',row['status'])
            self.assertEqual(0,r.conn.execute('SELECT COUNT(*) FROM joint_receipts').fetchone()[0])
            cert=r.recover_promotion(row['session_id']); self.assertEqual('aborted',cert['outcome'])
        finally: r.close()
    def test_sigkill_equivalent_after_database_promotion_recovers_committed(self):
        path=self._run_hard_crash('after_promotion_backup','hard-promoted.db'); r=JanusTwin(path)
        try:
            self.assertEqual('ok',r.conn.execute('PRAGMA integrity_check').fetchone()[0])
            row=r.conn.execute('SELECT session_id,status FROM promotion_journal').fetchone(); self.assertIsNotNone(row); self.assertEqual('prepared',row['status'])
            self.assertEqual(1,r.conn.execute('SELECT COUNT(*) FROM joint_receipts').fetchone()[0])
            cert=r.recover_promotion(row['session_id']); self.assertEqual('committed',cert['outcome'])
            again=r.recover_promotion(row['session_id']); self.assertEqual(cert['certificate_digest'],again['certificate_digest'])
        finally: r.close()

class Run025RecoverySweepTests(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def test_pending_promotion_recovery_sweep_is_idempotent(self):
        r=JanusTwin(self.root/'sweep.db')
        try:
            r.conn.execute("INSERT INTO sync_sessions(session_id,change_id,causal_root,trust_bundle_digest,authorization_decision_digest,receiver_state_digest,status,created_at,updated_at) VALUES (?,?,?,?,?,?,'staged',?,?)",('s1','change','c','t','a',r.state_digest(),'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z'))
            r.conn.execute("INSERT INTO promotion_journal(session_id,fence_epoch,owner_id,receiver_state_digest,status,prepared_at) VALUES (?,?,?,?, 'prepared',?)",('s1',1,'worker',r.state_digest(),'2026-01-01T00:00:00Z')); r.conn.commit()
            first=r.recover_pending_promotions(); second=r.recover_pending_promotions()
            self.assertEqual('aborted',first[0]['outcome']); self.assertEqual([],second)
        finally: r.close()

class Run026StorageFaultTests(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def _scenario(self):
        helper=JanusRun021Tests(); helper.root=self.root; helper.sender=JanusTwin(self.root/'sender26.db')
        try: return helper._scenario()
        finally: helper.sender.close()
    def test_corrupt_stage_is_quarantined_and_never_promoted(self):
        causal,cm,env,trust=self._scenario(); r=JanusTwin(self.root/'corrupt-receiver.db'); before=r.state_digest()
        try:
            with self.assertRaisesRegex(ValueError,'storage_stage_integrity_failed'):
                r.atomic_joint_sync(causal,cm,{},dict(causal['chunks']),trust,[env],storage_fault_at='corrupt_stage_before_promotion')
            self.assertEqual(before,r.state_digest()); self.assertEqual(0,r.conn.execute('SELECT COUNT(*) FROM joint_receipts').fetchone()[0])
            q=r.storage_quarantine(); self.assertEqual(1,len(q)); self.assertEqual('corrupt_stage_before_promotion',q[0]['fault_class']); self.assertTrue(Path(q[0]['quarantine_path']).exists())
        finally: r.close()
    def test_truncated_stage_is_quarantined_and_authoritative_db_stays_valid(self):
        causal,cm,env,trust=self._scenario(); r=JanusTwin(self.root/'truncate-receiver.db'); before=r.state_digest()
        try:
            with self.assertRaisesRegex(ValueError,'storage_stage_integrity_failed'):
                r.atomic_joint_sync(causal,cm,{},dict(causal['chunks']),trust,[env],storage_fault_at='truncate_stage_before_promotion')
            self.assertEqual(before,r.state_digest()); self.assertEqual('ok',r.conn.execute('PRAGMA integrity_check').fetchone()[0]); self.assertEqual(1,len(r.storage_quarantine()))
        finally: r.close()
    def test_injected_enospc_aborts_without_receipt_or_truth_divergence(self):
        causal,cm,env,trust=self._scenario(); r=JanusTwin(self.root/'enospc-receiver.db'); before=r.state_digest()
        try:
            with self.assertRaisesRegex(OSError,'ENOSPC'):
                r.atomic_joint_sync(causal,cm,{},dict(causal['chunks']),trust,[env],storage_fault_at='enospc_before_promotion')
            self.assertEqual(before,r.state_digest()); self.assertEqual(0,r.conn.execute('SELECT COUNT(*) FROM joint_receipts').fetchone()[0])
            sid=r.begin_sync_session(causal,cm,trust); self.assertEqual('aborted',r.promotion_journal(sid)['status'])
        finally: r.close()

def _reap_crash_child(proc, db_pid):
    """Hard-kill a hard_wait crash-injection child still alive (e.g. an assertion failed before the kill) so it can never leak."""
    import os, signal, subprocess
    if proc.stdout and not proc.stdout.closed: proc.stdout.close()
    if proc.poll() is not None: return
    try: os.kill(db_pid if db_pid is not None else proc.pid,getattr(signal,'SIGKILL',signal.SIGTERM))
    except OSError: pass
    try: proc.wait(timeout=5)
    except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=5)

def _read_child_pid(proc, timeout=30):
    """Read the crash-injection child's first stdout line (its PID) without blocking forever if it stalls."""
    import threading
    box=[]
    t=threading.Thread(target=lambda: box.append(proc.stdout.readline()),daemon=True); t.start(); t.join(timeout)
    if not box or not box[0].strip():
        raise AssertionError(f"crash-injection child did not report its pid within {timeout}s")
    proc.stdout.close()
    return int(box[0])

class Run027ExternalKillAuditTests(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def _scenario(self):
        helper=JanusRun021Tests(); helper.root=self.root; helper.sender=JanusTwin(self.root/'sender27.db')
        try: return helper._scenario()
        finally: helper.sender.close()
    def test_external_sigkill_after_prepare_recovers_aborted(self):
        import os, signal, subprocess, sys, time
        causal,cm,env,trust=self._scenario(); payload=self.root/'payload.json'; receiver=self.root/'sigkill.db'
        payload.write_text(json.dumps({'causal':causal,'cm':cm,'env':env,'trust':trust}))
        code="""import json,os,sys\nprint(os.getpid(),flush=True)\nfrom janus_infinity.core import JanusTwin\np=json.load(open(sys.argv[2])); r=JanusTwin(sys.argv[1]); r.atomic_joint_sync(p['causal'],p['cm'],{},dict(p['causal']['chunks']),p['trust'],[p['env']],hard_wait_at='after_prepare')\n"""
        proc=subprocess.Popen([sys.executable,'-c',code,str(receiver),str(payload)],env={**os.environ,'PYTHONPATH':str(Path(__file__).parents[1]/'src')},stdout=subprocess.PIPE,text=True)
        db_pid=None
        try:
            db_pid=_read_child_pid(proc)  # PID of the interpreter holding the DB (a Windows venv proc.pid is a launcher stub)
            sid=None
            for _ in range(100):
                time.sleep(.03)
                if receiver.exists():
                    try:
                        probe=JanusTwin(receiver); rows=probe.conn.execute("SELECT session_id FROM promotion_journal WHERE status='prepared'").fetchall(); probe.close()
                        if rows: sid=rows[0][0]; break
                    except Exception: pass
            self.assertIsNotNone(sid)
            # Windows has no SIGKILL: os.kill() there is an unconditional external TerminateProcess (exit code = sig) of the DB-holding
            # interpreter; the venv launcher waits for it and propagates that exit code, so wait() returns only once the DB holder is gone.
            if sys.platform=='win32': os.kill(db_pid,signal.SIGTERM); proc.wait(timeout=5); self.assertEqual(int(signal.SIGTERM),proc.returncode)
            else: os.kill(proc.pid,signal.SIGKILL); proc.wait(timeout=5); self.assertLess(proc.returncode,0)
        finally: _reap_crash_child(proc,db_pid)
        r=JanusTwin(receiver)
        try:
            self.assertEqual('ok',r.conn.execute('PRAGMA integrity_check').fetchone()[0]); cert=r.recover_promotion(sid); self.assertEqual('aborted',cert['outcome']); self.assertEqual(0,r.conn.execute('SELECT COUNT(*) FROM joint_receipts').fetchone()[0])
        finally: r.close()
    def test_invalid_wal_header_is_classified_as_corrupt(self):
        db=self.root/'wal.db'; r=JanusTwin(db); r.close(); wal=Path(str(db)+'-wal'); wal.write_bytes(b'NOT-A-SQLITE-WAL'+b'X'*64)
        report=JanusTwin.classify_storage_artifacts(db)
        self.assertEqual('wal_corrupt_header',report['wal']['classification']); self.assertEqual('ok',report['main_db']['integrity'])
    def test_storage_fault_audit_is_signed_and_hash_chained(self):
        r=JanusTwin(self.root/'audit.db'); stage=self.root/'damaged.stage'; stage.write_bytes(b'bad-stage')
        try:
            ev1=r._quarantine_stage('s1',stage,'corrupt_stage','database_error'); ev2=r._quarantine_stage('s2',stage,'truncate_stage','database_error')
            priv,pub=r.generate_signing_keypair(); a1=r.sign_storage_fault_evidence(ev1['evidence_digest'],'JANUS-AUDIT',priv); a2=r.sign_storage_fault_evidence(ev2['evidence_digest'],'JANUS-AUDIT',priv)
            self.assertIsNone(a1['previous_audit_digest']); self.assertEqual(a1['audit_digest'],a2['previous_audit_digest']); self.assertTrue(r.verify_storage_fault_audit(a2,{'JANUS-AUDIT':pub}))
            tampered=dict(a2); tampered['fault_evidence_digest']='0'*64; self.assertFalse(r.verify_storage_fault_audit(tampered,{'JANUS-AUDIT':pub}))
        finally: r.close()

class Run028WalRecoveryCrossLinkTests(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def _scenario(self):
        helper=JanusRun021Tests(); helper.root=self.root; helper.sender=JanusTwin(self.root/'sender28.db')
        try: return helper._scenario()
        finally: helper.sender.close()
    def _real_wal_bytes(self, db: Path) -> bytes:
        import sqlite3
        con=sqlite3.connect(db)
        try:
            con.execute('PRAGMA journal_mode=WAL')
            con.execute('PRAGMA wal_autocheckpoint=0')
            con.execute('CREATE TABLE wal_probe(x INTEGER)')
            con.commit()
            con.execute('INSERT INTO wal_probe VALUES (1)')
            con.commit()
            wal=Path(str(db)+'-wal')
            self.assertTrue(wal.exists())
            return wal.read_bytes()
        finally:
            con.close()
    def test_wal_frames_and_rolling_checksums_are_fully_validated(self):
        db=self.root/'wal-full.db'; data=self._real_wal_bytes(db); wal=Path(str(db)+'-wal'); wal.write_bytes(data)
        good=JanusTwin.classify_storage_artifacts(db)
        self.assertEqual('wal_valid',good['wal']['classification'])
        self.assertTrue(good['wal']['header_checksum_valid'])
        self.assertGreater(good['wal']['frame_count'],0)
        self.assertEqual(good['wal']['frame_count'],good['wal']['valid_frame_count'])
        self.assertIsNone(good['wal']['first_invalid_frame'])
        bad_header=bytearray(data); bad_header[24] ^= 0x01; wal.write_bytes(bytes(bad_header))
        h=JanusTwin.classify_storage_artifacts(db)
        self.assertEqual('wal_corrupt_header_checksum',h['wal']['classification'])
        bad_salt=bytearray(data); bad_salt[40] ^= 0x01; wal.write_bytes(bytes(bad_salt))
        s=JanusTwin.classify_storage_artifacts(db)
        self.assertEqual('wal_corrupt_frame_salt',s['wal']['classification'])
        self.assertEqual(1,s['wal']['salt_mismatch_frame'])
        damaged=bytearray(data); damaged[-1] ^= 0x01; wal.write_bytes(bytes(damaged))
        bad=JanusTwin.classify_storage_artifacts(db)
        self.assertEqual('wal_corrupt_frame_checksum',bad['wal']['classification'])
        self.assertIsNotNone(bad['wal']['first_invalid_frame'])
        self.assertEqual(bad['wal']['first_invalid_frame'],bad['wal']['checksum_mismatch_frame'])
    def test_external_sigkill_after_authoritative_backup_recovers_committed(self):
        import os, signal, subprocess, sys, time
        causal,cm,env,trust=self._scenario(); payload=self.root/'payload28.json'; receiver=self.root/'sigkill-after-backup.db'
        payload.write_text(json.dumps({'causal':causal,'cm':cm,'env':env,'trust':trust}))
        code="""import json,os,sys\nprint(os.getpid(),flush=True)\nfrom janus_infinity.core import JanusTwin\np=json.load(open(sys.argv[2])); r=JanusTwin(sys.argv[1]); r.atomic_joint_sync(p['causal'],p['cm'],{},dict(p['causal']['chunks']),p['trust'],[p['env']],hard_wait_at='after_promotion_backup')\n"""
        proc=subprocess.Popen([sys.executable,'-c',code,str(receiver),str(payload)],env={**os.environ,'PYTHONPATH':str(Path(__file__).parents[1]/'src')},stdout=subprocess.PIPE,text=True)
        db_pid=None
        try:
            db_pid=_read_child_pid(proc)  # PID of the interpreter holding the DB (a Windows venv proc.pid is a launcher stub)
            sid=None; receipt_digest=None
            for _ in range(160):
                time.sleep(.03)
                if receiver.exists():
                    try:
                        probe=JanusTwin(receiver)
                        row=probe.conn.execute("SELECT j.session_id,r.receipt_digest FROM promotion_journal j JOIN joint_receipts r ON r.session_id=j.session_id WHERE j.status='prepared' LIMIT 1").fetchone()
                        probe.close()
                        if row: sid,receipt_digest=row[0],row[1]; break
                    except Exception: pass
            self.assertIsNotNone(sid); self.assertIsNotNone(receipt_digest)
            # Windows has no SIGKILL: os.kill() there is an unconditional external TerminateProcess (exit code = sig) of the DB-holding
            # interpreter; the venv launcher waits for it and propagates that exit code, so wait() returns only once the DB holder is gone.
            if sys.platform=='win32': os.kill(db_pid,signal.SIGTERM); proc.wait(timeout=5); self.assertEqual(int(signal.SIGTERM),proc.returncode)
            else: os.kill(proc.pid,signal.SIGKILL); proc.wait(timeout=5); self.assertLess(proc.returncode,0)
        finally: _reap_crash_child(proc,db_pid)
        r=JanusTwin(receiver)
        try:
            self.assertEqual('ok',r.conn.execute('PRAGMA integrity_check').fetchone()[0])
            cert=r.recover_promotion(sid)
            self.assertEqual('committed',cert['outcome'])
            self.assertEqual(receipt_digest,cert['receipt_digest'])
            self.assertEqual('committed',r.promotion_journal(sid)['status'])
            self.assertGreater(r.conn.execute('SELECT COUNT(*) FROM facts').fetchone()[0],0)
        finally: r.close()
    def test_signed_forensic_link_binds_fault_recovery_and_receipt_history(self):
        causal,cm,env,trust=self._scenario(); r=JanusTwin(self.root/'forensic-link.db'); prior='d'*64
        try:
            r.conn.execute("INSERT INTO joint_receipts(receipt_digest,session_id,receipt_json,created_at) VALUES (?,?,?,?)",(prior,'prior','{}','2026-01-01T00:00:00Z')); r.conn.commit()
            with self.assertRaisesRegex(ValueError,'storage_stage_integrity_failed'):
                r.atomic_joint_sync(causal,cm,{},dict(causal['chunks']),trust,[env],storage_fault_at='corrupt_stage_before_promotion')
            sid=r.begin_sync_session(causal,cm,trust); q=r.storage_quarantine(sid)[0]
            cert=r.recover_promotion(sid)
            priv,pub=r.generate_signing_keypair(); audit=r.sign_storage_fault_evidence(q['evidence_digest'],'JANUS-AUDIT',priv)
            link=r.sign_forensic_proof_link(audit['audit_digest'],sid,'JANUS-AUDIT',priv)
            self.assertEqual(cert['certificate_digest'],link['recovery_certificate_digest'])
            self.assertEqual(prior,link['receipt_head_digest'])
            self.assertIsNone(link['session_receipt_digest'])
            self.assertTrue(r.verify_forensic_proof_link(link,{'JANUS-AUDIT':pub}))
            tampered=dict(link); tampered['receipt_head_digest']='0'*64
            self.assertFalse(r.verify_forensic_proof_link(tampered,{'JANUS-AUDIT':pub}))
        finally: r.close()

class Run029ShmHostFaultForensicDagTests(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def _scenario(self):
        helper=JanusRun021Tests(); helper.root=self.root; helper.sender=JanusTwin(self.root/'sender29.db')
        try: return helper._scenario()
        finally: helper.sender.close()

    def _live_wal_shm(self, db: Path):
        import sqlite3
        con=sqlite3.connect(db)
        con.execute('PRAGMA journal_mode=WAL')
        con.execute('PRAGMA wal_autocheckpoint=0')
        con.execute('CREATE TABLE shm_probe(x INTEGER)'); con.commit()
        con.execute('INSERT INTO shm_probe VALUES (1)'); con.commit()
        wal=Path(str(db)+'-wal'); shm=Path(str(db)+'-shm')
        self.assertTrue(wal.exists()); self.assertTrue(shm.exists())
        return con,wal.read_bytes(),shm.read_bytes()

    def test_shm_header_and_frame_map_match_wal_horizon(self):
        db=self.root/'shm-consistency.db'; con,wal_bytes,shm_bytes=self._live_wal_shm(db)
        try:
            report=JanusTwin.classify_storage_artifacts(db)
            self.assertEqual('shm_consistent',report['shm']['classification'])
            self.assertTrue(report['shm']['header_copies_identical'])
            self.assertTrue(report['shm']['header_checksum_valid'])
            self.assertEqual(report['wal']['last_commit_frame'],report['shm']['mx_frame'])
            self.assertEqual(report['wal']['last_commit_checksum'],report['shm']['frame_checksum'])
            self.assertEqual(report['wal']['salt_hex'],report['shm']['salt_hex'])
            self.assertTrue(report['shm']['frame_map_valid'])
            damaged=bytearray(shm_bytes)
            current=int.from_bytes(damaged[136:140],__import__('sys').byteorder)
            damaged[136:140]=((current+1) & 0xffffffff).to_bytes(4,__import__('sys').byteorder)
            bad=JanusTwin._classify_shm_bytes(Path(str(db)+'-shm'),bytes(damaged),report['wal'],wal_bytes)
            self.assertEqual('shm_wal_frame_map_mismatch',bad['classification'])
            self.assertEqual(1,bad['first_frame_map_mismatch'])
        finally:
            con.close()

    @unittest.skipIf(sys.platform=='win32',"POSIX-only: kernel RLIMIT_FSIZE/EFBIG needs setrlimit ('resource' module), absent on Windows; probe there fails closed as 'probe_failed'")
    def test_kernel_rlimit_fault_probe_is_real_and_isolated(self):
        receiver=JanusTwin(self.root/'authoritative.db'); before=receiver.state_digest()
        try:
            probe=JanusTwin.run_host_storage_fault_probe(self.root/'host-fault',max_file_bytes=1024,attempted_bytes=4096)
            self.assertEqual('kernel_file_size_limit',probe['classification'])
            self.assertEqual(27,probe['errno'])
            self.assertEqual('EFBIG',probe['errno_name'])
            self.assertLessEqual(probe['resulting_size_bytes'],1024)
            self.assertEqual(before,receiver.state_digest())
            self.assertEqual('ok',receiver.conn.execute('PRAGMA integrity_check').fetchone()[0])
        finally: receiver.close()

    def test_unified_forensic_dag_verifies_and_tamper_fails(self):
        causal,cm,env,trust=self._scenario(); r=JanusTwin(self.root/'dag.db')
        try:
            priv,pub=r.generate_signing_keypair()
            anchor_core={'format':'janus-joint-proof-receipt-v1','previous_receipt_digest':None,'session_id':'anchor-session','verified':True}
            anchor={**anchor_core,'receipt_digest':sha256_bytes(stable_json(anchor_core).encode())}
            anchor=r.sign_joint_receipt(anchor,'JANUS-AUDIT',priv)
            r.conn.execute("INSERT INTO joint_receipts(receipt_digest,session_id,previous_receipt_digest,signer_authority,signature_b64,receipt_json,created_at) VALUES (?,?,?,?,?,?,?)",(anchor['receipt_digest'],'anchor-session',None,'JANUS-AUDIT',anchor['signature']['signature_b64'],stable_json(anchor),'2026-01-01T00:00:00Z')); r.conn.commit()
            with self.assertRaisesRegex(ValueError,'storage_stage_integrity_failed'):
                r.atomic_joint_sync(causal,cm,{},dict(causal['chunks']),trust,[env],storage_fault_at='corrupt_stage_before_promotion')
            sid=r.begin_sync_session(causal,cm,trust); q=r.storage_quarantine(sid)[0]; r.recover_promotion(sid)
            audit=r.sign_storage_fault_evidence(q['evidence_digest'],'JANUS-AUDIT',priv)
            link=r.sign_forensic_proof_link(audit['audit_digest'],sid,'JANUS-AUDIT',priv)
            dag=r.build_forensic_proof_dag(link['link_digest'])
            verified=r.verify_forensic_proof_dag(dag,{'JANUS-AUDIT':pub})
            self.assertTrue(verified['valid'],verified)
            self.assertEqual({'forensic_link','storage_audit','quarantine','recovery_certificate','receipt'},set(n['kind'] for n in dag['nodes']))
            tampered=json.loads(json.dumps(dag))
            next(n for n in tampered['nodes'] if n['kind']=='recovery_certificate')['payload']['outcome']='committed'
            bad=r.verify_forensic_proof_dag(tampered,{'JANUS-AUDIT':pub})
            self.assertFalse(bad['valid'])
            self.assertIn('recovery_certificate_digest_mismatch',bad['errors'])
            omitted=json.loads(json.dumps(dag))
            audit_id='storage_audit:'+link['audit_digest']
            omitted['nodes']=[n for n in omitted['nodes'] if n['id']!=audit_id]
            omitted['edges']=[e for e in omitted['edges'] if e['to']!=audit_id and e['from']!=audit_id]
            core={k:omitted[k] for k in ('format','root_link_digest','nodes','edges')}; omitted['dag_digest']=sha256_bytes(stable_json(core).encode())
            missing=r.verify_forensic_proof_dag(omitted,{'JANUS-AUDIT':pub})
            self.assertFalse(missing['valid'])
            self.assertIn('referenced_node_missing',missing['errors'])
        finally: r.close()

class Run030StorageStateCertificateTests(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def _scenario(self):
        helper=JanusRun021Tests(); helper.root=self.root; helper.sender=JanusTwin(self.root/'sender30.db')
        try: return helper._scenario()
        finally: helper.sender.close()

    def test_signed_storage_state_certificate_binds_storage_recovery_receipt_and_forensic_dag(self):
        causal,cm,env,trust=self._scenario(); r=JanusTwin(self.root/'storage-state.db')
        try:
            priv,pub=r.generate_signing_keypair()
            anchor_core={'format':'janus-joint-proof-receipt-v1','previous_receipt_digest':None,'session_id':'anchor30','verified':True}
            anchor={**anchor_core,'receipt_digest':sha256_bytes(stable_json(anchor_core).encode())}
            anchor=r.sign_joint_receipt(anchor,'JANUS-STATE',priv)
            r.conn.execute("INSERT INTO joint_receipts(receipt_digest,session_id,previous_receipt_digest,signer_authority,signature_b64,receipt_json,created_at) VALUES (?,?,?,?,?,?,?)",(anchor['receipt_digest'],'anchor30',None,'JANUS-STATE',anchor['signature']['signature_b64'],stable_json(anchor),'2026-01-01T00:00:00Z')); r.conn.commit()
            with self.assertRaisesRegex(ValueError,'storage_stage_integrity_failed'):
                r.atomic_joint_sync(causal,cm,{},dict(causal['chunks']),trust,[env],storage_fault_at='corrupt_stage_before_promotion')
            sid=r.begin_sync_session(causal,cm,trust); q=r.storage_quarantine(sid)[0]; cert=r.recover_promotion(sid)
            audit=r.sign_storage_fault_evidence(q['evidence_digest'],'JANUS-STATE',priv)
            link=r.sign_forensic_proof_link(audit['audit_digest'],sid,'JANUS-STATE',priv)
            dag=r.build_forensic_proof_dag(link['link_digest'])
            state=r.build_storage_state_certificate(sid,'JANUS-STATE',priv,root_link_digest=link['link_digest'])
            self.assertEqual('janus-storage-state-certificate-v1',state['format'])
            self.assertEqual(anchor['receipt_digest'],state['receipt_head_digest'])
            self.assertEqual(cert['certificate_digest'],state['recovery_certificate_digest'])
            self.assertEqual(dag['dag_digest'],state['forensic_dag_digest'])
            self.assertEqual(link['link_digest'],state['forensic_root_link_digest'])
            self.assertEqual([q['evidence_digest']],state['quarantine_evidence_digests'])
            checked=r.verify_storage_state_certificate(state,{'JANUS-STATE':pub},forensic_dag=dag,db_path=r.db_path)
            self.assertTrue(checked['valid'],checked)
            r.add_fact({'subject':'RUN030.probe','predicate':'value','value':1,'valid_from':'2026-09-25T00:00:00Z','known_at':'2026-09-25T00:00:00Z','source':'run030-test'})
            stale=r.verify_storage_state_certificate(state,{'JANUS-STATE':pub},forensic_dag=dag,db_path=r.db_path)
            self.assertFalse(stale['valid']); self.assertIn('project_state_digest_mismatch',stale['errors'])
            tampered=json.loads(json.dumps(state)); tampered['receipt_head_digest']='0'*64
            bad=r.verify_storage_state_certificate(tampered,{'JANUS-STATE':pub},forensic_dag=dag,db_path=r.db_path)
            self.assertFalse(bad['valid']); self.assertIn('certificate_digest_mismatch',bad['errors'])
        finally: r.close()

    def test_kernel_write_permission_fault_probe_is_real_and_isolated(self):
        r=JanusTwin(self.root/'permission-authoritative.db'); before=r.state_digest()
        try:
            probe=JanusTwin.run_host_permission_fault_probe(self.root/'permission-probe')
            self.assertEqual('kernel_write_denied',probe['classification'])
            self.assertIn(probe['errno_name'],('EACCES','EPERM','EROFS'))
            self.assertFalse(probe['write_succeeded'])
            self.assertEqual(before,r.state_digest())
            self.assertEqual('ok',r.conn.execute('PRAGMA integrity_check').fetchone()[0])
        finally: r.close()

    def test_live_reconciliation_gate_fails_closed_and_verifies_clean_matching_repo(self):
        import subprocess
        absent=JanusTwin.live_reconciliation_gate(self.root/'not-a-repo')
        self.assertFalse(absent['ready_to_commit']); self.assertEqual('git_repository_unavailable',absent['status'])
        repo=self.root/'repo'; repo.mkdir(); subprocess.run(['git','init','-q'],cwd=repo,check=True)
        subprocess.run(['git','config','user.email','janus@example.invalid'],cwd=repo,check=True)
        subprocess.run(['git','config','user.name','JANUS Test'],cwd=repo,check=True)
        target=repo/'artifact.txt'; target.write_text('verified\n')
        subprocess.run(['git','add','artifact.txt'],cwd=repo,check=True); subprocess.run(['git','commit','-qm','baseline'],cwd=repo,check=True)
        no_expected=JanusTwin.live_reconciliation_gate(repo)
        self.assertFalse(no_expected['ready_to_commit']); self.assertEqual('expected_hashes_required',no_expected['status'])
        expected=sha256_bytes(target.read_bytes())
        clean=JanusTwin.live_reconciliation_gate(repo,{'artifact.txt':expected})
        self.assertTrue(clean['ready_to_commit'],clean); self.assertEqual('reconciled',clean['status']); self.assertEqual(expected,clean['files']['artifact.txt']['actual_sha256'])
        target.write_text('dirty\n')
        dirty=JanusTwin.live_reconciliation_gate(repo,{'artifact.txt':expected})
        self.assertFalse(dirty['ready_to_commit']); self.assertEqual('worktree_dirty',dirty['status'])

class Run031IndependentReceiverReplayTests(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def _scenario(self):
        helper=JanusRun021Tests(); helper.root=self.root; helper.sender=JanusTwin(self.root/'sender31-source.db')
        try: return helper._scenario()
        finally: helper.sender.close()
    def _certified_sender(self):
        causal,cm,env,trust=self._scenario(); sender=JanusTwin(self.root/'sender31.db')
        priv,pub=sender.generate_signing_keypair()
        anchor_core={'format':'janus-joint-proof-receipt-v1','previous_receipt_digest':None,'session_id':'anchor31','verified':True}
        anchor={**anchor_core,'receipt_digest':sha256_bytes(stable_json(anchor_core).encode())}
        anchor=sender.sign_joint_receipt(anchor,'JANUS-STATE',priv)
        sender.conn.execute("INSERT INTO joint_receipts(receipt_digest,session_id,previous_receipt_digest,signer_authority,signature_b64,receipt_json,created_at) VALUES (?,?,?,?,?,?,?)",(anchor['receipt_digest'],'anchor31',None,'JANUS-STATE',anchor['signature']['signature_b64'],stable_json(anchor),'2026-01-01T00:00:00Z')); sender.conn.commit()
        with self.assertRaisesRegex(ValueError,'storage_stage_integrity_failed'):
            sender.atomic_joint_sync(causal,cm,{},dict(causal['chunks']),trust,[env],storage_fault_at='corrupt_stage_before_promotion')
        sid=sender.begin_sync_session(causal,cm,trust); q=sender.storage_quarantine(sid)[0]; sender.recover_promotion(sid)
        audit=sender.sign_storage_fault_evidence(q['evidence_digest'],'JANUS-STATE',priv)
        link=sender.sign_forensic_proof_link(audit['audit_digest'],sid,'JANUS-STATE',priv)
        dag=sender.build_forensic_proof_dag(link['link_digest'])
        sender.add_fact({'subject':'RUN031.replay','predicate':'marker','value':'portable','valid_from':'2026-09-25T00:00:00Z','known_at':'2026-09-25T00:00:00Z','source':'run031-fixture'})
        cert=sender.build_storage_state_certificate(sid,'JANUS-STATE',priv,root_link_digest=link['link_digest'])
        return sender,priv,pub,sid,dag,cert

    def test_fresh_receiver_reconstructs_and_verifies_sender_certificate(self):
        sender,priv,pub,sid,dag,cert=self._certified_sender(); receiver=JanusTwin(self.root/'fresh-receiver.db')
        try:
            bundle=sender.build_receiver_replay_bundle(cert,dag)
            self.assertEqual('janus-receiver-replay-bundle-v1',bundle['format'])
            self.assertGreater(len(bundle['tables']),0)
            before=receiver.state_digest()
            result=receiver.import_and_verify_receiver_replay_bundle(bundle,{'JANUS-STATE':pub})
            self.assertTrue(result['valid'],result)
            self.assertEqual(cert['project_state_digest'],receiver.state_digest())
            self.assertEqual(cert['certificate_digest'],result['certificate_digest'])
            self.assertEqual(cert['receipt_head_digest'],receiver._receipt_head())
            recovery=receiver.conn.execute("SELECT certificate_digest FROM recovery_certificates WHERE session_id=?",(sid,)).fetchone()
            self.assertIsNotNone(recovery); self.assertEqual(cert['recovery_certificate_digest'],recovery[0])
            self.assertEqual(cert['quarantine_evidence_digests'],[q[0] for q in receiver.conn.execute("SELECT evidence_digest FROM storage_quarantine WHERE session_id=? ORDER BY evidence_digest",(sid,))])
            self.assertIsNotNone(receiver.conn.execute("SELECT 1 FROM promotion_journal WHERE session_id=?",(sid,)).fetchone())
            self.assertTrue(result['storage_snapshot_verified'])
            self.assertTrue(Path(result['storage_snapshot_db_path']).exists())
        finally:
            sender.close(); receiver.close()

    def test_replay_bundle_tamper_fails_before_receiver_promotion(self):
        sender,priv,pub,sid,dag,cert=self._certified_sender(); receiver=JanusTwin(self.root/'tamper-receiver.db')
        try:
            bundle=sender.build_receiver_replay_bundle(cert,dag); before=receiver.state_digest()
            tampered=json.loads(json.dumps(bundle))
            table=next(name for name,spec in tampered['tables'].items() if spec['rows'])
            tampered['tables'][table]['rows'][0][0]='tampered'
            with self.assertRaisesRegex(ValueError,'replay_bundle_digest_mismatch'):
                receiver.import_and_verify_receiver_replay_bundle(tampered,{'JANUS-STATE':pub})
            self.assertEqual(before,receiver.state_digest())
        finally:
            sender.close(); receiver.close()

    def test_replay_bundle_semantic_omission_fails_even_with_recomputed_outer_digest(self):
        sender,priv,pub,sid,dag,cert=self._certified_sender(); receiver=JanusTwin(self.root/'omission-receiver.db')
        try:
            bundle=sender.build_receiver_replay_bundle(cert,dag); before=receiver.state_digest()
            omitted=json.loads(json.dumps(bundle))
            omitted['tables']['recovery_certificates']['rows']=[]
            core={k:omitted.get(k) for k in ('format','certificate','forensic_dag','tables','storage_artifacts')}
            omitted['bundle_digest']=sha256_bytes(stable_json(core).encode())
            with self.assertRaisesRegex(ValueError,'replay_reconstruction_failed:.*recovery_certificate_mismatch'):
                receiver.import_and_verify_receiver_replay_bundle(omitted,{'JANUS-STATE':pub})
            self.assertEqual(before,receiver.state_digest())
            self.assertEqual(0,receiver.conn.execute("SELECT COUNT(*) FROM recovery_certificates").fetchone()[0])
        finally:
            sender.close(); receiver.close()

    def test_storage_certificate_chain_binds_deltas_and_predecessor(self):
        sender,priv,pub,sid,dag,cert1=self._certified_sender()
        try:
            sender.add_fact({'subject':'RUN031.delta','predicate':'value','value':1,'valid_from':'2026-09-25T01:00:00Z','known_at':'2026-09-25T01:00:00Z','source':'run031'})
            cert2=sender.build_storage_state_certificate(sid,'JANUS-STATE',priv,root_link_digest=cert1['forensic_root_link_digest'])
            e1=sender.build_storage_certificate_chain_entry(cert1,cert2,'JANUS-STATE',priv)
            sender.add_fact({'subject':'RUN031.delta','predicate':'value2','value':2,'valid_from':'2026-09-25T02:00:00Z','known_at':'2026-09-25T02:00:00Z','source':'run031'})
            cert3=sender.build_storage_state_certificate(sid,'JANUS-STATE',priv,root_link_digest=cert1['forensic_root_link_digest'])
            e2=sender.build_storage_certificate_chain_entry(cert2,cert3,'JANUS-STATE',priv,previous_chain_digest=e1['chain_digest'])
            certs={c['certificate_digest']:c for c in (cert1,cert2,cert3)}
            checked=sender.verify_storage_certificate_chain([e1,e2],certs,{'JANUS-STATE':pub})
            self.assertTrue(checked['valid'],checked)
            self.assertEqual(e1['chain_digest'],e2['previous_chain_digest'])
            self.assertTrue(e1['delta']['project_state']['changed'])
            wrong=sender.build_storage_certificate_chain_entry(cert2,cert3,'JANUS-STATE',priv,previous_chain_digest='0'*64)
            bad=sender.verify_storage_certificate_chain([e1,wrong],certs,{'JANUS-STATE':pub})
            self.assertFalse(bad['valid']); self.assertIn('previous_chain_digest_mismatch',bad['errors'])
        finally: sender.close()

    @unittest.skipIf(sys.platform=='win32',"POSIX-only: kernel RLIMIT_NOFILE/EMFILE needs setrlimit ('resource' module) and /dev/null, absent on Windows; probe there fails closed as 'unexpected'")
    def test_kernel_fd_exhaustion_probe_is_real_and_isolated(self):
        receiver=JanusTwin(self.root/'fd-authoritative.db'); before=receiver.state_digest()
        try:
            probe=JanusTwin.run_host_fd_exhaustion_probe(self.root/'fd-probe',max_open_files=32)
            self.assertEqual('kernel_fd_limit',probe['classification'])
            self.assertEqual(24,probe['errno'])
            self.assertEqual('EMFILE',probe['errno_name'])
            self.assertGreater(probe['opened_fds'],0)
            self.assertFalse(probe['authoritative_path_touched'])
            self.assertEqual(before,receiver.state_digest())
            self.assertEqual('ok',receiver.conn.execute('PRAGMA integrity_check').fetchone()[0])
        finally: receiver.close()

class Run032ObjectReplayForkFaultTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()

    def _certified_sender(self):
        helper=Run031IndependentReceiverReplayTests(); helper.root=self.root
        return helper._certified_sender()

    def test_minimal_object_graph_reconstructs_certified_receiver_with_exact_closure(self):
        sender,priv,pub,sid,dag,cert=self._certified_sender(); receiver=JanusTwin(self.root/'run032-receiver.db')
        try:
            graph=sender.build_object_replay_graph(cert,dag)
            self.assertEqual('janus-object-replay-graph-v1',graph['format'])
            self.assertNotIn('tables',graph)
            self.assertEqual(len(graph['objects']),graph['object_count'])
            all_tables=set(sender._replay_tables_snapshot())
            self.assertLess(set(graph['included_tables']),all_tables)
            before=receiver.state_digest()
            result=receiver.import_and_verify_object_replay_graph(graph,{'JANUS-STATE':pub})
            self.assertTrue(result['valid'],result)
            self.assertTrue(result['exact_closure_verified'])
            self.assertEqual(cert['project_state_digest'],receiver.state_digest())
            self.assertNotEqual(before,receiver.state_digest())
            self.assertEqual(cert['certificate_digest'],result['certificate_digest'])
            self.assertEqual(cert['receipt_head_digest'],receiver._receipt_head())
            self.assertEqual(cert['recovery_certificate_digest'],receiver.conn.execute("SELECT certificate_digest FROM recovery_certificates WHERE session_id=?",(sid,)).fetchone()[0])
        finally:
            sender.close(); receiver.close()

    def test_object_graph_rejects_missing_extra_and_substituted_objects_before_promotion(self):
        sender,priv,pub,sid,dag,cert=self._certified_sender(); receiver=JanusTwin(self.root/'run032-negative.db')
        try:
            graph=sender.build_object_replay_graph(cert,dag); before=receiver.state_digest()
            non_root=next(h for h in graph['objects'] if h!=graph['root_object'])

            missing=json.loads(json.dumps(graph)); missing['objects'].pop(non_root)
            missing['object_count']=len(missing['objects'])
            missing['graph_digest']=sha256_bytes(stable_json(JanusTwin._object_replay_graph_core(missing)).encode())
            with self.assertRaisesRegex(ValueError,'object_graph_missing_object'):
                receiver.import_and_verify_object_replay_graph(missing,{'JANUS-STATE':pub})
            self.assertEqual(before,receiver.state_digest())

            extra=json.loads(json.dumps(graph))
            extra_obj={'kind':'opaque-test','payload':{'unreachable':True},'refs':[]}
            extra_hash=sha256_bytes(stable_json(extra_obj).encode())
            extra['objects'][extra_hash]=extra_obj; extra['object_count']=len(extra['objects'])
            extra['graph_digest']=sha256_bytes(stable_json(JanusTwin._object_replay_graph_core(extra)).encode())
            with self.assertRaisesRegex(ValueError,'object_graph_extra_object'):
                receiver.import_and_verify_object_replay_graph(extra,{'JANUS-STATE':pub})
            self.assertEqual(before,receiver.state_digest())

            substituted=json.loads(json.dumps(graph)); substituted['objects'][non_root]['payload']={'tampered':True}
            substituted['graph_digest']=sha256_bytes(stable_json(JanusTwin._object_replay_graph_core(substituted)).encode())
            with self.assertRaisesRegex(ValueError,'object_graph_hash_mismatch'):
                receiver.import_and_verify_object_replay_graph(substituted,{'JANUS-STATE':pub})
            self.assertEqual(before,receiver.state_digest())
        finally:
            sender.close(); receiver.close()

    def test_signed_certificate_branches_produce_neutral_fork_evidence(self):
        sender,priv,pub,sid,dag,cert1=self._certified_sender()
        try:
            sender.add_fact({'subject':'RUN032.branch','predicate':'a','value':1,'valid_from':'2026-09-25T03:00:00Z','known_at':'2026-09-25T03:00:00Z','source':'run032'})
            cert2=sender.build_storage_state_certificate(sid,'JANUS-STATE',priv,root_link_digest=cert1['forensic_root_link_digest'])
            sender.add_fact({'subject':'RUN032.branch','predicate':'b','value':2,'valid_from':'2026-09-25T04:00:00Z','known_at':'2026-09-25T04:00:00Z','source':'run032'})
            cert3=sender.build_storage_state_certificate(sid,'JANUS-STATE',priv,root_link_digest=cert1['forensic_root_link_digest'])
            e1=sender.build_storage_certificate_chain_entry(cert1,cert2,'JANUS-STATE',priv)
            e2=sender.build_storage_certificate_chain_entry(cert1,cert3,'JANUS-STATE',priv)
            certs={c['certificate_digest']:c for c in (cert1,cert2,cert3)}
            result=sender.detect_storage_certificate_forks([e2,e1],certs,{'JANUS-STATE':pub})
            self.assertTrue(result['valid'],result)
            self.assertTrue(result['fork_detected'])
            self.assertEqual(1,len(result['forks']))
            fork=result['forks'][0]
            self.assertEqual(cert1['certificate_digest'],fork['previous_certificate_digest'])
            self.assertEqual(sorted([cert2['certificate_digest'],cert3['certificate_digest']]),fork['current_certificate_digests'])
            self.assertEqual(sorted([e1['chain_digest'],e2['chain_digest']]),fork['branch_chain_digests'])
            self.assertNotIn('winner',fork)
            self.assertEqual(fork['evidence_digest'],sha256_bytes(stable_json({k:fork[k] for k in ('format','previous_chain_digest','previous_certificate_digest','current_certificate_digests','branch_chain_digests')}).encode()))

            tampered=json.loads(json.dumps(e2)); tampered['signature']['signature_b64']='AAAA'
            bad=sender.detect_storage_certificate_forks([e1,tampered],certs,{'JANUS-STATE':pub})
            self.assertFalse(bad['valid'])
            self.assertIn('invalid_chain_entry',bad['errors'])
        finally: sender.close()

    @unittest.skipIf(sys.platform=='win32',"POSIX-only: kernel RLIMIT_FSIZE/EFBIG/SIGXFSZ needs setrlimit ('resource' module), absent on Windows; probe there fails closed as 'unexpected'")
    def test_kernel_file_size_limit_probe_is_real_and_isolated(self):
        receiver=JanusTwin(self.root/'run032-authoritative.db'); before=receiver.state_digest()
        try:
            probe=JanusTwin.run_host_file_size_limit_probe(self.root/'fsize-probe',max_file_bytes=4096)
            self.assertEqual('janus-host-file-size-fault-probe-v1',probe['format'])
            self.assertEqual('kernel_file_size_limit',probe['classification'])
            self.assertEqual(27,probe['errno'])
            self.assertEqual('EFBIG',probe['errno_name'])
            self.assertLessEqual(probe['bytes_written'],4096)
            self.assertFalse(probe['authoritative_path_touched'])
            self.assertEqual(before,receiver.state_digest())
            self.assertEqual('ok',receiver.conn.execute('PRAGMA integrity_check').fetchone()[0])
        finally: receiver.close()

class Run033SelectiveFetchConflictFaultTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def _certified_sender(self):
        helper=Run031IndependentReceiverReplayTests(); helper.root=self.root
        return helper._certified_sender()

    def test_selective_fetch_negotiates_only_missing_and_reconstructs(self):
        sender,priv,pub,sid,dag,cert=self._certified_sender(); receiver=JanusTwin(self.root/'r33.db')
        try:
            graph=sender.build_object_replay_graph(cert,dag); hashes=sorted(graph['objects']); cached={h:graph['objects'][h] for h in hashes[::2]}
            n=JanusTwin.negotiate_object_fetch(graph,cached)
            self.assertEqual(sorted(set(hashes)-set(cached)),n['missing_object_hashes'])
            resp=JanusTwin.fulfill_object_fetch(graph,n)
            header={k:v for k,v in graph.items() if k!='objects'}
            assembled=JanusTwin.assemble_fetched_object_graph(header,cached,resp)
            result=receiver.import_and_verify_object_replay_graph(assembled,{'JANUS-STATE':pub})
            self.assertTrue(result['valid']); self.assertEqual(cert['project_state_digest'],receiver.state_digest())
        finally: sender.close(); receiver.close()

    def test_selective_fetch_rejects_bad_missing_proof_overdelivery_and_equivocation(self):
        sender,priv,pub,sid,dag,cert=self._certified_sender()
        try:
            graph=sender.build_object_replay_graph(cert,dag); hashes=sorted(graph['objects']); cached={hashes[0]:graph['objects'][hashes[0]]}
            n=JanusTwin.negotiate_object_fetch(graph,cached); bad=json.loads(json.dumps(n)); bad['missing_object_hashes']=bad['missing_object_hashes'][:-1]
            with self.assertRaisesRegex(ValueError,'missing_object_proof_invalid'): JanusTwin.fulfill_object_fetch(graph,bad)
            resp=JanusTwin.fulfill_object_fetch(graph,n); extra=json.loads(json.dumps(resp)); extra['objects'][hashes[0]]=graph['objects'][hashes[0]]
            with self.assertRaisesRegex(ValueError,'overdelivery'): JanusTwin.assemble_fetched_object_graph({k:v for k,v in graph.items() if k!='objects'},cached,extra)
        finally: sender.close()

    def test_certificate_fork_crosslink_is_descriptive_and_never_selects_winner(self):
        fork={'format':'janus-storage-certificate-fork-evidence-v1','previous_chain_digest':'a','previous_certificate_digest':'p','current_certificate_digests':['c2','c1'],'branch_chain_digests':['b1','b2']}
        core={k:fork[k] for k in ('format','previous_chain_digest','previous_certificate_digest','current_certificate_digests','branch_chain_digests')}; fork['evidence_digest']=sha256_bytes(stable_json(core).encode())
        report={'valid':True,'forks':[fork]}; out=JanusTwin.crosslink_certificate_forks_to_temporal_conflicts(report)
        self.assertFalse(out['winner_selected']); self.assertNotIn('winner',out['conflicts'][0]); self.assertEqual('quarantined',out['conflicts'][0]['resolution']['status'])

    def test_real_enospc_probe_is_kernel_enforced_and_isolated_when_available(self):
        receiver=JanusTwin(self.root/'authority.db'); before=receiver.state_digest()
        try:
            probe=JanusTwin.run_host_enospc_probe()
            if probe['classification']=='unavailable': self.skipTest('/dev/full unavailable')
            self.assertEqual('kernel_storage_capacity',probe['classification']); self.assertEqual(28,probe['errno']); self.assertEqual('ENOSPC',probe['errno_name'])
            self.assertFalse(probe['authoritative_path_touched']); self.assertEqual(before,receiver.state_digest())
        finally: receiver.close()

class Run034ResumableAcquisitionSessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def _sender(self):
        helper=Run031IndependentReceiverReplayTests(); helper.root=self.root
        return helper._certified_sender()

    def test_resumable_session_chains_receipts_and_avoids_retransmit(self):
        sender,priv,pub,sid,dag,cert=self._sender()
        try:
            graph=sender.build_object_replay_graph(cert,dag)
            s0=JanusTwin.begin_object_acquisition_session(graph,{})
            first=s0['missing_object_hashes'][:max(1,len(s0['missing_object_hashes'])//2)]
            r1=JanusTwin.advance_object_acquisition_session(graph,s0,{h:graph['objects'][h] for h in first})
            self.assertEqual(sorted(first),r1['accepted_object_hashes'])
            self.assertTrue(set(first).isdisjoint(r1['missing_object_hashes']))
            r2=JanusTwin.advance_object_acquisition_session(graph,r1,{h:graph['objects'][h] for h in r1['missing_object_hashes']})
            self.assertEqual([],r2['missing_object_hashes']); self.assertTrue(r2['complete'])
            self.assertEqual(r1['receipt_digest'],r2['previous_receipt_digest'])
            assembled=JanusTwin.finalize_object_acquisition_session(graph,r2)
            self.assertEqual(graph['graph_digest'],assembled['graph_digest'])
        finally: sender.close()

    def test_session_rejects_stale_root_rollback_and_unrequested_objects(self):
        sender,priv,pub,sid,dag,cert=self._sender()
        try:
            graph=sender.build_object_replay_graph(cert,dag); s=JanusTwin.begin_object_acquisition_session(graph,{})
            stale=json.loads(json.dumps(s)); stale['graph_digest']='0'*64
            with self.assertRaisesRegex(ValueError,'session_graph_mismatch'): JanusTwin.advance_object_acquisition_session(graph,stale,{})
            h=s['missing_object_hashes'][0]; one=JanusTwin.advance_object_acquisition_session(graph,s,{h:graph['objects'][h]})
            rollback=json.loads(json.dumps(one)); rollback['accepted_object_hashes']=[]
            with self.assertRaisesRegex(ValueError,'session_receipt_invalid'): JanusTwin.advance_object_acquisition_session(graph,rollback,{})
            with self.assertRaisesRegex(ValueError,'unrequested_object'): JanusTwin.advance_object_acquisition_session(graph,one,{h:graph['objects'][h]})
        finally: sender.close()

    def test_session_rejects_cache_poison_and_object_substitution(self):
        sender,priv,pub,sid,dag,cert=self._sender()
        try:
            graph=sender.build_object_replay_graph(cert,dag); h=sorted(graph['objects'])[0]
            poisoned={h:{'poison':True}}
            with self.assertRaisesRegex(ValueError,'cached_object_invalid'): JanusTwin.begin_object_acquisition_session(graph,poisoned)
            s=JanusTwin.begin_object_acquisition_session(graph,{}) ; h=s['missing_object_hashes'][0]
            with self.assertRaisesRegex(ValueError,'object_hash_mismatch'): JanusTwin.advance_object_acquisition_session(graph,s,{h:{'wrong':True}})
        finally: sender.close()

    def test_session_receipts_are_deterministic_and_policy_neutral(self):
        sender,priv,pub,sid,dag,cert=self._sender()
        try:
            graph=sender.build_object_replay_graph(cert,dag)
            a=JanusTwin.begin_object_acquisition_session(graph,{}) ; b=JanusTwin.begin_object_acquisition_session(graph,{})
            self.assertEqual(a,b); self.assertFalse(a['winner_selected']); self.assertNotIn('winner',a)
            self.assertEqual(a['receipt_digest'],sha256_bytes(stable_json({k:a[k] for k in a if k!='receipt_digest'}).encode()))
        finally: sender.close()

class Run035CompactPortableAcquisitionProofTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def _sender(self):
        helper=Run031IndependentReceiverReplayTests(); helper.root=self.root
        return helper._certified_sender()

    def test_compact_receipts_exclude_object_bytes_and_resume_without_retransmit(self):
        sender,priv,pub,sid,dag,cert=self._sender()
        try:
            graph=sender.build_object_replay_graph(cert,dag); cache={}
            r0=JanusTwin.begin_compact_acquisition_session(graph,cache)
            self.assertNotIn('accepted_objects',r0)
            first=r0['missing_object_hashes'][:max(1,len(r0['missing_object_hashes'])//3)]
            supplied={h:graph['objects'][h] for h in first}
            cache.update(supplied)
            r1=JanusTwin.advance_compact_acquisition_session(graph,r0,cache,supplied)
            self.assertEqual(r0['receipt_digest'],r1['previous_receipt_digest'])
            self.assertTrue(set(first).isdisjoint(r1['missing_object_hashes']))
            self.assertLess(len(stable_json(r1)),len(stable_json(cache)))
            rest={h:graph['objects'][h] for h in r1['missing_object_hashes']}; cache.update(rest)
            r2=JanusTwin.advance_compact_acquisition_session(graph,r1,cache,rest)
            assembled=JanusTwin.finalize_compact_acquisition_session(graph,r2,cache)
            self.assertEqual(graph['graph_digest'],assembled['graph_digest']); self.assertTrue(r2['complete'])
        finally: sender.close()

    def test_compact_session_rejects_cache_rollback_stale_root_splice_and_retransmit(self):
        sender,priv,pub,sid,dag,cert=self._sender()
        try:
            graph=sender.build_object_replay_graph(cert,dag); cache={}; r0=JanusTwin.begin_compact_acquisition_session(graph,cache)
            h=r0['missing_object_hashes'][0]; supplied={h:graph['objects'][h]}; cache.update(supplied)
            r1=JanusTwin.advance_compact_acquisition_session(graph,r0,cache,supplied)
            with self.assertRaisesRegex(ValueError,'cache_continuity_mismatch'):
                JanusTwin.advance_compact_acquisition_session(graph,r1,{}, {})
            stale=json.loads(json.dumps(r1)); stale['graph_digest']='0'*64
            with self.assertRaisesRegex(ValueError,'session_graph_mismatch'):
                JanusTwin.advance_compact_acquisition_session(graph,stale,cache,{})
            with self.assertRaisesRegex(ValueError,'unrequested_object'):
                JanusTwin.advance_compact_acquisition_session(graph,r1,cache,{h:graph['objects'][h]})
            splice=json.loads(json.dumps(r1)); splice['previous_receipt_digest']='f'*64
            with self.assertRaisesRegex(ValueError,'session_receipt_invalid'):
                JanusTwin.advance_compact_acquisition_session(graph,splice,cache,{})
        finally: sender.close()

    def test_randomized_interruption_schedules_reconstruct_identically(self):
        import random
        sender,priv,pub,sid,dag,cert=self._sender()
        try:
            graph=sender.build_object_replay_graph(cert,dag); hashes=sorted(graph['objects'])
            for seed in range(12):
                rng=random.Random(seed); order=hashes[:]; rng.shuffle(order); cache={}; receipt=JanusTwin.begin_compact_acquisition_session(graph,cache); i=0
                while i<len(order):
                    width=rng.randint(1,min(5,len(order)-i)); batch=order[i:i+width]; supplied={h:graph['objects'][h] for h in batch}; cache.update(supplied)
                    receipt=JanusTwin.advance_compact_acquisition_session(graph,receipt,cache,supplied); i+=width
                assembled=JanusTwin.finalize_compact_acquisition_session(graph,receipt,cache)
                self.assertEqual(graph['graph_digest'],assembled['graph_digest']); self.assertEqual(graph['objects'],assembled['objects'])
        finally: sender.close()

    def test_compact_receipt_chain_is_deterministic_portable_and_policy_neutral(self):
        sender,priv,pub,sid,dag,cert=self._sender()
        try:
            graph=sender.build_object_replay_graph(cert,dag); a=JanusTwin.begin_compact_acquisition_session(graph,{}); b=JanusTwin.begin_compact_acquisition_session(graph,{})
            self.assertEqual(a,b); self.assertFalse(a['winner_selected']); self.assertNotIn('winner',a)
            h=a['missing_object_hashes'][0]; cache={h:graph['objects'][h]}
            r=JanusTwin.advance_compact_acquisition_session(graph,a,cache,cache)
            checked=JanusTwin.verify_compact_acquisition_receipt_chain([a,r],graph)
            self.assertTrue(checked['valid'],checked); self.assertEqual(r['receipt_digest'],checked['head_receipt_digest'])
            self.assertEqual(r['receipt_digest'],sha256_bytes(stable_json({k:r[k] for k in r if k!='receipt_digest'}).encode()))
        finally: sender.close()

class Run036AcquisitionProvenanceAndCacheContinuityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def _sender(self):
        helper=Run031IndependentReceiverReplayTests(); helper.root=self.root
        return helper._certified_sender()
    def _chain(self,graph):
        cache={}; receipts=[JanusTwin.begin_compact_acquisition_session(graph,cache)]
        hashes=receipts[0]['missing_object_hashes']; cut=max(1,len(hashes)//2)
        for batch in (hashes[:cut],hashes[cut:]):
            if not batch: continue
            supplied={h:graph['objects'][h] for h in batch}; cache.update(supplied)
            receipts.append(JanusTwin.advance_compact_acquisition_session(graph,receipts[-1],cache,supplied))
        return cache,receipts

    def test_acquisition_provenance_crosslink_is_descriptive_and_non_authoritative(self):
        sender,priv,pub,sid,dag,cert=self._sender()
        try:
            graph=sender.build_object_replay_graph(cert,dag); cache,receipts=self._chain(graph)
            link=JanusTwin.crosslink_compact_acquisition_provenance(receipts,graph)
            self.assertTrue(link['possession_continuity_verified']); self.assertTrue(link['complete'])
            self.assertFalse(link['temporal_truth_validity_asserted']); self.assertFalse(link['winner_selected'])
            self.assertEqual('descriptive_only',link['authority']); self.assertEqual(cert['certificate_digest'],graph['objects'][link['certificate_ref']]['payload']['certificate_digest'])
            self.assertEqual(receipts[-1]['receipt_digest'],link['head_receipt_digest'])
        finally: sender.close()

    def test_generated_splice_out_of_order_and_duplicate_round_schedules_fail_closed(self):
        sender,priv,pub,sid,dag,cert=self._sender()
        try:
            graph=sender.build_object_replay_graph(cert,dag); cache,receipts=self._chain(graph)
            schedules=JanusTwin.generate_compact_receipt_chain_adversarial_schedules(receipts)
            self.assertEqual({'duplicate_round','out_of_order','splice'},set(schedules))
            for name,chain in schedules.items():
                checked=JanusTwin.verify_compact_acquisition_receipt_chain(chain,graph)
                self.assertFalse(checked['valid'],(name,checked)); self.assertTrue(checked['errors'])
        finally: sender.close()

    def test_cache_snapshot_restore_proves_possession_but_not_temporal_truth(self):
        sender,priv,pub,sid,dag,cert=self._sender()
        try:
            graph=sender.build_object_replay_graph(cert,dag); cache,receipts=self._chain(graph)
            snapshot=JanusTwin.build_compact_cache_snapshot(graph,receipts[-1],cache)
            restored=JanusTwin.restore_compact_cache_snapshot(graph,snapshot)
            self.assertEqual(cache,restored['cache'])
            proof=restored['proof']; self.assertTrue(proof['possession_continuity_verified'])
            self.assertFalse(proof['temporal_truth_validity_asserted']); self.assertTrue(proof['requires_independent_truth_revalidation'])
            self.assertFalse(proof['winner_selected'])
            assembled=JanusTwin.finalize_compact_acquisition_session(graph,receipts[-1],restored['cache'])
            self.assertEqual(graph['graph_digest'],assembled['graph_digest'])
        finally: sender.close()

    def test_cache_snapshot_tamper_or_graph_substitution_fails_closed(self):
        sender,priv,pub,sid,dag,cert=self._sender()
        try:
            graph=sender.build_object_replay_graph(cert,dag); cache,receipts=self._chain(graph)
            snapshot=JanusTwin.build_compact_cache_snapshot(graph,receipts[-1],cache)
            bad=json.loads(json.dumps(snapshot)); bad['objects'][next(iter(bad['objects']))]={'tampered':True}
            with self.assertRaisesRegex(ValueError,'cache_snapshot_invalid'): JanusTwin.restore_compact_cache_snapshot(graph,bad)
            other=json.loads(json.dumps(snapshot)); other['graph_digest']='0'*64
            core={k:v for k,v in other.items() if k!='snapshot_digest'}; other['snapshot_digest']=sha256_bytes(stable_json(core).encode())
            with self.assertRaisesRegex(ValueError,'cache_snapshot_graph_mismatch'): JanusTwin.restore_compact_cache_snapshot(graph,other)
        finally: sender.close()

class Run037PortableProvenanceReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def _sender(self):
        helper=Run031IndependentReceiverReplayTests(); helper.root=self.root
        return helper._certified_sender()
    def _complete_chain_snapshot(self,graph):
        cache={}; receipts=[JanusTwin.begin_compact_acquisition_session(graph,cache)]
        hashes=list(receipts[0]['missing_object_hashes']); cut=max(1,len(hashes)//2)
        for batch in (hashes[:cut],hashes[cut:]):
            if not batch: continue
            supplied={h:graph['objects'][h] for h in batch}; cache.update(supplied)
            receipts.append(JanusTwin.advance_compact_acquisition_session(graph,receipts[-1],cache,supplied))
        snapshot=JanusTwin.build_compact_cache_snapshot(graph,receipts[-1],cache)
        return cache,receipts,snapshot

    def test_portable_bundle_replays_on_fresh_receiver_and_emits_truth_revalidation_receipt(self):
        sender,priv,pub,sid,dag,cert=self._sender(); receiver=JanusTwin(self.root/'run037-receiver.db')
        try:
            graph=sender.build_object_replay_graph(cert,dag); cache,receipts,snapshot=self._complete_chain_snapshot(graph)
            bundle=JanusTwin.build_portable_provenance_replay_bundle(graph,receipts,snapshot)
            before=receiver.state_digest(); result=receiver.replay_portable_provenance_bundle(bundle,{'JANUS-STATE':pub})
            self.assertTrue(result['valid'],result); self.assertNotEqual(before,receiver.state_digest())
            self.assertTrue(result['portable_verification']['possession_continuity_verified'])
            receipt=result['truth_revalidation_receipt']
            self.assertTrue(receipt['temporal_truth_revalidated']); self.assertFalse(receipt['possession_evidence_truth_authority'])
            self.assertEqual('independent_receiver_object_replay',receipt['basis'])
            self.assertEqual(bundle['bundle_digest'],receipt['bundle_digest'])
            self.assertEqual(result['restore_proof']['proof_digest'],receipt['restore_proof_digest'])
            self.assertEqual(result['receiver_replay']['reconstruction_receipt']['receipt_digest'],receipt['reconstruction_receipt_digest'])
            self.assertFalse(receipt['winner_selected'])
        finally: sender.close(); receiver.close()

    def test_possession_proof_alone_cannot_mint_truth_revalidation(self):
        sender,priv,pub,sid,dag,cert=self._sender()
        try:
            graph=sender.build_object_replay_graph(cert,dag); cache,receipts,snapshot=self._complete_chain_snapshot(graph)
            bundle=JanusTwin.build_portable_provenance_replay_bundle(graph,receipts,snapshot)
            restored=JanusTwin.restore_compact_cache_snapshot(graph,snapshot)
            with self.assertRaisesRegex(ValueError,'truth_revalidation_not_verified'):
                JanusTwin.build_replay_truth_revalidation_receipt(bundle,restored['proof'],{'valid':False})
        finally: sender.close()

    def test_generated_portable_corruption_schedules_fail_before_receiver_promotion(self):
        sender,priv,pub,sid,dag,cert=self._sender()
        try:
            graph=sender.build_object_replay_graph(cert,dag); cache,receipts,snapshot=self._complete_chain_snapshot(graph)
            bundle=JanusTwin.build_portable_provenance_replay_bundle(graph,receipts,snapshot)
            schedules=JanusTwin.generate_portable_provenance_corruption_schedules(bundle)
            self.assertEqual({'crosslink_head_mismatch','receipt_chain_truncation','snapshot_object_substitution'},set(schedules))
            for name,bad in schedules.items():
                receiver=JanusTwin(self.root/f'bad-{name}.db'); before=receiver.state_digest()
                try:
                    with self.assertRaises(ValueError): receiver.replay_portable_provenance_bundle(bad,{'JANUS-STATE':pub})
                    self.assertEqual(before,receiver.state_digest())
                finally: receiver.close()
        finally: sender.close()

    def test_portable_verification_is_deterministic_and_non_authoritative(self):
        sender,priv,pub,sid,dag,cert=self._sender()
        try:
            graph=sender.build_object_replay_graph(cert,dag); cache,receipts,snapshot=self._complete_chain_snapshot(graph)
            a=JanusTwin.build_portable_provenance_replay_bundle(graph,receipts,snapshot)
            b=JanusTwin.build_portable_provenance_replay_bundle(graph,receipts,snapshot)
            self.assertEqual(a,b)
            checked=JanusTwin.verify_portable_provenance_replay_bundle(a)
            self.assertTrue(checked['valid']); self.assertTrue(checked['possession_continuity_verified'])
            self.assertFalse(checked['temporal_truth_validity_asserted']); self.assertTrue(checked['requires_independent_truth_revalidation'])
            self.assertFalse(checked['winner_selected'])
        finally: sender.close()

class Run038RevalidationLedgerAndEquivalenceTests(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def _sender(self):
        helper=Run031IndependentReceiverReplayTests(); helper.root=self.root
        return helper._certified_sender()
    def _bundle(self,graph,batches=2):
        cache={}; receipts=[JanusTwin.begin_compact_acquisition_session(graph,cache)]
        hashes=list(receipts[0]['missing_object_hashes'])
        if batches==1: chunks=[hashes]
        else:
            cut=max(1,len(hashes)//2); chunks=[hashes[:cut],hashes[cut:]]
        for batch in chunks:
            if not batch: continue
            supplied={h:graph['objects'][h] for h in batch}; cache.update(supplied)
            receipts.append(JanusTwin.advance_compact_acquisition_session(graph,receipts[-1],cache,supplied))
        snapshot=JanusTwin.build_compact_cache_snapshot(graph,receipts[-1],cache)
        return JanusTwin.build_portable_provenance_replay_bundle(graph,receipts,snapshot)

    def test_revalidation_receipt_chain_is_durable_and_stale_head_fails_closed(self):
        sender,priv,pub,sid,dag,cert=self._sender(); path=self.root/'run038-ledger.db'; receiver=JanusTwin(path)
        try:
            graph=sender.build_object_replay_graph(cert,dag)
            r1=receiver.replay_portable_provenance_bundle(self._bundle(graph,2),{'JANUS-STATE':pub})
            e1=receiver.append_truth_revalidation_receipt(r1['truth_revalidation_receipt'],r1['receiver_replay'],expected_previous_entry_digest=None)
            r2=receiver.replay_portable_provenance_bundle(self._bundle(graph,1),{'JANUS-STATE':pub})
            e2=receiver.append_truth_revalidation_receipt(r2['truth_revalidation_receipt'],r2['receiver_replay'],expected_previous_entry_digest=e1['entry_digest'])
            self.assertEqual(e1['entry_digest'],e2['previous_entry_digest']); self.assertEqual(2,e2['sequence'])
            with self.assertRaisesRegex(ValueError,'revalidation_chain_stale_head'):
                receiver.append_truth_revalidation_receipt(r1['truth_revalidation_receipt'],r1['receiver_replay'],expected_previous_entry_digest=None)
        finally: receiver.close(); sender.close()
        reopened=JanusTwin(path)
        try:
            chain=reopened.export_truth_revalidation_receipt_chain(); checked=JanusTwin.verify_truth_revalidation_receipt_chain(chain,expected_head_digest=e2['entry_digest'])
            self.assertTrue(checked['valid'],checked); self.assertEqual(2,checked['entry_count']); self.assertEqual(e2['entry_digest'],checked['head_entry_digest'])
        finally: reopened.close()

    def test_chain_rollback_and_tamper_are_detected(self):
        sender,priv,pub,sid,dag,cert=self._sender(); receiver=JanusTwin(self.root/'run038-rollback.db')
        try:
            graph=sender.build_object_replay_graph(cert,dag)
            results=[]
            for n in (2,1): results.append(receiver.replay_portable_provenance_bundle(self._bundle(graph,n),{'JANUS-STATE':pub}))
            e1=receiver.append_truth_revalidation_receipt(results[0]['truth_revalidation_receipt'],results[0]['receiver_replay'],expected_previous_entry_digest=None)
            e2=receiver.append_truth_revalidation_receipt(results[1]['truth_revalidation_receipt'],results[1]['receiver_replay'],expected_previous_entry_digest=e1['entry_digest'])
            chain=receiver.export_truth_revalidation_receipt_chain()
            rolled=JanusTwin.verify_truth_revalidation_receipt_chain(chain[:-1],expected_head_digest=e2['entry_digest'])
            self.assertFalse(rolled['valid']); self.assertIn('revalidation_chain_rollback',rolled['errors'])
            tampered=json.loads(json.dumps(chain)); tampered[1]['previous_entry_digest']='f'*64
            bad=JanusTwin.verify_truth_revalidation_receipt_chain(tampered,expected_head_digest=e2['entry_digest'])
            self.assertFalse(bad['valid']); self.assertIn('revalidation_entry_digest_invalid',bad['errors'])
        finally: sender.close(); receiver.close()

    def test_cross_receiver_equivalence_requires_independent_matching_truth_receipts(self):
        sender,priv,pub,sid,dag,cert=self._sender(); a=JanusTwin(self.root/'receiver-a.db'); b=JanusTwin(self.root/'receiver-b.db')
        try:
            graph=sender.build_object_replay_graph(cert,dag); bundle=self._bundle(graph,2)
            ra=a.replay_portable_provenance_bundle(bundle,{'JANUS-STATE':pub}); rb=b.replay_portable_provenance_bundle(bundle,{'JANUS-STATE':pub})
            proof=JanusTwin.build_cross_receiver_replay_equivalence('receiver-a',ra['truth_revalidation_receipt'],'receiver-b',rb['truth_revalidation_receipt'])
            self.assertTrue(proof['equivalent']); self.assertEqual(cert['certificate_digest'],proof['certificate_digest'])
            self.assertEqual(cert['project_state_digest'],proof['project_state_digest']); self.assertFalse(proof['winner_selected'])
            forged=json.loads(json.dumps(rb['truth_revalidation_receipt'])); forged['project_state_digest']='0'*64
            core={k:v for k,v in forged.items() if k!='receipt_digest'}; forged['receipt_digest']=sha256_bytes(stable_json(core).encode())
            with self.assertRaisesRegex(ValueError,'cross_receiver_replay_mismatch'):
                JanusTwin.build_cross_receiver_replay_equivalence('receiver-a',ra['truth_revalidation_receipt'],'receiver-b',forged)
        finally: sender.close(); a.close(); b.close()

    def test_generated_forged_and_stale_truth_receipts_fail_binding_verification(self):
        sender,priv,pub,sid,dag,cert=self._sender(); receiver=JanusTwin(self.root/'run038-corrupt.db')
        try:
            graph=sender.build_object_replay_graph(cert,dag); bundle=self._bundle(graph,2)
            result=receiver.replay_portable_provenance_bundle(bundle,{'JANUS-STATE':pub}); receipt=result['truth_revalidation_receipt']
            schedules=JanusTwin.generate_truth_revalidation_receipt_corruption_schedules(receipt)
            self.assertEqual({'forged_certificate','forged_reconstruction','stale_bundle'},set(schedules))
            for bad in schedules.values():
                with self.assertRaises(ValueError): JanusTwin.verify_replay_truth_revalidation_receipt(bad,bundle,result['receiver_replay'])
        finally: sender.close(); receiver.close()
