"""Collect fresh ICARUS engineering evidence without remote writes.

Initialization precedes dependency setup. The always-run finalizer preserves
completed failures and makes interrupted or missing collection visible.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import threading
import time


SCHEMA = "icarus.observatory.collection.v1"
LOG_LIMIT = 65_536
REPORT_LIMIT = 4 * 1024 * 1024
EVIDENCE_FILES = (
    "collection.json", "hub.json", "validation_report.json",
    "hub.stdout.log", "hub.stderr.log", "validation.stdout.log", "validation.stderr.log",
    "run.json", "comparison.json", "summary.md", "index.html", "SHA256SUMS",
)
_UNSAFE_ENV = {
    "PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTHONOPTIMIZE", "PYTHONINSPECT",
    "PYTHONSTARTUP", "PYTHONHOME", "GITHUB_TOKEN", "GH_TOKEN",
    "ACTIONS_RUNTIME_TOKEN", "SYSTEM_ACCESSTOKEN",
}
_SUMMARY = re.compile(r"(\d+) (passed|failed|errors?|skipped|xfailed|xpassed|deselected)\b")
_INVENTORY = """
import json
from divine_providence import registry, connections, validate
print(json.dumps({
    'systems': sorted(registry.SYSTEMS),
    'connections': {name: {'systems': list(c.systems), 'contract': c.contract}
                    for name, c in sorted(connections.CONNECTIONS.items())},
    'adversarial': sorted(validate.ASCENSION_SCRIPTS),
    'coverage': connections.coverage(),
}, sort_keys=True))
"""


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _environment(root: Path, environ: dict | None) -> dict[str, str]:
    supplied = {**os.environ, **(environ or {})}
    env = {k: v for k, v in supplied.items() if k not in _UNSAFE_ENV
           and not k.endswith(("_TOKEN", "_SECRET", "_PASSWORD"))}
    env["PYTHONPATH"] = os.pathsep.join((str(root / "src"), str(root)))
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    return env


def run_process(args: list[str], *, root: Path, timeout: float,
                stdout_path: Path | None = None, stderr_path: Path | None = None,
                environ: dict | None = None) -> dict:
    """Drain both pipes concurrently, retaining only bounded tails in memory.

    A new process group contains the validator's nested workers. Group cleanup
    also prevents orphaned workers from holding pipes open after their parent.
    """
    if timeout <= 0:
        raise ValueError("process timeout must be positive")
    started = time.monotonic()
    buffers = [bytearray(), bytearray()]
    timed_out = False
    returncode = None
    try:
        process = subprocess.Popen(args, cwd=root, env=_environment(root, environ),
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=(os.name == "posix"))
    except OSError as exc:
        buffers[1].extend(str(exc).encode("utf-8", "replace")[-LOG_LIMIT:])
    else:
        def drain(pipe, target):
            try:
                while block := pipe.read(8192):
                    target.extend(block)
                    if len(target) > LOG_LIMIT:
                        del target[:-LOG_LIMIT]
            finally:
                pipe.close()

        readers = [threading.Thread(target=drain, args=(pipe, buffer), daemon=True)
                   for pipe, buffer in zip((process.stdout, process.stderr), buffers)]
        for reader in readers:
            reader.start()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            if os.name == "posix":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            elif process.poll() is None:
                process.kill()
            returncode = process.wait()
            for reader in readers:
                reader.join(timeout=2)

    # Replacement characters can expand invalid bytes. Bound the encoded text
    # once more and drop a partial leading UTF-8 character before writing it.
    tails = [bytes(buffer).decode("utf-8", "replace").encode("utf-8")[-LOG_LIMIT:]
             .decode("utf-8", "ignore") for buffer in buffers]
    for path, tail in zip((stdout_path, stderr_path), tails):
        if path is not None:
            path.write_text(tail, encoding="utf-8")
    return {"returncode": returncode, "timed_out": timed_out,
            "seconds": round(time.monotonic() - started, 3),
            "stdout_tail": tails[0], "stderr_tail": tails[1]}


def _paths(output: Path, root: Path | None) -> tuple[Path, Path]:
    root = Path(root or Path(__file__).resolve().parents[2]).resolve()
    raw_output = Path(output)
    if raw_output.is_symlink():
        raise ValueError("output directory must not be a symlink")
    output = raw_output.resolve()
    if output == root or output in root.parents:
        raise ValueError("output directory must not contain the repository")
    output.mkdir(parents=True, exist_ok=True)
    return output, root


def _write(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _remove(path: Path, errors: list[str]) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        errors.append(f"cannot remove stale evidence {path.name}: {exc}")


def _clean(output: Path, root: Path, errors: list[str], *, keep_receipt=False) -> None:
    for name in EVIDENCE_FILES:
        if keep_receipt and name == "collection.json":
            continue
        _remove(output / name, errors)
    _remove(root / "provenance" / "validation_report.json", errors)


def _identity(root: Path, environ: dict | None) -> dict:
    env = {**os.environ, **(environ or {})}
    def integer(name):
        try:
            return int(env.get(name, "0"))
        except (TypeError, ValueError):
            return 0
    repository = env.get("GITHUB_REPOSITORY", "local")
    commit = env.get("GITHUB_SHA", "")
    if not commit:
        try:
            result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                                    env=_environment(root, environ), capture_output=True,
                                    text=True, timeout=5)
            commit = result.stdout.strip() if result.returncode == 0 else "unknown"
        except (OSError, subprocess.TimeoutExpired):
            commit = "unknown"
    run_id = integer("GITHUB_RUN_ID")
    return {"run_id": run_id, "run_attempt": integer("GITHUB_RUN_ATTEMPT"),
            "event": env.get("GITHUB_EVENT_NAME", "local"),
            "repository": repository, "ref": env.get("GITHUB_REF", "local"),
            "commit": commit,
            "run_url": f"https://github.com/{repository}/actions/runs/{run_id}"}


def _dependencies(receipt: dict) -> None:
    try:
        pairs = {(re.sub(r"[-_.]+", "-", d.metadata["Name"]).lower(), d.version)
                 for d in metadata.distributions() if d.metadata["Name"]}
        receipt["dependencies"] = [{"name": name, "version": version}
                                   for name, version in sorted(pairs)]
    except Exception as exc:
        receipt["dependencies"] = []
        receipt["collection_errors"].append(f"dependency metadata unavailable: {exc}")
    encoded = json.dumps(receipt["dependencies"], sort_keys=True, separators=(",", ":")).encode("utf-8")
    receipt["dependency_hash"] = hashlib.sha256(encoded).hexdigest()


def _inventory(receipt: dict, root: Path, environ: dict | None) -> None:
    result = run_process([sys.executable, "-c", _INVENTORY], root=root, timeout=30, environ=environ)
    try:
        if result["returncode"] != 0 or result["timed_out"]:
            raise ValueError(result["stderr_tail"] or "inventory process did not complete")
        value = json.loads(result["stdout_tail"])
        if not isinstance(value, dict) or set(value) != {"systems", "connections", "adversarial", "coverage"}:
            raise ValueError("unexpected inventory shape")
        receipt["inventory"] = value
    except (ValueError, TypeError) as exc:
        receipt["collection_errors"].append(f"source inventory unavailable: {str(exc)[-2000:]}")


def initialize(output: Path, *, root: Path | None = None, environ: dict | None = None) -> dict:
    """Discard old outputs and write the current run receipt before setup."""
    output, root = _paths(output, root)
    now = _utc()
    receipt = {"schema": SCHEMA, **_identity(root, environ),
               "started_at": now, "finished_at": now,
               "python": platform.python_version(), "platform": platform.platform(),
               "hub_exit_code": None, "validator_exit_code": None,
               "hub_timed_out": False, "validator_timed_out": False,
               "collection_errors": [], "dependencies": [],
               "inventory": {"systems": [], "connections": {}, "adversarial": [], "coverage": {}},
               "phase": "initialized"}
    _clean(output, root, receipt["collection_errors"])
    _write(output / "collection.json", receipt)
    _dependencies(receipt)
    _inventory(receipt, root, environ)
    _write(output / "collection.json", receipt)
    return receipt


def _current(output: Path, root: Path, environ: dict | None) -> dict | None:
    try:
        path = output / "collection.json"
        if path.is_symlink() or path.stat().st_size > REPORT_LIMIT:
            return None
        receipt = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(receipt, dict) or receipt.get("schema") != SCHEMA:
            return None
        if any(receipt.get(k) != value for k, value in _identity(root, environ).items()):
            return None
        if not isinstance(receipt.get("collection_errors"), list) or any(
                not isinstance(error, str) for error in receipt["collection_errors"]):
            return None
        if receipt.get("phase") not in {"initialized", "collecting", "completed", "finalized"}:
            return None
        for name in ("hub_exit_code", "validator_exit_code"):
            if receipt.get(name) is not None and type(receipt[name]) is not int:
                return None
        return receipt
    except (OSError, ValueError, TypeError):
        return None


def _counts(stdout: str) -> dict[str, int]:
    line = next((line for line in reversed(stdout.splitlines()) if _SUMMARY.search(line)), "")
    return {"errors" if kind.startswith("error") else kind: int(number)
            for number, kind in _SUMMARY.findall(line)}


def collect(output: Path, *, root: Path | None = None, environ: dict | None = None,
            hub_timeout: float = 900, validator_timeout: float = 2700) -> dict:
    """Run independent hub and validator processes, recording checkpoints."""
    if hub_timeout <= 0 or validator_timeout <= 0 or validator_timeout > 2700:
        raise ValueError("timeouts must be positive; validator timeout cannot exceed 2700 seconds")
    output, root = _paths(output, root)
    receipt = _current(output, root, environ)
    if receipt is None or receipt["phase"] != "initialized":
        receipt = initialize(output, root=root, environ=environ)
    _clean(output, root, receipt["collection_errors"], keep_receipt=True)
    receipt["python"] = platform.python_version()
    receipt["platform"] = platform.platform()
    _dependencies(receipt)
    receipt["phase"] = "collecting"
    _write(output / "collection.json", receipt)
    for name, args, timeout in (
        ("hub", ["-m", "pytest", "-q", "tests", "-p", "no:cacheprovider", "-o", "addopts="], hub_timeout),
        ("validation", ["-m", "divine_providence.validate", "--workers", "2"], validator_timeout),
    ):
        # A stale native file we could not remove is never admitted as evidence.
        if name == "validation" and any("cannot remove stale evidence" in error
                                         for error in receipt["collection_errors"]):
            receipt["collection_errors"].append("validator not run because fresh evidence cleanup failed")
            continue
        try:
            result = run_process([sys.executable, *args], root=root, timeout=timeout,
                                 stdout_path=output / f"{name}.stdout.log",
                                 stderr_path=output / f"{name}.stderr.log", environ=environ)
        except Exception as exc:
            receipt["collection_errors"].append(f"{name} collection failed: {str(exc)[-2000:]}")
            continue
        key = "validator" if name == "validation" else name
        receipt[f"{key}_exit_code"] = result["returncode"]
        receipt[f"{key}_timed_out"] = result["timed_out"]
        if result["returncode"] is None:
            receipt["collection_errors"].append(f"{name} process could not start")
        if name == "hub":
            counts = _counts(result["stdout_tail"])
            if result["returncode"] == 0 and (counts.get("passed", 0) <= 0 or any(
                    counts.get(kind, 0) for kind in ("failed", "errors", "deselected"))):
                receipt["collection_errors"].append("hub exited zero without a passing test summary")
            _write(output / "hub.json", {**result, "counts": counts})
        _write(output / "collection.json", receipt)
    native = root / "provenance" / "validation_report.json"
    try:
        if receipt["validator_exit_code"] is None:
            raise ValueError("validator was not observed")
        if native.is_symlink():
            raise ValueError("native report is a symlink")
        if native.stat().st_size > REPORT_LIMIT:
            raise ValueError("native report exceeds evidence size limit")
        # Preserve the original bytes, including malformed JSON, for diagnosis.
        (output / "validation_report.json").write_bytes(native.read_bytes())
    except (OSError, ValueError) as exc:
        receipt["collection_errors"].append(f"fresh validation report unavailable: {exc}")
    receipt["phase"] = "completed"
    receipt["finished_at"] = _utc()
    _write(output / "collection.json", receipt)
    return receipt


def finalize(output: Path, *, root: Path | None = None, environ: dict | None = None) -> dict:
    """Finalize only this run; never import an old native report as success."""
    output, root = _paths(output, root)
    receipt = _current(output, root, environ)
    if receipt is None:
        receipt = initialize(output, root=root, environ=environ)
        receipt["collection_errors"].append("current collection receipt missing or invalid")
    if receipt["phase"] not in {"completed", "finalized"}:
        receipt["collection_errors"].append("collection not completed; setup failed or execution was interrupted")
        if receipt["validator_exit_code"] is None:
            _remove(output / "validation_report.json", receipt["collection_errors"])
        receipt["phase"] = "finalized"
        receipt["finished_at"] = _utc()
    _write(output / "collection.json", receipt)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--root", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--initialize", action="store_true")
    mode.add_argument("--finalize", action="store_true")
    parser.add_argument("--hub-timeout", type=float, default=900)
    parser.add_argument("--validator-timeout", type=float, default=2700)
    args = parser.parse_args(argv)
    if args.initialize:
        receipt = initialize(args.output, root=args.root)
        return int(bool(receipt["collection_errors"]))
    if args.finalize:
        finalize(args.output, root=args.root)
        return 0
    receipt = collect(args.output, root=args.root, hub_timeout=args.hub_timeout,
                      validator_timeout=args.validator_timeout)
    return int(bool(receipt["collection_errors"]) or receipt["hub_exit_code"] != 0
               or receipt["validator_exit_code"] != 0 or receipt["hub_timed_out"]
               or receipt["validator_timed_out"])


if __name__ == "__main__":
    raise SystemExit(main())
