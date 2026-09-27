import hashlib
import importlib
import importlib.util
import inspect
import json

import pytest

from scripts.witnessed_transparency import Witness, WitnessError, RFC9162WitnessedCheckpointLedger, _canon
from scripts.witness_policy_epoch import (
    WitnessPolicyEpoch,
    DurableWitnessPolicyRoot,
    EpochWitnessRegistry,
    policy_rotation_signature,
)
from scripts.durable_gossip_journal import DurableGossipJournal


def _tt_api():
    assert importlib.util.find_spec("scripts.trusted_time") is not None
    mod = importlib.import_module("scripts.trusted_time")
    for name in ("TrustedTimeSample", "DurableTrustedTimeFloor", "TrustedTimeGuard"):
        assert getattr(mod, name, None) is not None, f"missing trusted-time API: {name}"
    return mod.TrustedTimeSample, mod.DurableTrustedTimeFloor, mod.TrustedTimeGuard


class MutableSource:
    def __init__(self, sample):
        self.current = sample
        self.calls = 0

    def sample(self):
        self.calls += 1
        return self.current


def _expiring_policy(epoch, witnesses, threshold, expires_unix):
    assert "expires_unix" in inspect.signature(WitnessPolicyEpoch).parameters
    return WitnessPolicyEpoch(
        epoch,
        {w.witness_id: w.public_key_bytes() for w in witnesses},
        threshold,
        expires_unix=expires_unix,
    )


def _guard(tmp_path, sample, *, max_uncertainty=30, minimum_lower_bound=None):
    TrustedTimeSample, DurableTrustedTimeFloor, TrustedTimeGuard = _tt_api()
    source = MutableSource(sample)
    floor = DurableTrustedTimeFloor(tmp_path / "trusted-time-floor.json")
    guard = TrustedTimeGuard(
        source,
        floor=floor,
        max_uncertainty_seconds=max_uncertainty,
        minimum_lower_bound_unix=minimum_lower_bound,
    )
    return source, floor, guard


def test_trusted_time_module_is_available():
    _tt_api()


def test_expiring_policy_serialization_is_additive_and_legacy_digest_stays_stable():
    TrustedTimeSample, _, _ = _tt_api()
    a = Witness.generate("a")
    legacy = WitnessPolicyEpoch(1, {"a": a.public_key_bytes()}, 1)
    public = legacy.to_public_dict()
    assert "expires_unix" not in public
    expected = "sha256:" + hashlib.sha256(_canon(public)).hexdigest()
    assert legacy.digest() == expected

    expiring = _expiring_policy(2, [a], 1, 2_000)
    assert expiring.to_public_dict()["expires_unix"] == 2_000
    assert WitnessPolicyEpoch.from_public_dict(expiring.to_public_dict()).digest() == expiring.digest()
    with pytest.raises(WitnessError, match="expiration"):
        WitnessPolicyEpoch(3, {"a": a.public_key_bytes()}, 1, expires_unix=0)
    with pytest.raises(WitnessError, match="trusted time"):
        TrustedTimeSample(unix_seconds=-1, uncertainty_seconds=0, source="x")


def test_uncertainty_overlap_with_policy_expiry_fails_closed(tmp_path):
    TrustedTimeSample, _, _ = _tt_api()
    a = Witness.generate("a")
    policy = _expiring_policy(1, [a], 1, 1_000)
    _, _, guard = _guard(
        tmp_path,
        TrustedTimeSample(unix_seconds=995, uncertainty_seconds=10, source="test"),
        max_uncertainty=20,
    )
    with pytest.raises(WitnessError, match="expiry boundary"):
        guard.assert_policy_fresh(policy)


def test_durable_time_floor_rejects_rollback_and_external_floor(tmp_path):
    TrustedTimeSample, DurableTrustedTimeFloor, TrustedTimeGuard = _tt_api()
    a = Witness.generate("a")
    policy = _expiring_policy(1, [a], 1, 2_000)
    source, floor, guard = _guard(
        tmp_path,
        TrustedTimeSample(unix_seconds=1_000, uncertainty_seconds=1, source="tsa:test", evidence_digest="sha256:abc"),
        max_uncertainty=5,
    )
    report = guard.assert_policy_fresh(policy)
    assert report["lower_bound_unix"] == 999
    assert report["upper_bound_unix"] == 1001
    assert report["policy_expires_unix"] == 2000
    assert floor.path.exists()

    source.current = TrustedTimeSample(unix_seconds=998, uncertainty_seconds=0, source="tsa:test")
    with pytest.raises(WitnessError, match="rollback"):
        guard.assert_policy_fresh(policy)

    reloaded = DurableTrustedTimeFloor(floor.path)
    strict = TrustedTimeGuard(
        MutableSource(TrustedTimeSample(unix_seconds=1_000, uncertainty_seconds=0, source="tsa:test")),
        floor=reloaded,
        minimum_lower_bound_unix=1_100,
    )
    with pytest.raises(WitnessError, match="external minimum"):
        strict.assert_policy_fresh(policy)


