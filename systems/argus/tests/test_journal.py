import json
import sqlite3
from contextlib import closing

import pytest

from argus.contracts import EvidenceTier, MicrostructureFeature
from argus.evidence_bridge import EvidenceCapability, aion_tier_name, feature_export, reject_numeric_external_tier
from argus.journal import EventJournal, JournalEvent, SourceContract


def depth_contract():
    return SourceContract(
        source_id="depth",
        max_evidence_tier=EvidenceTier.TRUE_DEPTH,
        sequence_policy="contiguous",
        provider_reference="unit-test-provider",
        capability_reference="unit-test-depth",
        allowed_kinds=("book_snapshot", "book_delta"),
        identity_verified=True,
        source_identity_reference="unit-test-provider-contract:v1",
    )


def register_depth(journal):
    journal.register(depth_contract())


def snapshot(seq, received, *, flags=()):
    return JournalEvent(
        source_id="depth",
        kind="book_snapshot",
        event_time_ns=received - 1,
        received_time_ns=received,
        sequence=seq,
        evidence_tier=EvidenceTier.TRUE_DEPTH,
        payload={"bids": [[99.0, 5.0]], "asks": [[100.0, 4.0]]},
        quality_flags=flags,
    )


def delta(seq, received, size):
    return JournalEvent(
        source_id="depth",
        kind="book_delta",
        event_time_ns=received - 1,
        received_time_ns=received,
        sequence=seq,
        evidence_tier=EvidenceTier.TRUE_DEPTH,
        payload={"side": "bid", "action": "set", "price": 99.0, "size": size},
    )


def test_receipt_time_replay_gap_invalidation_and_recovery(tmp_path):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    register_depth(journal)
    journal.append(snapshot(1, 11))
    journal.append(delta(2, 12, 7.0))

    before = journal.replay_book("depth", 12)
    assert before["status"] == "true_depth"
    assert before["bid_depth"] == 7.0
    assert before["sequence"] == 2

    gap = journal.append(delta(4, 13, 8.0))
    assert gap["gap_before"] == 1
    assert journal.replay_book("depth", 13)["status"] == "sequence_gap"

    recovery = journal.append(snapshot(5, 15, flags=("provider_recovery",)))
    assert recovery["gap_before"] == 0
    after = journal.replay_book("depth", 15)
    assert after["status"] == "true_depth"
    assert after["sequence"] == 5
    assert after["execution_authorized"] is False
    assert journal.replay_book("depth", 14)["status"] == "sequence_gap"


def test_gap_size_is_preserved_even_when_recovery_snapshot_skips_more_sequences(tmp_path):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    register_depth(journal)
    journal.append(snapshot(1, 11))
    recovered = journal.append(snapshot(5, 15, flags=("provider_recovery",)))
    assert recovered["gap_before"] == 3
    assert journal.replay_book("depth", 15)["status"] == "true_depth"
    assert journal.verify()["verified"] is True


def test_future_receipt_is_not_visible_to_earlier_replay(tmp_path):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    register_depth(journal)
    journal.append(snapshot(1, 20))
    assert journal.events_asof(19, source_id="depth") == []
    assert journal.replay_book("depth", 19)["status"] == "missing_snapshot"
    assert journal.replay_book("depth", 20)["status"] == "true_depth"


def test_raw_event_tiers_and_source_identity_fail_closed(tmp_path):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    unverified = SourceContract(
        source_id="trades",
        max_evidence_tier=EvidenceTier.TRUE_TRADE,
        sequence_policy="monotone",
        provider_reference="unit-test-provider",
        capability_reference="unit-test-trades",
        allowed_kinds=("trade",),
        identity_verified=False,
        source_identity_reference="not-yet-verified",
    )
    journal.register(unverified)
    with pytest.raises(ValueError, match="TRUE_TRADE"):
        JournalEvent(
            source_id="trades",
            kind="trade",
            event_time_ns=1,
            received_time_ns=2,
            sequence=1,
            evidence_tier=EvidenceTier.INFERRED_TRADE,
            payload={"price": 100, "size": 1, "side": "buy"},
        )

    trade = JournalEvent(
        source_id="trades",
        kind="trade",
        event_time_ns=1,
        received_time_ns=2,
        sequence=1,
        evidence_tier=EvidenceTier.TRUE_TRADE,
        payload={"price": 100, "size": 1, "side": "buy"},
    )
    with pytest.raises(ValueError, match="verified source identity"):
        journal.append(trade)


