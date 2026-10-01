import asyncio
import json
import os
import sys

import pytest

from divine_providence import connections, engine, registry, runner

REPO = registry.repo_root()


@pytest.mark.parametrize("name", sorted(registry.SYSTEMS))
def test_every_system_tree_and_import_root_exists(name):
    s = registry.get(name)
    assert s.path.is_dir()
    for root in s.pythonpath():
        assert os.path.isdir(root), root
    assert any((s.path / d).is_file() for d in s.docs), f"{name} has none of its declared docs"
    assert any(p.name.startswith("test_") for p in s.path.rglob("test_*.py")), f"{name} ships no tests"


def test_unknown_system_is_rejected():
    with pytest.raises(KeyError):
        registry.get("icarus-live-execution")


def test_pytest_summary_parsing():
    assert runner.pytest_counts("....\n12 passed, 1 skipped in 3.2s\n") == {"passed": 12, "skipped": 1}
    assert runner.pytest_counts("x\n2 failed, 3 passed, 1 error in 1s") == {"failed": 2, "passed": 3, "errors": 1}


def test_nexus_sibling_contracts_hold_in_monorepo():
    r = connections.check("nexus-siblings")
    assert r["ok"] is True, r
    assert all(r["result"][k] for k in ("aion", "argus", "athena", "daedalus"))


def test_nexus_packet_reaches_oracle_financial_state():
    r = connections.check("nexus-oracle")
    assert r["ok"] is True, r
    assert r["packet_contract"] == "nexus.market-state.v2"


def test_prometheus_binds_fresh_nexus_bundle_only_without_drift():
    r = connections.check("nexus-prometheus")
    if r["semantic_drift_vs_current_baseline"]:
        # Fail-closed but not connected: PROMETHEUS must quarantine the live identity.
        assert r["link_state"] == "QUARANTINED_AS_EXPECTED" and r["ok"] is False, r
        assert r["accepted"] is False and r["refusal"]["failure_type"] == "CONTRACT_DRIFT"
    else:
        assert r["link_state"] == "LINKED" and r["ok"] is True, r
        assert r["accepted"] is True and r["identity_pinned_by_prometheus"] is True
        tiers = {o["sibling"]: o["evidence_tier"] for o in r["observations"]}
        assert tiers["ARGUS"] == "CANDLE_PROXY" and tiers["DAEDALUS"] == "RESEARCH_CANDIDATE_ONLY"


def test_sibling_contracts_match_the_pinned_v116_baseline():
    r = connections.check("nexus-contract-drift")
    assert r["ok"] is True and r["semantic_drift"] is False, r
    assert r["baseline_snapshot_hash"] == "65cba148bc5df86bd4b660ba15b14e6c58c113fa00fecdf3e22ea745a13ffe9a"
    assert {i["status"] for i in r["items"]} == {"unchanged"}

    v115 = {(i["sibling"], i["role"]): i["status"] for i in r["vs_v115"]["items"]}
    assert v115[("AION", "contracts")] == "semantic_change"
    assert v115[("AION", "store")] == "semantic_change"
    assert {v for k, v in v115.items() if k not in {("AION", "contracts"), ("AION", "store")}} == {"unchanged"}

    v03 = {(i["sibling"], i["role"]): i["status"] for i in r["vs_v03_release"]["items"]}
    assert v03[("AION", "contracts")] == "semantic_change"
    assert v03[("AION", "store")] == "semantic_change"
    assert v03[("DAEDALUS", "bridge")] == "semantic_change"
    assert v03[("ARGUS", "contracts")] == "unchanged"
    assert v03[("ATHENA", "contracts")] == "unchanged"


def test_prometheus_ascension_link_never_claims_authentication():
    r = connections.check("prometheus-ascension")
    assert r["authenticated"] is False
    assert r["transfer"].startswith("BLOCKED")


def test_supermesh_witnesses_nexus_artifacts_and_rejects_rewrites():
    r = connections.check("supermesh-witness")
    assert r["ok"] is True, r
    assert r["witness_quorum"] == 2 and r["gossip_verified"] is True and r["tree_size"] == 2
    assert r["negative_controls"]["history_rewrite_rejected"] and r["negative_controls"]["rollback_rejected"]


def test_every_system_is_connected_or_explicitly_standalone():
    cov = connections.coverage()
    assert set(cov) == set(registry.SYSTEMS)
    assert all(v["status"] in ("connected", "standalone") for v in cov.values())
    assert not any(v.get("reason") == "UNEXPLAINED" for v in cov.values())
    assert {n for n, v in cov.items() if v["status"] == "standalone"} == {"aegis", "janus", "infrastructure"}


def test_tour_follows_one_instant_through_every_connected_system():
    from divine_providence import tour
    t = tour.run(include_engine=False)
    assert t["ok"] is True and t["same_instant_everywhere"] is True, {k: v.get("ok") for k, v in t["connections"].items()}
    assert set(t["connections"]) == set(connections.CONNECTIONS)
    text = tour.narrate(t)
    assert "RESULT: ALL CONNECTED SYSTEMS RAN TOGETHER" in text
    assert "Same instant at every hop: YES" in text