def test_expiring_policy_requires_time_guard_for_bootstrap_and_active_checkpoint(tmp_path):
    TrustedTimeSample, _, TrustedTimeGuard = _tt_api()
    a, b = Witness.generate("a"), Witness.generate("b")
    policy = _expiring_policy(1, [a, b], 2, 2_000)
    assert "trusted_time_guard" in inspect.signature(DurableWitnessPolicyRoot.bootstrap).parameters
    with pytest.raises(WitnessError, match="trusted time guard required"):
        DurableWitnessPolicyRoot.bootstrap(tmp_path / "bad-policy.json", policy)

    source, floor, guard = _guard(
        tmp_path,
        TrustedTimeSample(unix_seconds=1_000, uncertainty_seconds=0, source="test"),
    )
    root = DurableWitnessPolicyRoot.bootstrap(tmp_path / "policy.json", policy, trusted_time_guard=guard)
    assert "trusted_time_guard" in inspect.signature(EpochWitnessRegistry).parameters
    registry_without_time = EpochWitnessRegistry(root)
    ledger_without_time = RFC9162WitnessedCheckpointLedger(registry_without_time, "log-A")
    with pytest.raises(WitnessError, match="trusted time guard required"):
        ledger_without_time.checkpoint([b"x"], [a, b])

    registry = EpochWitnessRegistry(root, trusted_time_guard=guard)
    ledger = RFC9162WitnessedCheckpointLedger(registry, "log-A")
    cp = ledger.checkpoint([b"x"], [a, b])
    assert cp["policy_epoch"] == 1


def test_historical_signature_verification_survives_expiry_but_new_checkpoint_does_not(tmp_path):
    TrustedTimeSample, _, _ = _tt_api()
    a, b = Witness.generate("a"), Witness.generate("b")
    policy = _expiring_policy(1, [a, b], 2, 2_000)
    source, _, guard = _guard(
        tmp_path,
        TrustedTimeSample(unix_seconds=1_000, uncertainty_seconds=0, source="test"),
    )
    root = DurableWitnessPolicyRoot.bootstrap(tmp_path / "policy.json", policy, trusted_time_guard=guard)
    registry = EpochWitnessRegistry(root, trusted_time_guard=guard)
    ledger = RFC9162WitnessedCheckpointLedger(registry, "log-A")
    cp = ledger.checkpoint([b"x"], [a, b])
    statement = {
        k: cp[k]
        for k in (
            "schema", "log_id", "tree_algorithm", "tree_size", "root",
            "previous_tree_size", "previous_root", "consistency_digest",
            "policy_epoch", "policy_digest",
        )
    }

    source.current = TrustedTimeSample(unix_seconds=2_001, uncertainty_seconds=0, source="test")
    assert registry.verify("a", statement, cp["receipts"][0]["signature"])
    with pytest.raises(WitnessError, match="expired"):
        ledger.checkpoint([b"x", b"y"], [a, b])


def test_rotation_samples_time_once_and_rejects_expired_next_policy(tmp_path):
    TrustedTimeSample, _, _ = _tt_api()
    a, b, c = Witness.generate("a"), Witness.generate("b"), Witness.generate("c")
    source, _, guard = _guard(
        tmp_path,
        TrustedTimeSample(unix_seconds=1_000, uncertainty_seconds=0, source="test"),
    )
    p1 = _expiring_policy(1, [a, b], 2, 2_000)
    root = DurableWitnessPolicyRoot.bootstrap(tmp_path / "policy.json", p1, trusted_time_guard=guard)
    source.calls = 0
    p2 = _expiring_policy(2, [b, c], 2, 900)
    statement = root.make_rotation_statement(p2)
    signatures = [policy_rotation_signature(w, statement) for w in (a, b, c)]
    assert "trusted_time_guard" in inspect.signature(root.rotate).parameters
    with pytest.raises(WitnessError, match="expired"):
        root.rotate(p2, signatures, trusted_time_guard=guard)
    assert source.calls == 1
    assert root.policy.epoch == 1


