"""Workspace and sandbox isolation contracts for SuperMesh-X v2.5.

This module is policy/receipt infrastructure only. It does not launch a VM,
container, browser computer, shell, agent, or secret-vault client. Its purpose is
to validate and serialize the boundaries that a future runtime must enforce.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from pathlib import PurePosixPath
from urllib.parse import urlparse


class WorkspacePolicyError(RuntimeError):
    pass


class NetworkPolicyError(RuntimeError):
    pass


class ExecutionSpecError(RuntimeError):
    pass


class VaultBrokerError(RuntimeError):
    pass


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _clean_rel_path(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkspacePolicyError(f"{field} must be a non-empty relative POSIX path")
    raw = value.strip().replace("\\", "/")
    path = PurePosixPath(raw)
    if path.is_absolute() or raw.startswith("/"):
        raise WorkspacePolicyError(f"{field} must not be absolute")
    if any(part in ("..", "") for part in path.parts):
        raise WorkspacePolicyError(f"{field} must not escape the workspace")
    normalized = str(path)
    if normalized in (".", ""):
        raise WorkspacePolicyError(f"{field} must name a workspace path")
    return normalized


_ALLOWED_SOURCE_SCHEMES = {
    "artifactref": {"ro"},
    "fileref": {"ro"},
    "workspace": {"ro", "rw"},
    "scratch": {"rw"},
    "artifactout": {"output"},
}


def _parse_source_ref(source_ref: str) -> tuple[str, str]:
    if not isinstance(source_ref, str) or "://" not in source_ref:
        raise WorkspacePolicyError("mount source_ref must be an opaque URI-like reference")
    scheme, rest = source_ref.split("://", 1)
    scheme = scheme.lower().strip()
    if scheme not in _ALLOWED_SOURCE_SCHEMES or not rest.strip():
        raise WorkspacePolicyError("host paths and unsupported mount source schemes are forbidden")
    if scheme == "file":
        raise WorkspacePolicyError("host filesystem mounts are forbidden")
    return scheme, rest


def build_mount_manifest(workspace_id: str, mounts: list[dict]) -> dict:
    if not isinstance(workspace_id, str) or not workspace_id.strip():
        raise WorkspacePolicyError("workspace_id is required")
    out = []
    targets = set()
    names = set()
    for mount in mounts or []:
        name = str(mount.get("name", "")).strip()
        if not name or name in names:
            raise WorkspacePolicyError("mount names must be unique and non-empty")
        mode = str(mount.get("mode", "")).strip().lower()
        source_ref = mount.get("source_ref")
        scheme, _ = _parse_source_ref(source_ref)
        if mode not in _ALLOWED_SOURCE_SCHEMES[scheme]:
            raise WorkspacePolicyError(f"mount mode {mode!r} is not allowed for {scheme}://")
        target = _clean_rel_path(mount.get("target", ""), field="mount target")
        if target in targets:
            raise WorkspacePolicyError("mount targets must be unique")
        targets.add(target)
        names.add(name)
        out.append({
            "name": name,
            "source_ref": source_ref,
            "target": target,
            "mode": mode,
        })
    return {
        "schema": 1,
        "workspace_id": workspace_id.strip(),
        "host_filesystem_visible": False,
        "root_read_only": True,
        "mounts": out,
        "manifest_digest": _digest({"workspace_id": workspace_id.strip(), "mounts": out}),
    }


def _normalize_host(host: str) -> str:
    return host.rstrip(".").lower()


def _host_is_internal(host: str) -> bool:
    host = _normalize_host(host)
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_unspecified
        or ip.is_reserved
    )


def build_network_policy(policy_class: str = "none", *, allow_hosts: list[str] | None = None) -> dict:
    policy_class = str(policy_class or "none").strip().lower()
    if policy_class not in {"none", "public_https", "provider_allowlist"}:
        raise NetworkPolicyError("unknown network-egress class")
    hosts = []
    for host in allow_hosts or []:
        h = _normalize_host(str(host).strip())
        if not h or "/" in h or "://" in h or _host_is_internal(h):
            raise NetworkPolicyError("allow_hosts must contain explicit public hostnames")
        hosts.append(h)
    hosts = sorted(set(hosts))
    if policy_class == "provider_allowlist" and not hosts:
        raise NetworkPolicyError("provider_allowlist requires at least one explicit host")
    if policy_class != "provider_allowlist" and hosts:
        raise NetworkPolicyError("allow_hosts are valid only for provider_allowlist")
    return {
        "schema": 1,
        "class": policy_class,
        "allow_hosts": hosts,
        "https_only": policy_class != "none",
        "deny_private_networks": True,
        "deny_link_local_metadata": True,
    }


def egress_allowed(policy: dict, url: str) -> bool:
    if not isinstance(policy, dict) or policy.get("class") == "none":
        return False
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return False
    host = _normalize_host(parsed.hostname)
    if _host_is_internal(host):
        return False
    if policy.get("class") == "public_https":
        return True
    if policy.get("class") == "provider_allowlist":
        return host in set(policy.get("allow_hosts", []))
    return False


_SECRET_KEY_RE = re.compile(r"(?:TOKEN|SECRET|PASSWORD|PASSWD|API[_-]?KEY|PRIVATE[_-]?KEY|CREDENTIAL|AUTHORIZATION)", re.I)


def _validate_env_key(key: str) -> str:
    key = str(key)
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
        raise ExecutionSpecError("environment variable names must be portable identifiers")
    return key


def build_execution_spec(*, argv, cwd: str, env: dict | None, secret_env: dict | None, timeout_ms: int, shell: bool = False) -> dict:
    if shell:
        raise ExecutionSpecError("shell execution is forbidden; provide an argv vector")
    if not isinstance(argv, (list, tuple)) or not argv or any(not isinstance(x, str) or not x for x in argv):
        raise ExecutionSpecError("argv must be a non-empty list of strings")
    timeout = int(timeout_ms)
    if timeout <= 0:
        raise ExecutionSpecError("timeout_ms must be positive")
    cwd_clean = _clean_rel_path(cwd, field="cwd")
    clean_env = {}
    for key, value in sorted((env or {}).items()):
        k = _validate_env_key(key)
        if _SECRET_KEY_RE.search(k):
            raise ExecutionSpecError("secret-like environment variables must use secret_env references")
        if not isinstance(value, str):
            raise ExecutionSpecError("environment values must be strings")
        clean_env[k] = value
    clean_secret_env = {}
    for key, value in sorted((secret_env or {}).items()):
        k = _validate_env_key(key)
        if not isinstance(value, str) or not value.startswith("secretref://") or not value[len("secretref://"):].strip():
            raise ExecutionSpecError("secret_env values must be non-empty secretref:// references")
        clean_secret_env[k] = value
    overlap = set(clean_env) & set(clean_secret_env)
    if overlap:
        raise ExecutionSpecError("an environment variable cannot be both public and secret")
    return {
        "schema": 1,
        "argv": list(argv),
        "cwd": cwd_clean,
        "env": clean_env,
        "secret_env": clean_secret_env,
        "timeout_ms": timeout,
        "shell": False,
    }


def build_execution_receipt(spec: dict, *, exit_code: int | None, started_at_ms: int, ended_at_ms: int, stdout_bytes: int = 0, stderr_bytes: int = 0, killed_reason: str | None = None) -> dict:
    start = int(started_at_ms)
    end = int(ended_at_ms)
    if end < start:
        raise ExecutionSpecError("ended_at_ms cannot precede started_at_ms")
    argv = spec.get("argv") or []
    # Digest the command vector but never persist raw arguments; CLI args often contain secrets.
    command_digest = _digest({"argv": argv})
    secret_ref_digest = _digest({"secret_refs": sorted((spec.get("secret_env") or {}).values())})
    return {
        "schema": 1,
        "executable": argv[0] if argv else None,
        "arg_count": len(argv),
        "command_digest": command_digest,
        "cwd": spec.get("cwd"),
        "env_keys": sorted((spec.get("env") or {}).keys()),
        "secret_env_keys": sorted((spec.get("secret_env") or {}).keys()),
        "secret_ref_digest": secret_ref_digest,
        "timeout_ms": int(spec.get("timeout_ms", 0)),
        "exit_code": None if exit_code is None else int(exit_code),
        "started_at_ms": start,
        "ended_at_ms": end,
        "duration_ms": end - start,
        "stdout_bytes": max(0, int(stdout_bytes)),
        "stderr_bytes": max(0, int(stderr_bytes)),
        "killed_reason": killed_reason,
    }


def build_runtime_enforcement(reservation: dict, *, requested_limits: dict | None, requested_capabilities: list[str] | None) -> dict:
    if not isinstance(reservation, dict) or not reservation.get("run_id"):
        raise WorkspacePolicyError("a valid isolation reservation receipt is required")
    reserved = {str(k): int(v) for k, v in (reservation.get("resources") or {}).items()}
    limits = {}
    for key, value in sorted((requested_limits or {}).items()):
        if key not in reserved:
            raise WorkspacePolicyError(f"runtime limit is not present in reservation: {key}")
        amount = int(value)
        if amount < 0 or amount > reserved[key]:
            raise WorkspacePolicyError(f"runtime limit exceeds reservation: {key}")
        limits[key] = amount
    granted = set(map(str, reservation.get("granted_capabilities") or []))
    requested = sorted(set(map(str, requested_capabilities or [])))
    if not set(requested).issubset(granted):
        raise WorkspacePolicyError("runtime cannot receive capabilities outside the admitted reservation")
    return {
        "schema": 1,
        "run_id": reservation["run_id"],
        "reservation_digest": reservation.get("request_digest"),
        "limits": limits,
        "capabilities": requested,
        "enforcement_required": True,
        "host_escape_allowed": False,
    }


def build_vault_broker_request(*, run_id: str, secret_refs: list[str], purpose: str, authority_manifest: dict) -> dict:
    if not run_id or not purpose:
        raise VaultBrokerError("run_id and purpose are required")
    granted = set(map(str, (authority_manifest or {}).get("granted", [])))
    if "secrets.resolve" not in granted:
        raise VaultBrokerError("secrets.resolve authority is required")
    clean = sorted(set(map(str, secret_refs or [])))
    if not clean:
        raise VaultBrokerError("at least one secret reference is required")
    for ref in clean:
        if not ref.startswith("secretref://") or not ref[len("secretref://"):].strip():
            raise VaultBrokerError("only secretref:// references may cross the vault broker boundary")
    return {
        "schema": 1,
        "run_id": str(run_id),
        "purpose": str(purpose),
        "secret_refs": clean,
        "authority_digest": _digest({"granted": sorted(granted)}),
        "request_digest": _digest({"run_id": run_id, "purpose": purpose, "secret_refs": clean}),
    }


def build_vault_broker_receipt(request: dict, *, status: str, lease_ids: list[str] | None = None) -> dict:
    status = str(status)
    if status not in {"resolved", "denied", "unavailable", "revoked"}:
        raise VaultBrokerError("unsupported vault broker receipt status")
    refs = request.get("secret_refs") or []
    # Lease IDs can be sensitive/replayable. Persist only a digest/count.
    leases = sorted(set(map(str, lease_ids or [])))
    return {
        "schema": 1,
        "run_id": request.get("run_id"),
        "purpose": request.get("purpose"),
        "status": status,
        "request_digest": request.get("request_digest"),
        "secret_ref_count": len(refs),
        "secret_ref_digest": _digest({"refs": sorted(refs)}),
        "lease_count": len(leases),
        "lease_digest": _digest({"lease_ids": leases}),
    }


def watchdog_plan(runs: list[dict], reservations: dict | list | None, *, now_ms: int, max_runtime_ms: int | None = None) -> dict:
    now = int(now_ms)
    if isinstance(reservations, dict):
        reservation_ids = set(map(str, reservations.keys()))
    else:
        reservation_ids = {str(r.get("run_id")) for r in (reservations or []) if r.get("run_id")}
    actions = []
    terminal = {"completed", "failed", "cancelled"}
    for run in sorted(runs or [], key=lambda r: str(r.get("run_id", ""))):
        run_id = str(run.get("run_id", ""))
        if not run_id:
            continue
        status = str(run.get("status", ""))
        expires = run.get("lease_expires_at_ms")
        updated = int(run.get("updated_at_ms") or 0)
        if status in terminal:
            if run_id in reservation_ids:
                actions.append({"run_id": run_id, "action": "release_reservation", "reason": "terminal_run"})
            continue
        lease_expired = expires is not None and now >= int(expires)
        runaway = max_runtime_ms is not None and max_runtime_ms >= 0 and now - updated > int(max_runtime_ms)
        if lease_expired:
            actions.append({"run_id": run_id, "action": "mark_worker_lost", "reason": "lease_expired"})
            if run_id in reservation_ids:
                actions.append({"run_id": run_id, "action": "release_reservation", "reason": "lease_expired"})
        elif runaway:
            actions.append({"run_id": run_id, "action": "cancel_run", "reason": "runaway_runtime"})
            if run_id in reservation_ids:
                actions.append({"run_id": run_id, "action": "release_reservation", "reason": "runaway_runtime"})
    return {
        "schema": 1,
        "evaluated_at_ms": now,
        "executed": False,
        "actions": actions,
        "action_count": len(actions),
    }
