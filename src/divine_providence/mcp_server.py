"""icarus-engine MCP server (stdio): the Divine Providence subsystems + the live ICARUS engine.

Register with Claude Code:
  claude mcp add icarus-engine -e ICARUS_ENGINE_TOKEN=<token> -- <python> -m divine_providence.mcp_server

Every subsystem call runs in its own interpreter process (see runner.py). Tools
are read/verify-only: nothing here trades, pauses, flattens, promotes, signs,
spends a protected holdout or grants authority to any system.
"""
from __future__ import annotations

import json
import threading
from pathlib import PureWindowsPath

try:  # mcp >= 2.0 renamed FastMCP to MCPServer; the decorator API is the same.
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server

from . import connections, engine, registry, runner

mcp = _Server(
    "icarus-engine",
    instructions=(
        "ICARUS / Divine Providence system-of-systems. Subsystems (NEXUS, DAEDALUS, AION, ARGUS, ATHENA, ORACLE, "
        "PROMETHEUS, ASCENSION, AEGIS, JANUS, Infrastructure, SuperMesh-X) each own a strict authority boundary; "
        "call authority_map before reasoning about who may decide what. BUILT != VERIFIED != READY_TO_COMMIT: "
        "passing tests are engineering evidence, never trading edge or production authorization. Engine tools read the "
        "live paper engine on :8791 and cannot change it. run_system_tests can take minutes (DAEDALUS ~4 min)."
    ),
)


def _validation_report() -> dict:
    p = registry.repo_root() / "provenance" / "validation_report.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def _sources() -> dict:
    p = registry.repo_root() / "provenance" / "assembly_sources.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


# ---------------------------------------------------------------- systems
@mcp.tool()
def list_systems() -> list[dict]:
    """Every subsystem with version, role, and the last recorded validation result."""
    report = _validation_report()
    rep = report.get("systems", {})
    return [{"name": s.name, "title": s.title, "version": s.version, "role": s.role,
             "last_validation": rep.get(s.name, {}).get("counts"), "validated_at": report.get("generated_at")}
            for s in registry.SYSTEMS.values()]


@mcp.tool()
def system_info(name: str) -> dict:
    """Details for one subsystem: authority (owns / must not), canonical source archive + SHA-256, docs, validation."""
    s = registry.get(name)
    return {"name": s.name, "title": s.title, "version": s.version, "role": s.role, "owns": s.owns, "must_not": s.must_not,
            "path": str(s.path.relative_to(registry.repo_root())), "docs": [d for d in s.docs if (s.path / d).is_file()],
            "canonical_source": _sources().get(name), "last_validation": _validation_report().get("systems", {}).get(name)}


@mcp.tool()
def authority_map() -> dict:
    """Sibling authority map and global invariants (who owns what; what each system must never do)."""
    return {"systems": {s.name: {"owns": s.owns, "must_not": s.must_not} for s in registry.SYSTEMS.values()},
            "production_execution_authority": "ICARUS engine owner only; no subsystem here holds it",
            "integration_direction": registry.INTEGRATION_DIRECTION, "invariants": registry.GLOBAL_INVARIANTS}


_TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".csv"}


def _lexically_safe(doc: str) -> bool:
    """Reject before any filesystem I/O: resolving a UNC path such as //host/share would
    already open an SMB connection. Only plain relative paths inside the tree pass."""
    p = PureWindowsPath(doc)
    return bool(doc) and not (p.drive or p.root or ":" in doc or "\x00" in doc
                              or any(part == ".." for part in p.parts))


@mcp.tool()
def read_system_doc(name: str, doc: str = "README.md", max_chars: int = 20000) -> dict:
    """Read a text document inside one subsystem's tree (README, state capsule, validation status...)."""
    s = registry.get(name)
    available = [d for d in s.docs if (s.path / d).is_file()]
    if not _lexically_safe(doc):
        return {"error": "only relative paths inside the system tree are allowed", "available": available}
    base = s.path.resolve()
    target = (base / doc).resolve()
    if base not in target.parents or not target.is_file():
        return {"error": "document not found inside system", "available": available}
    if target.suffix.lower() not in _TEXT_SUFFIXES:
        return {"error": "only text documents can be read"}
    max_chars = max(1, min(int(max_chars), 200_000))
    text = target.read_text(encoding="utf-8", errors="replace")
    return {"system": name, "doc": doc, "truncated": len(text) > max_chars, "text": text[:max_chars]}


