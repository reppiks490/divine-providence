import tempfile
from pathlib import Path

import pytest

from scripts.durable_execution_store import (
    DurableTransitionError,
    SQLiteDurableRunStore,
    VersionConflict,
)
from scripts.execution_domain_kernel import LeaseConflict, StaleFence


def make_store(tmp_path: Path):
    return SQLiteDurableRunStore(tmp_path / "runs.sqlite3")


def test_restart_preserves_fence_checkpoint_and_takeover_blocks_stale_worker(tmp_path):
    store1 = make_store(tmp_path)
    lease1 = store1.acquire("run-1", "worker-a", now_ms=1000, ttl_ms=100)
    cp = store1.checkpoint(
        "run-1", "worker-a", lease1["fencing_token"], {"phase": "alpha", "secret": "never-store-me"},
        now_ms=1050, state_ref="blob://opaque/state-1",
    )
    assert cp["state_hash"].startswith("sha256:")
    assert "never-store-me" not in repr(cp)

    # Simulate a process restart by constructing a fresh store instance.
    store2 = make_store(tmp_path)
    recovered = store2.get_run("run-1")
    assert recovered["checkpoint_id"] == cp["checkpoint_id"]
    assert recovered["fencing_token"] == 1

    lease2 = store2.acquire("run-1", "worker-b", now_ms=1100, ttl_ms=100)
    assert lease2["fencing_token"] == 2
    assert lease2["attempt"] == 2

    with pytest.raises(StaleFence):
        store1.checkpoint("run-1", "worker-a", 1, {"phase": "late"}, now_ms=1110)

    cp2 = store2.checkpoint("run-1", "worker-b", 2, {"phase": "beta"}, now_ms=1120)
    assert cp2["fencing_token"] == 2


def test_active_lease_conflict_is_shared_across_store_instances(tmp_path):
    a = make_store(tmp_path)
    b = make_store(tmp_path)
    a.acquire("run-lock", "worker-a", now_ms=1000, ttl_ms=1000)
    with pytest.raises(LeaseConflict):
        b.acquire("run-lock", "worker-b", now_ms=1500, ttl_ms=1000)


def test_suspend_resume_is_durable_and_resume_key_is_idempotent(tmp_path):
    store = make_store(tmp_path)
    lease = store.acquire("run-s", "worker-a", now_ms=1000, ttl_ms=1000)
    suspended = store.suspend(
        "run-s", "worker-a", lease["fencing_token"],
        pending_approval_ids=["approval-2", "approval-1", "approval-1"], now_ms=1100,
    )
    assert suspended["status"] == "suspended"
    assert suspended["pending_approval_ids"] == ["approval-1", "approval-2"]

    reopened = make_store(tmp_path)
    first = reopened.resume("run-s", resume_key="resume-abc", now_ms=1200)
    second = reopened.resume("run-s", resume_key="resume-abc", now_ms=1300)
    assert first["status"] == "queued"
    assert second == first

    with pytest.raises(DurableTransitionError):
        reopened.resume("run-s", resume_key="different-key", now_ms=1400)

    lease2 = reopened.acquire("run-s", "worker-b", now_ms=1500, ttl_ms=1000)
    assert lease2["fencing_token"] == 2


def test_cancel_uses_version_cas_and_fences_current_worker(tmp_path):
    store = make_store(tmp_path)
    lease = store.acquire("run-c", "worker-a", now_ms=1000, ttl_ms=1000)
    before = store.get_run("run-c")

    with pytest.raises(VersionConflict):
        store.cancel("run-c", expected_version=before["version"] - 1, now_ms=1100, reason="operator")

    receipt = store.cancel("run-c", expected_version=before["version"], now_ms=1100, reason="operator")
    assert receipt["status"] == "cancelled"
    assert receipt["fencing_token"] == lease["fencing_token"] + 1

    with pytest.raises(StaleFence):
        store.checkpoint("run-c", "worker-a", lease["fencing_token"], {"late": True}, now_ms=1110)
    with pytest.raises(LeaseConflict):
        store.acquire("run-c", "worker-b", now_ms=2000, ttl_ms=100)


def test_mark_worker_lost_requires_expired_lease_and_survives_restart(tmp_path):
    store = make_store(tmp_path)
    store.acquire("run-lost", "worker-a", now_ms=1000, ttl_ms=100)
    with pytest.raises(DurableTransitionError):
        store.mark_worker_lost("run-lost", now_ms=1099)

    lost = store.mark_worker_lost("run-lost", now_ms=1100)
    assert lost["status"] == "worker_lost"
    assert lost["lease_worker"] is None

    reopened = make_store(tmp_path)
    lease2 = reopened.acquire("run-lost", "worker-b", now_ms=1200, ttl_ms=100)
    assert lease2["attempt"] == 2
    assert lease2["fencing_token"] == 2


def test_checkpoint_table_stores_receipt_not_raw_state(tmp_path):
    store = make_store(tmp_path)
    lease = store.acquire("run-p", "worker-a", now_ms=1000, ttl_ms=1000)
    cp = store.checkpoint("run-p", "worker-a", lease["fencing_token"], {"private": "TOP-SECRET"}, now_ms=1100)
    raw = (tmp_path / "runs.sqlite3").read_bytes()
    assert b"TOP-SECRET" not in raw
    assert store.get_checkpoint(cp["checkpoint_id"])["state_hash"] == cp["state_hash"]
