import pytest

from scripts.isolation_admission import AdmissionDenied, SQLiteIsolationAdmission


CAPACITY = {
    "cpu_millis": 8000,
    "memory_mb": 32768,
    "storage_mb": 100000,
    "gpu_units": 4,
    "model_tokens": 1000000,
    "provider_calls": 10000,
    "concurrent_tasks": 64,
}

ALLOWED = {
    "filesystem.read",
    "terminal.sandbox",
    "network.public_read",
    "provider.read",
    "gpu.compute",
}


def controller(tmp_path):
    return SQLiteIsolationAdmission(tmp_path / "admission.sqlite3", capacity=CAPACITY, admissible_capabilities=ALLOWED)


def manifest(granted):
    return {"requested": sorted(set(granted)), "granted": sorted(set(granted))}


def test_durable_admission_reserves_capacity_and_is_idempotent(tmp_path):
    c1 = controller(tmp_path)
    req = {"cpu_millis": 2000, "memory_mb": 4096, "gpu_units": 1, "concurrent_tasks": 8}
    first = c1.admit("run-a", resources=req, authority_manifest=manifest(["terminal.sandbox", "gpu.compute"]), credential_refs=["secretref://broker/read-only"], now_ms=1000)
    second = c1.admit("run-a", resources=req, authority_manifest=manifest(["terminal.sandbox", "gpu.compute"]), credential_refs=["secretref://broker/read-only"], now_ms=1200)
    assert first == second
    assert first["status"] == "admitted"
    assert first["credential_ref_count"] == 1
    assert "broker/read-only" not in repr(first)

    c2 = controller(tmp_path)
    available = c2.available()
    assert available["cpu_millis"] == 6000
    assert available["gpu_units"] == 3


def test_capacity_is_shared_and_overcommit_fails_closed(tmp_path):
    a = controller(tmp_path)
    b = controller(tmp_path)
    a.admit("run-a", resources={"cpu_millis": 7000, "memory_mb": 1000}, authority_manifest=manifest(["terminal.sandbox"]), now_ms=1)
    with pytest.raises(AdmissionDenied):
        b.admit("run-b", resources={"cpu_millis": 2000}, authority_manifest=manifest(["terminal.sandbox"]), now_ms=2)


def test_unbudgeted_resources_and_negative_values_are_rejected(tmp_path):
    c = controller(tmp_path)
    with pytest.raises(AdmissionDenied):
        c.admit("x", resources={"unknown_resource": 1}, authority_manifest=manifest(["terminal.sandbox"]), now_ms=1)
    with pytest.raises(AdmissionDenied):
        c.admit("y", resources={"cpu_millis": -1}, authority_manifest=manifest(["terminal.sandbox"]), now_ms=1)


def test_capability_allowlist_blocks_host_and_broker_execution(tmp_path):
    c = controller(tmp_path)
    with pytest.raises(AdmissionDenied):
        c.admit("broker", resources={"cpu_millis": 1}, authority_manifest=manifest(["broker.orders"]), now_ms=1)
    with pytest.raises(AdmissionDenied):
        c.admit("host", resources={"cpu_millis": 1}, authority_manifest=manifest(["filesystem.host_write"]), now_ms=1)


def test_raw_or_ambiguous_credentials_are_rejected(tmp_path):
    c = controller(tmp_path)
    with pytest.raises(AdmissionDenied):
        c.admit("raw", resources={"cpu_millis": 1}, authority_manifest=manifest(["terminal.sandbox"]), credential_refs=["sk-live-secret"], now_ms=1)
    with pytest.raises(AdmissionDenied):
        c.admit("empty", resources={"cpu_millis": 1}, authority_manifest=manifest(["terminal.sandbox"]), credential_refs=["secretref://"], now_ms=1)


def test_release_restores_capacity_and_is_idempotent(tmp_path):
    c = controller(tmp_path)
    c.admit("run-a", resources={"cpu_millis": 5000, "provider_calls": 300}, authority_manifest=manifest(["provider.read"]), now_ms=1)
    released = c.release("run-a", now_ms=2)
    assert released["released"] is True
    assert c.available()["cpu_millis"] == CAPACITY["cpu_millis"]
    assert c.release("run-a", now_ms=3)["released"] is False


def test_same_run_with_changed_request_is_not_silently_mutated(tmp_path):
    c = controller(tmp_path)
    c.admit("run-a", resources={"cpu_millis": 1000}, authority_manifest=manifest(["terminal.sandbox"]), now_ms=1)
    with pytest.raises(AdmissionDenied):
        c.admit("run-a", resources={"cpu_millis": 2000}, authority_manifest=manifest(["terminal.sandbox"]), now_ms=2)
