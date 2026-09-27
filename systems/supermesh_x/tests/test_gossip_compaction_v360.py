import json
import shutil

import pytest

from scripts.witnessed_transparency import Witness, WitnessError, RFC9162WitnessedCheckpointLedger
from scripts.witness_policy_epoch import WitnessPolicyEpoch, DurableWitnessPolicyRoot, EpochWitnessRegistry
from scripts.durable_gossip_journal import DurableGossipJournal


def setup(tmp_path):
    a, b = Witness.generate("a"), Witness.generate("b")
    policy = WitnessPolicyEpoch(1, {w.witness_id: w.public_key_bytes() for w in (a, b)}, 2)
    root = DurableWitnessPolicyRoot.bootstrap(tmp_path / "policy.json", policy)
    registry = EpochWitnessRegistry(root)
    ledger = RFC9162WitnessedCheckpointLedger(registry, "log-A")
    journal = DurableGossipJournal(tmp_path / "gossip.jsonl", registry)
    return a, b, registry, ledger, journal


def test_signed_compaction_replays_only_suffix_and_continues_chain(tmp_path):
    a, b, registry, ledger, journal = setup(tmp_path)
    journal.append(ledger.checkpoint([b"a"], [a, b]))
    snapshot = tmp_path / "snapshot-1.json"
    anchors = tmp_path / "anchors.jsonl"

    report = journal.compact(snapshot, anchors, [a, b])
    assert report["snapshot_epoch"] == 1
    assert report["journal_sequence"] == 1
    assert report["journal_prefix_bytes"] == (tmp_path / "gossip.jsonl").stat().st_size

    journal.append(ledger.checkpoint([b"a", b"b"], [a, b]))
    restored = DurableGossipJournal.load_compacted(
        tmp_path / "gossip.jsonl", snapshot, anchors, registry
    )
    assert restored.sequence == 2
    assert restored.latest("log-A")["tree_size"] == 2
    assert restored.compaction_report["snapshot_epoch"] == 1

    journal3 = ledger.checkpoint([b"a", b"b", b"c"], [a, b])
    restored.append(journal3)
    restored2 = DurableGossipJournal.load_compacted(
        tmp_path / "gossip.jsonl", snapshot, anchors, registry
    )
    assert restored2.sequence == 3
    assert restored2.latest("log-A")["tree_size"] == 3


def test_compaction_snapshot_tamper_and_journal_prefix_rewrite_fail_closed(tmp_path):
    a, b, registry, ledger, journal = setup(tmp_path)
    journal.append(ledger.checkpoint([b"a"], [a, b]))
    snapshot = tmp_path / "snapshot-1.json"
    anchors = tmp_path / "anchors.jsonl"
    journal.compact(snapshot, anchors, [a, b])

    original = snapshot.read_text()
    env = json.loads(original)
    env["statement"]["journal_sequence"] = 0
    snapshot.write_text(json.dumps(env))
    with pytest.raises(WitnessError):
        DurableGossipJournal.load_compacted(tmp_path / "gossip.jsonl", snapshot, anchors, registry)

    snapshot.write_text(original)
    journal_path = tmp_path / "gossip.jsonl"
    raw = bytearray(journal_path.read_bytes())
    raw[0] ^= 1
    journal_path.write_bytes(bytes(raw))
    with pytest.raises(WitnessError, match="prefix"):
        DurableGossipJournal.load_compacted(journal_path, snapshot, anchors, registry)


def test_latest_anchor_rejects_older_snapshot_and_external_epoch_pin_survives_anchor_rollback(tmp_path):
    a, b, registry, ledger, journal = setup(tmp_path)
    path = tmp_path / "gossip.jsonl"
    anchors = tmp_path / "anchors.jsonl"
    snapshot1 = tmp_path / "snapshot-1.json"
    snapshot2 = tmp_path / "snapshot-2.json"

    journal.append(ledger.checkpoint([b"a"], [a, b]))
    r1 = journal.compact(snapshot1, anchors, [a, b])
    anchors_epoch1 = tmp_path / "anchors-epoch1.jsonl"
    shutil.copyfile(anchors, anchors_epoch1)

    journal.append(ledger.checkpoint([b"a", b"b"], [a, b]))
    r2 = journal.compact(snapshot2, anchors, [a, b])
    assert r2["snapshot_epoch"] == 2

    with pytest.raises(WitnessError, match="latest anchored"):
        DurableGossipJournal.load_compacted(path, snapshot1, anchors, registry)

    with pytest.raises(WitnessError, match="minimum snapshot epoch"):
        DurableGossipJournal.load_compacted(
            path,
            snapshot1,
            anchors_epoch1,
            registry,
            minimum_snapshot_epoch=2,
        )

    restored = DurableGossipJournal.load_compacted(
        path,
        snapshot2,
        anchors,
        registry,
        minimum_snapshot_epoch=2,
        expected_anchor_digest=r2["anchor_digest"],
    )
    assert restored.sequence == 2
    assert restored.latest("log-A")["tree_size"] == 2
    assert r1["anchor_digest"] != r2["anchor_digest"]