def test_source_capability_is_explicit_and_cannot_be_escalated(tmp_path):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    journal.register(SourceContract(
        source_id="trades",
        max_evidence_tier=EvidenceTier.TRUE_TRADE,
        sequence_policy="monotone",
        provider_reference="provider",
        capability_reference="authenticated prints only",
        allowed_kinds=("trade",),
        identity_verified=True,
        source_identity_reference="provider-contract:v1",
    ))
    with pytest.raises(ValueError, match="not authorized"):
        journal.append(JournalEvent(
            source_id="trades",
            kind="book_snapshot",
            event_time_ns=1,
            received_time_ns=2,
            sequence=1,
            evidence_tier=EvidenceTier.TRUE_DEPTH,
            payload={"bids": [[99, 1]], "asks": [[100, 1]]},
        ))


def test_duplicate_sequence_is_idempotent_even_after_later_rows_and_collision_fails(tmp_path):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    register_depth(journal)
    first = snapshot(1, 11)
    journal.append(first)
    journal.append(delta(2, 12, 7.0))
    duplicate = journal.append(first)
    assert duplicate["idempotent"] is True
    assert duplicate["position"] == 1
    with pytest.raises(ValueError, match="collision"):
        journal.append(JournalEvent(
            source_id="depth",
            kind="book_snapshot",
            event_time_ns=10,
            received_time_ns=11,
            sequence=1,
            evidence_tier=EvidenceTier.TRUE_DEPTH,
            payload={"bids": [[98.0, 5.0]], "asks": [[100.0, 4.0]]},
        ))


def test_backdated_receipt_or_event_time_cannot_rewrite_history(tmp_path):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    register_depth(journal)
    journal.append(snapshot(1, 20))
    with pytest.raises(ValueError, match="receipt time"):
        journal.append(JournalEvent(
            "depth", "book_delta", 18, 19, 2, EvidenceTier.TRUE_DEPTH,
            {"side": "bid", "action": "set", "price": 99.0, "size": 6.0},
        ))
    with pytest.raises(ValueError, match="event time"):
        journal.append(JournalEvent(
            "depth", "book_delta", 18, 21, 2, EvidenceTier.TRUE_DEPTH,
            {"side": "bid", "action": "set", "price": 99.0, "size": 6.0},
        ))


def test_hash_chain_detects_content_tamper(tmp_path):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    register_depth(journal)
    journal.append(snapshot(1, 11))
    assert journal.verify()["verified"] is True

    with closing(sqlite3.connect(journal.path)) as db, db:
        db.execute("DROP TRIGGER events_no_update")
        row = db.execute("SELECT body FROM events WHERE position=1").fetchone()
        body = json.loads(row[0])
        body["payload"]["bids"][0][1] = 999
        db.execute(
            "UPDATE events SET body=? WHERE position=1",
            (json.dumps(body, sort_keys=True, separators=(",", ":")),),
        )

    with pytest.raises(ValueError, match="tampered|canonical"):
        journal.verify()


def test_source_contract_is_immutable(tmp_path):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    register_depth(journal)
    register_depth(journal)
    with pytest.raises(ValueError, match="immutable"):
        journal.register(SourceContract(
            source_id="depth",
            max_evidence_tier=EvidenceTier.TRUE_DEPTH,
            sequence_policy="contiguous",
            provider_reference="other",
            capability_reference="other",
            allowed_kinds=("book_snapshot", "book_delta"),
            identity_verified=True,
            source_identity_reference="other:v2",
        ))


def test_named_capability_bridge_never_maps_by_integer():
    assert aion_tier_name(EvidenceCapability("candle", candle_only=True)) == "CANDLE_PROXY"
    assert aion_tier_name(EvidenceCapability("prints", authenticated_trade=True)) == "TRUE_TRADE"
    assert aion_tier_name(EvidenceCapability("mbp", authenticated_trade=True, market_by_price=True)) == "TRUE_DEPTH"
    with pytest.raises(ValueError, match="insufficient"):
        aion_tier_name(EvidenceCapability("unknown"))
    with pytest.raises(ValueError, match="numeric"):
        reject_numeric_external_tier(2)


def test_feature_export_preserves_tier_and_never_authorizes_execution():
    feature = MicrostructureFeature(
        name="imbalance",
        value=0.5,
        evidence_tier=EvidenceTier.CANDLE_PROXY,
        event_time_ns=10,
        source_id="csv",
        reason="unit-test",
    )
    packet = feature_export(feature)
    assert packet["argus_evidence_tier"] == "CANDLE_PROXY"
    assert packet["aion_evidence_tier_name"] == "CANDLE_PROXY"
    assert packet["execution_authorized"] is False