def test_engine_client_reports_unreachable_engine(monkeypatch):
    monkeypatch.setattr(engine, "BASE", "http://127.0.0.1:9")
    r = engine.health()
    assert r["error"] == "engine_unreachable"


def test_mcp_tools_are_registered_and_read_only():
    import inspect

    from divine_providence import mcp_server
    tools = mcp_server.mcp.list_tools()
    names = {t.name for t in (asyncio.run(tools) if inspect.isawaitable(tools) else tools)}
    assert {"list_systems", "system_info", "authority_map", "run_system_tests", "check_all_connections",
            "engine_status", "engine_trades"} <= names
    for forbidden in ("pause", "resume", "flatten", "order", "activate", "promote", "sign"):
        assert not any(forbidden in n for n in names), forbidden


def test_read_system_doc_refuses_path_traversal():
    from divine_providence import mcp_server
    r = mcp_server.read_system_doc("aegis", "../../pyproject.toml")
    assert "error" in r
    ok = mcp_server.read_system_doc("aegis", "README.md", max_chars=50)
    assert ok["system"] == "aegis" and len(ok["text"]) <= 50


@pytest.mark.parametrize("doc", ["//attacker/share/x.md", "\\\\attacker\\share\\x.md", "C:/Windows/win.ini", "D:foo.md",
                                 "/etc/passwd", "README.md:stream.txt", "docs/../../../x.md", ""])
def test_read_system_doc_rejects_before_any_filesystem_access(doc, monkeypatch):
    from pathlib import Path

    from divine_providence import mcp_server

    real_resolve = Path.resolve
    markers = [m for m in ("attacker", "Windows", "foo.md", "passwd", "stream", "x.md") if m in doc]

    def guarded_resolve(self, *a, **k):
        if any(m in str(self) for m in markers):
            raise AssertionError(f"filesystem touched for unsafe path {self}")
        return real_resolve(self, *a, **k)

    monkeypatch.setattr(Path, "resolve", guarded_resolve)
    r = mcp_server.read_system_doc("aegis", doc)
    assert r["error"].startswith("only relative paths")


def test_driver_crash_or_foreign_output_fails_closed():
    r = runner.run_json_driver("does_not_exist", [])
    assert r["ok"] is False and r["returncode"] != 0


def test_runner_strips_env_that_could_hide_failures(monkeypatch):
    monkeypatch.setenv("PYTEST_ADDOPTS", "-k smoke")
    monkeypatch.setenv("PYTHONOPTIMIZE", "1")
    env = runner._env(["x"])
    assert "PYTEST_ADDOPTS" not in env and "PYTHONOPTIMIZE" not in env and env["PYTHONPATH"] == "x"


def test_deselected_or_timed_out_suites_never_pass(monkeypatch):
    fake = runner.RunResult(["py"], ".", 0, 1.0, "...\n3 passed, 2 deselected in 1s\n", "")
    monkeypatch.setattr(runner, "run", lambda *a, **k: fake)
    assert runner.run_system_tests("aegis")["passed"] is False
    slow = runner.RunResult(["py"], ".", -1, 1.0, "3 passed in 1s", "", timed_out=True)
    monkeypatch.setattr(runner, "run", lambda *a, **k: slow)
    assert runner.run_system_tests("aegis")["passed"] is False


def test_engine_symbols_cannot_escape_their_route():
    for bad in ("../../admin", "NQ/../x", "", "A" * 21):
        with pytest.raises(ValueError):
            engine.trades(bad)


def test_engine_token_only_sent_to_research_routes_and_never_redirected(monkeypatch):
    import urllib.request

    seen = []

    class Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b"{}"

    def fake_urlopen(req, timeout):
        seen.append((req.full_url, req.get_header("Authorization"), dict(req.unredirected_hdrs)))
        return Resp()

    monkeypatch.setenv("ICARUS_ENGINE_TOKEN", "t0k")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    engine.health()
    engine.research("status")
    (u1, h1, _), (u2, h2, unred) = seen
    assert u1.endswith("/healthz") and h1 is None
    assert u2.endswith("/api/research") and h2 == "Bearer t0k" and "Authorization" in unred


def test_authority_map_keeps_execution_out_of_every_subsystem():
    from divine_providence import mcp_server
    m = mcp_server.authority_map()
    assert set(m["systems"]) == set(registry.SYSTEMS)
    assert "no subsystem here holds it" in m["production_execution_authority"]


def test_mcp_stdio_handshake_lists_tools():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def go():
        params = StdioServerParameters(command=sys.executable, args=["-m", "divine_providence.mcp_server"],
                                       env={**os.environ, "PYTHONPATH": str(REPO / "src")}, cwd=str(REPO))
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                tools = await s.list_tools()
                res = await s.call_tool("list_systems", {})
                return {t.name for t in tools.tools}, res

    names, res = asyncio.run(go())
    assert "list_systems" in names and "engine_health" in names
    payload = [json.loads(c.text) for c in res.content]
    flat = payload[0] if len(payload) == 1 and isinstance(payload[0], list) else payload
    assert {row["name"] for row in flat} == set(registry.SYSTEMS)