def test_failed_anchor_commit_does_not_displace_previous_good_compaction(tmp_path, monkeypatch):
    a, b, registry, ledger, journal = setup(tmp_path)
    path = tmp_path / "gossip.jsonl"
    anchors = tmp_path / "anchors.jsonl"
    snapshot1 = tmp_path / "snapshot-1.json"
    snapshot2 = tmp_path / "snapshot-2.json"

    journal.append(ledger.checkpoint([b"a"], [a, b]))
    r1 = journal.compact(snapshot1, anchors, [a, b])
    anchor_before = anchors.read_bytes()

    journal.append(ledger.checkpoint([b"a", b"b"], [a, b]))

    def fail_anchor(*args, **kwargs):
        raise OSError("simulated anchor disk failure")

    monkeypatch.setattr(DurableGossipJournal, "_append_anchor_envelope", staticmethod(fail_anchor))
    with pytest.raises(WitnessError, match="anchor persistence failed"):
        journal.compact(snapshot2, anchors, [a, b])

    assert anchors.read_bytes() == anchor_before
    assert snapshot1.exists()
    assert snapshot2.exists()  # orphaned but never committed by the anchor journal
    restored = DurableGossipJournal.load_compacted(
        path,
        snapshot1,
        anchors,
        registry,
        expected_anchor_digest=r1["anchor_digest"],
    )
    assert restored.latest("log-A")["tree_size"] == 2


def test_compaction_refuses_snapshot_overwrite_and_requires_quorum(tmp_path):
    a, b, registry, ledger, journal = setup(tmp_path)
    journal.append(ledger.checkpoint([b"a"], [a, b]))
    snapshot = tmp_path / "snapshot-1.json"
    anchors = tmp_path / "anchors.jsonl"

    with pytest.raises(WitnessError, match="quorum"):
        journal.compact(snapshot, anchors, [a])
    assert not snapshot.exists()
    assert not anchors.exists()

    journal.compact(snapshot, anchors, [a, b])
    with pytest.raises(WitnessError, match="already exists"):
        journal.compact(snapshot, anchors, [a, b])


def test_compaction_refuses_when_exclusive_anchor_lock_exists(tmp_path):
    a, b, registry, ledger, journal = setup(tmp_path)
    journal.append(ledger.checkpoint([b"a"], [a, b]))
    snapshot = tmp_path / "snapshot-1.json"
    anchors = tmp_path / "anchors.jsonl"
    lock = tmp_path / "anchors.jsonl.compaction.lock"
    lock.write_text("other-writer")

    with pytest.raises(WitnessError, match="compaction already in progress"):
        journal.compact(snapshot, anchors, [a, b])
    assert not snapshot.exists()
    assert not anchors.exists()


def test_anchor_commit_rejects_stale_previous_digest_without_modifying_chain(tmp_path):
    a, b, registry, ledger, journal = setup(tmp_path)
    journal.append(ledger.checkpoint([b"a"], [a, b]))
    snapshot = tmp_path / "snapshot-1.json"
    anchors = tmp_path / "anchors.jsonl"
    journal.compact(snapshot, anchors, [a, b])
    before = anchors.read_bytes()

    stale_statement = {
        "schema": 1,
        "kind": "gossip-compaction-anchor",
        "snapshot_epoch": 2,
        "previous_anchor_digest": "00" * 32,
        "snapshot_digest": "11" * 32,
        "journal_sequence": 2,
        "journal_last_digest": "22" * 32,
        "journal_prefix_bytes": len((tmp_path / "gossip.jsonl").read_bytes()),
        "journal_prefix_sha256": "33" * 32,
        "policy_epoch": registry.policy_epoch,
        "policy_digest": registry.policy_digest,
    }
    from scripts.durable_gossip_journal import _entry_digest
    envelope = {"statement": stale_statement, "signatures": [], "entry_digest": _entry_digest(stale_statement)}

    with pytest.raises(WitnessError, match="changed during commit"):
        DurableGossipJournal._append_anchor_envelope(anchors, envelope)
    assert anchors.read_bytes() == before