_SUITE_LOCKS = {n: threading.Lock() for n in registry.SYSTEMS}


@mcp.tool()
def run_system_tests(name: str, timeout_s: int = 900) -> dict:
    """Run one subsystem's full pytest suite in an isolated process; returns counts and output tail.
    Runs of the same system are serialized; the timeout is clamped to 30s..3x the system default."""
    s = registry.get(name)
    timeout_s = max(30, min(int(timeout_s), 3 * s.test_timeout_s))
    with _SUITE_LOCKS[name]:
        res = runner.run_system_tests(name, timeout_s=timeout_s)
    res["stdout_tail"] = res["stdout_tail"][-3000:]
    res["stderr_tail"] = res["stderr_tail"][-1500:]
    return res


@mcp.tool()
def validation_report() -> dict:
    """The last full-build validation report (all suites, connections, compile checks) written by scripts/validate_all.py."""
    return _validation_report() or {"error": "no report yet; run: dp validate  (python -m divine_providence.validate)"}


# ---------------------------------------------------------------- connections
@mcp.tool()
def list_connections() -> list[dict]:
    """Cross-system contracts that are exercised end to end."""
    return [{"name": c.name, "systems": list(c.systems), "contract": c.contract, "description": c.description}
            for c in connections.CONNECTIONS.values()]


@mcp.tool()
def run_tour() -> dict:
    """End-to-end run: one deterministic NEXUS market instant followed through every connected system
    (NEXUS -> AION/ARGUS/ATHENA/DAEDALUS -> ORACLE -> PROMETHEUS -> ASCENSION -> SuperMesh-X), plus
    standalone systems and live-engine health. Returns a readable narration and the structured results."""
    from . import tour
    t = tour.run()
    return {"ok": t["ok"], "narration": tour.narrate(t), "same_instant_everywhere": t["same_instant_everywhere"],
            "instant_bundle_hash": t["instant_bundle_hash"], "connections": t["connections"], "engine": t["engine"]}


@mcp.tool()
def connection_coverage() -> dict:
    """Per system: the verified connections it takes part in, or why it is standalone (no contract exists in its code)."""
    return connections.coverage()


@mcp.tool()
def check_connection(name: str) -> dict:
    """Execute one cross-system connection now (e.g. nexus-siblings, nexus-oracle, nexus-prometheus, prometheus-ascension)."""
    return connections.check(name)


@mcp.tool()
def check_all_connections() -> dict:
    """Execute every cross-system connection now and report which links are healthy."""
    return connections.check_all()


# ---------------------------------------------------------------- live engine (read-only)
@mcp.tool()
def engine_health() -> dict:
    """Live ICARUS engine liveness: running assets and warm-up state."""
    return engine.health()


@mcp.tool()
def engine_status() -> dict:
    """Live ICARUS engine public status (per-asset state, positions, equity) from the paper runtime."""
    return engine.status()


@mcp.tool()
def engine_assets() -> dict:
    """Asset registry of the engine and which assets are currently running."""
    return engine.assets()


@mcp.tool()
def engine_trades(symbol: str, limit: int = 50) -> list | dict:
    """Recent paper trades for one engine asset (e.g. NQ, ES, GC, BTC)."""
    return engine.trades(symbol, limit)


@mcp.tool()
def engine_inputs(symbol: str) -> dict:
    """Effective strategy inputs, preset and overrides for one engine asset (read-only)."""
    return engine.inputs(symbol)


@mcp.tool()
def engine_presets() -> list | dict:
    """The owner's imported TradingView presets known to the engine."""
    return engine.presets()


@mcp.tool()
def engine_research(view: str = "status") -> dict:
    """Engine research plane (needs ICARUS_ENGINE_TOKEN): status | adaptation | source-watch | analysis | activation | sources."""
    return engine.research(view)


# ---------------------------------------------------------------- resources
@mcp.resource("icarus://systems")
def systems_resource() -> str:
    """All subsystems as JSON."""
    return json.dumps(list_systems(), indent=2)


@mcp.resource("icarus://authority-map")
def authority_resource() -> str:
    """Authority map and invariants as JSON."""
    return json.dumps(authority_map(), indent=2)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