def test_compaction_binds_fixed_trusted_time_and_load_rechecks_current_freshness(tmp_path):
    TrustedTimeSample, _, _ = _tt_api()
    a, b = Witness.generate("a"), Witness.generate("b")
    source, _, guard = _guard(
        tmp_path,
        TrustedTimeSample(unix_seconds=1_000, uncertainty_seconds=0, source="tsa:test", evidence_digest="sha256:evidence"),
    )
    policy = _expiring_policy(1, [a, b], 2, 2_000)
    root = DurableWitnessPolicyRoot.bootstrap(tmp_path / "policy.json", policy, trusted_time_guard=guard)
    registry = EpochWitnessRegistry(root, trusted_time_guard=guard)
    ledger = RFC9162WitnessedCheckpointLedger(registry, "log-A")
    journal = DurableGossipJournal(tmp_path / "gossip.jsonl", registry)
    journal.append(ledger.checkpoint([b"x"], [a, b]))
    snapshot = tmp_path / "snapshot.json"
    anchors = tmp_path / "anchors.jsonl"
    journal.compact(snapshot, anchors, [a, b])
    env = json.loads(snapshot.read_text())
    trusted_time = env["statement"].get("trusted_time")
    assert trusted_time is not None
    assert trusted_time["source"] == "tsa:test"
    assert trusted_time["lower_bound_unix"] == 1_000
    assert trusted_time["upper_bound_unix"] == 1_000
    assert trusted_time["policy_expires_unix"] == 2_000

    # Historical full replay is forensic and remains valid after policy expiry.
    source.current = TrustedTimeSample(unix_seconds=2_001, uncertainty_seconds=0, source="tsa:test")
    historical = DurableGossipJournal.load(tmp_path / "gossip.jsonl", registry)
    assert historical.sequence == 1
    with pytest.raises(WitnessError, match="expired"):
        DurableGossipJournal.load_compacted(
            tmp_path / "gossip.jsonl", snapshot, anchors, registry
        )


def test_active_journal_append_rejects_expired_current_policy(tmp_path):
    TrustedTimeSample, _, _ = _tt_api()
    a, b = Witness.generate("a"), Witness.generate("b")
    source, _, guard = _guard(
        tmp_path,
        TrustedTimeSample(unix_seconds=1_000, uncertainty_seconds=0, source="test"),
    )
    policy = _expiring_policy(1, [a, b], 2, 2_000)
    root = DurableWitnessPolicyRoot.bootstrap(tmp_path / "policy.json", policy, trusted_time_guard=guard)
    registry = EpochWitnessRegistry(root, trusted_time_guard=guard)
    ledger = RFC9162WitnessedCheckpointLedger(registry, "log-A")
    checkpoint = ledger.checkpoint([b"x"], [a, b])

    # The evidence remains historically authentic, but accepting it into a new
    # active journal after policy expiry is an active trust decision and fails.
    source.current = TrustedTimeSample(unix_seconds=2_001, uncertainty_seconds=0, source="test")
    journal = DurableGossipJournal(tmp_path / "late.jsonl", registry)
    with pytest.raises(WitnessError, match="expired"):
        journal.append(checkpoint)
    assert not (tmp_path / "late.jsonl").exists()


def test_trusted_time_floor_refuses_when_update_lock_exists(tmp_path):
    TrustedTimeSample, DurableTrustedTimeFloor, _ = _tt_api()
    path = tmp_path / "trusted-time-floor.json"
    floor = DurableTrustedTimeFloor(path)
    lock = path.with_name(path.name + ".update.lock")
    lock.write_text("other-writer")
    with pytest.raises(WitnessError, match="update already in progress"):
        floor.accept(TrustedTimeSample(1_000, 0, "test"))
    assert not path.exists()


def test_trusted_time_floor_reloads_disk_state_before_monotonic_compare(tmp_path):
    TrustedTimeSample, DurableTrustedTimeFloor, _ = _tt_api()
    path = tmp_path / "trusted-time-floor.json"
    writer_a = DurableTrustedTimeFloor(path)
    writer_a.accept(TrustedTimeSample(1_000, 0, "test"))
    writer_b = DurableTrustedTimeFloor(path)  # caches floor=1000
    writer_a.accept(TrustedTimeSample(1_100, 0, "test"))

    # A stale process must not overwrite the newer durable floor with 1050.
    with pytest.raises(WitnessError, match="rollback"):
        writer_b.accept(TrustedTimeSample(1_050, 0, "test"))
    assert DurableTrustedTimeFloor(path).lower_bound_unix == 1_100


def test_trusted_time_and_expiry_reject_fractional_or_string_seconds():
    TrustedTimeSample, _, _ = _tt_api()
    a = Witness.generate("a")
    for value in (1000.5, "1000"):
        with pytest.raises(WitnessError, match="integer"):
            TrustedTimeSample(unix_seconds=value, uncertainty_seconds=0, source="test")
        with pytest.raises(WitnessError, match="integer"):
            TrustedTimeSample(unix_seconds=1000, uncertainty_seconds=value, source="test")
        with pytest.raises(WitnessError, match="integer"):
            WitnessPolicyEpoch(1, {"a": a.public_key_bytes()}, 1, expires_unix=value)
