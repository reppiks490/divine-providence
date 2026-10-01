import hashlib
import json
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from aion.contracts import EvidenceTier as Tier, Observation, SourceSpec
from aion.demo import SECOND, START, install
from aion.federation import export_views
from aion.replay import Scenario, compare, frame
from aion.store import EventStore, GapError
from aion.webapp import handler_for


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = EventStore(Path(self.temp.name) / "memory.sqlite3")

    def source(self, source_id="bar", representation="clock:1m", kind=("bar",), tier=Tier.CANDLE_PROXY, sequence="none"):
        spec = SourceSpec(source_id, representation, "NQ", kind, tier,
                          hashlib.sha256(source_id.encode()).hexdigest(), sequence_policy=sequence,
                          origin="unit_test", license_reference="unit-test", evidence_reference="unit-test")
        self.store.register(spec)
        return spec

    def event(self, source="bar", name="row", *, revision=1, kind="bar", event_ns=10,
              available_ns=11, sequence=None, tier=Tier.CANDLE_PROXY, payload=None):
        return Observation(source, name, revision, kind, event_ns, available_ns, available_ns,
                           tier, payload or {"open": 1, "high": 2, "low": 1, "close": 2},
                           sequence=sequence)

    def test_observed_receipt_cannot_claim_earlier_availability(self):
        with self.assertRaisesRegex(ValueError, "must equal ingestion"):
            Observation("bar", "row", 1, "bar", 10, 11, 100, Tier.CANDLE_PROXY,
                        {"open": 1, "high": 2, "low": 1, "close": 2})

    def test_asof_revision_and_same_timestamp_representation(self):
        self.source()
        self.source("renko", "renko:owner-verified")
        first = self.store.append(self.event())
        self.store.append(self.event(source="renko", name="r1", event_ns=10, available_ns=12))
        self.store.append(self.event(source="renko", name="r2", event_ns=10, available_ns=13))
        self.store.append(self.event(revision=2, available_ns=20, payload={"open": 1, "high": 3, "low": 1, "close": 3}))
        self.assertEqual(self.store.append(self.event()), {**first, "idempotent": True})
        self.assertEqual(len(self.store.asof(11)), 1)
        self.assertEqual(len(self.store.asof(13)), 3)
        self.assertEqual(len(self.store.asof(20)), 3)
        self.assertEqual(self.store.asof(20)[-1]["event"]["revision"], 2)
        self.assertEqual(len(self.store.asof(20, include_revisions=True)), 4)
        self.assertTrue(self.store.verify_chain()["verified"])

    def test_revisions_cannot_be_retroactively_available(self):
        self.source()
        self.store.append(self.event(available_ns=20))
        with self.assertRaisesRegex(ValueError, "availability must increase"):
            self.store.append(self.event(revision=2, available_ns=19,
                                         payload={"open": 1, "high": 3, "low": 1, "close": 3}))
        self.assertEqual(self.store.asof(20)[0]["event"]["revision"], 1)

    def test_revision_cannot_change_fact_kind_or_event_time(self):
        self.source("mixed", "clock:1m", ("bar", "macro"))
        self.store.append(self.event(source="mixed", available_ns=20))
        with self.assertRaisesRegex(ValueError, "fact identity"):
            self.store.append(self.event(source="mixed", revision=2, kind="macro", event_ns=10,
                                         available_ns=30, payload={"series": "CPI", "period": "2026-08"}))
        with self.assertRaisesRegex(ValueError, "fact identity"):
            self.store.append(self.event(source="mixed", revision=2, event_ns=11, available_ns=30))

    def test_future_publication_and_prediction_leak_block(self):
        self.source("macro", "macro:v1", ("macro",))
        self.source()
        old = self.store.append(self.event())
        future = self.store.append(self.event(source="macro", name="release", kind="macro", event_ns=30,
                                              available_ns=40, payload={"series": "CPI", "period": "2026-08", "surprise": 2}))
        self.assertEqual(len(self.store.asof(39)), 1)
        self.assertEqual(len(self.store.asof(40)), 2)
        with self.assertRaisesRegex(ValueError, "future evidence"):
            from aion.replay import frame
            self.store.predict(decision_ns=39, horizon_ns=50, model_id="m1", symbol="NQ",
                               forecast=.7, confidence=.8, abstain=False, reason_codes=["test"],
                               evidence_hashes=[old["event_hash"], future["event_hash"]],
                               frame_hash=frame(self.store, 39)["frame_hash"])
        prediction = self.store.predict(decision_ns=39, horizon_ns=50, model_id="m1", symbol="NQ",
                                        forecast=.7, confidence=.8, abstain=False, reason_codes=["test"],
                                        evidence_hashes=[old["event_hash"]],
                                        frame_hash=frame(self.store, 39)["frame_hash"])
        with self.assertRaisesRegex(ValueError, "horizon incomplete"):
            self.store.settle(prediction["prediction_id"], outcome_ns=49, realized_move=1, outcome_reference="test")
        self.store.settle(prediction["prediction_id"], outcome_ns=51, realized_move=1, outcome_reference="test")
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.store.settle(prediction["prediction_id"], outcome_ns=52, realized_move=2, outcome_reference="rewrite")

    def test_late_import_cannot_rewrite_a_frozen_prediction_frame(self):
        self.source()
        first = self.store.append(self.event(name="first", available_ns=11))
        original = frame(self.store, 20)
        prediction = self.store.predict(decision_ns=20, horizon_ns=30, model_id="review", symbol="NQ",
                                        forecast=1.0, confidence=0.5, abstain=False,
                                        reason_codes=["test"], evidence_hashes=[first["event_hash"]],
                                        frame_hash=original["frame_hash"])
        self.assertEqual(prediction["schema"], 2)
        self.assertEqual(prediction["issuance_class"], "retrospective_replay")
        self.assertFalse(prediction["performance_eligible"])
        self.store.append(self.event(name="late-import", event_ns=12, available_ns=13))
        self.assertNotEqual(frame(self.store, 20)["frame_hash"], original["frame_hash"])
        self.assertEqual(self.store.frozen_frame(prediction["prediction_id"])["frame_hash"], original["frame_hash"])
        settlement = self.store.settle(prediction["prediction_id"], outcome_ns=31,
                                       realized_move=999, outcome_reference="unverified-fixture")
        self.assertFalse(settlement["outcome_verified"])

    def test_later_gap_transition_cannot_rewrite_frozen_book_quality(self):
        self.source("depth", "book:l2", ("book_snapshot", "book_delta"), Tier.TRUE_DEPTH, "contiguous")
        snapshot = self.store.append(self.event("depth", "s1", kind="book_snapshot", sequence=1,
                                                tier=Tier.TRUE_DEPTH,
                                                payload={"bids": [[99, 5]], "asks": [[100, 4]]}))
        original = frame(self.store, 20)
        prediction = self.store.predict(decision_ns=20, horizon_ns=30, model_id="review", symbol="NQ",
                                        forecast=1.0, confidence=0.5, abstain=False,
                                        reason_codes=["test"], evidence_hashes=[snapshot["event_hash"]],
                                        frame_hash=original["frame_hash"])
        with self.assertRaises(GapError):
            self.store.append(self.event("depth", "d3", kind="book_delta", event_ns=12,
                                         available_ns=13, sequence=3, tier=Tier.TRUE_DEPTH,
                                         payload={"side": "bid", "price": 99, "size": 8, "action": "set"}))
        self.assertEqual(frame(self.store, 20)["books"]["depth"]["status"], "sequence_gap")
        self.assertEqual(self.store.frozen_frame(prediction["prediction_id"])["books"]["depth"]["status"], "true_depth")

    def test_macro_vintage_cannot_replace_a_newer_observation_period(self):
        self.source("macro", "macro:vintage", ("macro",))
        self.store.append(self.event("macro", "jan", kind="macro", event_ns=10, available_ns=11,
                                     payload={"series": "CPI", "period": "2026-01", "value": 1}))
        self.store.append(self.event("macro", "feb", kind="macro", event_ns=20, available_ns=21,
                                     payload={"series": "CPI", "period": "2026-02", "value": 2}))
        self.store.append(self.event("macro", "jan", revision=2, kind="macro", event_ns=10,
                                     available_ns=31, payload={"series": "CPI", "period": "2026-01", "value": 3}))
        state = frame(self.store, 31)
        self.assertEqual({row["values"]["period"] for row in state["macro"]}, {"2026-01", "2026-02"})
        self.assertEqual(next(row for row in state["macro"] if row["values"]["period"] == "2026-01")["revision"], 2)

    def test_evidence_tier_firewall(self):
        self.source("csv", "clock:1m", ("bar", "trade", "book_snapshot"))
        with self.assertRaisesRegex(ValueError, "exceeds"):
            self.store.append(self.event(source="csv", kind="trade", tier=Tier.TRUE_TRADE,
                                         payload={"price": 2, "size": 1}))
        with self.assertRaisesRegex(ValueError, "requires authenticated"):
            self.store.append(self.event(source="csv", kind="book_snapshot", sequence=1,
                                         payload={"bids": [], "asks": []}))
        self.assertEqual(self.store.timeline(), [])

    def test_sequence_gap_requires_provider_recovery(self):
        self.source("depth", "book:l2", ("book_snapshot", "book_delta"), Tier.TRUE_DEPTH, "contiguous")
        snapshot = self.event("depth", "s1", kind="book_snapshot", sequence=1, tier=Tier.TRUE_DEPTH,
                              payload={"bids": [[99, 5]], "asks": [[100, 4]]})
        self.store.append(snapshot)
        self.assertEqual(frame(self.store, 12)["books"]["depth"]["status"], "true_depth")
        with self.assertRaises(GapError):
            self.store.append(self.event("depth", "d3", kind="book_delta", event_ns=12,
                                         available_ns=13, sequence=3, tier=Tier.TRUE_DEPTH,
                                         payload={"side": "bid", "price": 99, "size": 8, "action": "set"}))
        self.assertEqual(len(self.store.gaps()), 1)
        self.assertEqual(frame(self.store, 12)["books"]["depth"]["status"], "true_depth")
        self.assertEqual(frame(self.store, 13)["books"]["depth"]["status"], "sequence_gap")
        with self.assertRaises(GapError):
            self.store.append(self.event("depth", "d4", kind="book_delta", sequence=4,
                                         tier=Tier.TRUE_DEPTH, payload={"side": "bid", "price": 99, "size": 8, "action": "set"}))
        recovery = Observation("depth", "s5", 1, "book_snapshot", 14, 15, 15,
                               Tier.TRUE_DEPTH, {"bids": [[99, 7]], "asks": [[100, 4]]},
                               sequence=5, quality_flags=("provider_recovery",))
        self.store.append(recovery)
        self.assertEqual(self.store.gaps(), [])
        self.assertEqual(frame(self.store, 13)["books"]["depth"]["status"], "sequence_gap")
        self.assertEqual(frame(self.store, 15)["books"]["depth"]["status"], "true_depth")
        self.assertEqual(len(self.store.gaps_asof(13)), 1)
        self.assertEqual(self.store.gaps_asof(15), [])

    def test_recovery_cannot_be_backdated_before_gap(self):
        self.source("depth", "book:l2", ("book_snapshot", "book_delta"), Tier.TRUE_DEPTH, "contiguous")
        self.store.append(self.event("depth", "s1", kind="book_snapshot", sequence=1,
                                     tier=Tier.TRUE_DEPTH, payload={"bids": [[99, 5]], "asks": [[100, 4]]}))
        with self.assertRaises(GapError):
            self.store.append(self.event("depth", "d3", kind="book_delta", event_ns=12,
                                         available_ns=30, sequence=3, tier=Tier.TRUE_DEPTH,
                                         payload={"side": "bid", "price": 99, "size": 8, "action": "set"}))
        recovery = self.event("depth", "s3", kind="book_snapshot", event_ns=14,
                              available_ns=20, sequence=3, tier=Tier.TRUE_DEPTH,
                              payload={"bids": [[99, 5]], "asks": [[100, 4]]})
        recovery = Observation(**{**recovery.to_dict(), "evidence_tier": Tier.TRUE_DEPTH,
                                  "quality_flags": ("provider_recovery",)})
        with self.assertRaisesRegex(GapError, "follow the observed gap"):
            self.store.append(recovery)

    def test_book_revision_requires_reviewed_correction_semantics(self):
        self.source("depth", "book:l2", ("book_snapshot",), Tier.TRUE_DEPTH, "contiguous")
        self.store.append(self.event("depth", "s1", kind="book_snapshot", sequence=1, tier=Tier.TRUE_DEPTH,
                                     payload={"bids": [[99, 5]], "asks": [[100, 4]]}))
        with self.assertRaisesRegex(ValueError, "reviewed provider adapter"):
            self.store.append(self.event("depth", "s1", revision=2, kind="book_snapshot", available_ns=20,
                                         sequence=2, tier=Tier.TRUE_DEPTH,
                                         payload={"bids": [[99, 6]], "asks": [[100, 4]]}))

    def test_demo_is_time_correct_and_scenarios_are_labeled(self):
        install(self.store)
        before = frame(self.store, START + 242 * SECOND)
        after = frame(self.store, START + 243 * SECOND)
        self.assertEqual(before["macro"], [])
        self.assertEqual(len(after["macro"]), 1)
        self.assertEqual(before["books"]["DEMO:NQ:book"]["status"], "true_depth")
        self.assertTrue(before["synthetic"])
        self.assertIsNone(before["scenario"])
        self.assertIn("DEMO:NQ:book", before["quality"]["synthetic_sources"])
        self.assertEqual(before, frame(self.store, START + 242 * SECOND))
        drought = frame(self.store, START + 242 * SECOND, scenario=Scenario("drought", depth_multiplier=0))
        self.assertTrue(drought["synthetic"])
        self.assertEqual(drought["books"]["DEMO:NQ:book"]["status"], "synthetic_liquidity_drought")
        self.assertFalse(compare(before, drought)["empirical_counterfactual_fill"])
        views = export_views(before)
        self.assertTrue(all(packet["synthetic"] for packet in views.values()))
        self.assertFalse(views["icarus"]["execution_authorized"])
        self.assertEqual(views["icarus"]["suggested_order"], None)

    def test_synthetic_event_cannot_hide_under_real_source(self):
        self.source()
        event = Observation("bar", "synthetic", 1, "bar", 10, 11, 100, Tier.CANDLE_PROXY,
                            {"open": 1, "high": 2, "low": 1, "close": 2},
                            quality_flags=("synthetic",), availability_basis="synthetic")
        with self.assertRaisesRegex(ValueError, "synthetic source"):
            self.store.append(event)

    def test_stale_depth_is_not_exported_as_true_depth(self):
        self.source("depth", "book:l2", ("book_snapshot",), Tier.TRUE_DEPTH, "contiguous")
        self.store.append(self.event("depth", "s1", kind="book_snapshot", sequence=1,
                                     tier=Tier.TRUE_DEPTH, payload={"bids": [[99, 5]], "asks": [[100, 4]]}))
        state = frame(self.store, 20_000_000_000)
        self.assertEqual(state["books"]["depth"]["status"], "stale_depth")
        self.assertEqual(export_views(state)["argus"]["depth"], {})

    def test_database_triggers_block_prediction_and_event_rewrite(self):
        install(self.store)
        with closing(sqlite3.connect(self.store.path)) as db:
            with self.assertRaises(sqlite3.DatabaseError):
                db.execute("DELETE FROM events")
            with self.assertRaises(sqlite3.DatabaseError):
                db.execute("UPDATE predictions SET body='{}'")

    def test_confirmed_pivots_appear_only_after_right_bars(self):
        self.source()
        highs = [2, 3, 8, 4, 3]
        for i, high in enumerate(highs):
            self.store.append(self.event(name=f"p{i}", event_ns=10+i*10, available_ns=11+i*10,
                                         payload={"open": 1, "high": high, "low": 0, "close": 1}))
        self.assertEqual(frame(self.store, 41)["atlas"]["terrain"][0]["confirmed_pivots"], [])
        pivot = frame(self.store, 51)["atlas"]["terrain"][0]["confirmed_pivots"][0]
        self.assertEqual(pivot["price"], 8)
        self.assertEqual(pivot["confirmed_ns"], 51)
        self.assertEqual(pivot["evidence_tier"], Tier.CANDLE_PROXY)

    def test_true_depth_source_needs_declared_provenance(self):
        with self.assertRaisesRegex(ValueError, "provider, license"):
            SourceSpec("unknown", "book:l2", "NQ", ("book_snapshot",), Tier.TRUE_DEPTH,
                       hashlib.sha256(b"source").hexdigest())

    def test_http_cockpit_hides_unsettled_future(self):
        install(self.store)
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(self.store))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_port}"
        before = START + 232 * SECOND
        with urlopen(base + "/api/predictions?at=" + str(before)) as response:
            prediction = json.load(response)
        self.assertEqual(len(prediction), 1)
        self.assertIsNone(prediction[0]["settlement"])
        with urlopen(base + "/api/predictions?at=" + str(START + 361 * SECOND)) as response:
            settled = json.load(response)
        self.assertEqual(settled[0]["settlement"]["realized_move"], 10.0)
        with urlopen(base) as response:
            self.assertIn(b"THE MARKET REMEMBERS", response.read())
        with self.assertRaises(HTTPError) as blocked:
            urlopen(Request(base + "/api/evidence?at=" + str(before), headers={"Host": "attacker.example"}))
        self.assertEqual(blocked.exception.code, 403)
        with urlopen(base + "/api/frame?at=" + str(before) + "&scenario=source_blackout") as response:
            branch = json.load(response)
        self.assertTrue(branch["frame"]["synthetic"])
        self.assertTrue(branch["actual_frame"]["synthetic"])
        self.assertIsNone(branch["actual_frame"]["scenario"])
        self.assertEqual(branch["frame"]["books"], {})
        self.assertFalse(branch["comparison"]["empirical_counterfactual_fill"])


if __name__ == "__main__":
    unittest.main()
