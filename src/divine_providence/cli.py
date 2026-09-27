"""``dp`` command line: inspect systems, run suites, check connections, serve MCP."""
from __future__ import annotations

import argparse
import json

from . import connections, registry, runner


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="dp", description="Divine Providence / ICARUS subsystem hub")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("systems", help="list subsystems")
    t = sub.add_parser("test", help="run one subsystem's test suite")
    t.add_argument("name")
    c = sub.add_parser("connect", help="check cross-system connections")
    c.add_argument("name", nargs="?")
    sub.add_parser("validate", help="full-build validation (writes provenance/validation_report.json)")
    sub.add_parser("tour", help="end-to-end run: one NEXUS instant through every connected system + live engine")
    sub.add_parser("mcp", help="serve the icarus-engine MCP server over stdio")
    a = ap.parse_args(argv)
    if a.cmd == "systems":
        for s in registry.SYSTEMS.values():
            print(f"{s.name:15s} {s.version:32s} {s.title}")
    elif a.cmd == "test":
        r = runner.run_system_tests(a.name)
        print(r["stdout_tail"][-2000:])
        return 0 if r["passed"] else 1
    elif a.cmd == "connect":
        r = connections.check(a.name) if a.name else connections.check_all()
        print(json.dumps(r, indent=2, sort_keys=True))
        return 0 if r.get("ok") else 1
    elif a.cmd == "validate":
        from .validate import main as vmain
        return vmain([])
    elif a.cmd == "tour":
        from .tour import main as tmain
        return tmain()
    elif a.cmd == "mcp":
        from .mcp_server import main as mmain
        mmain()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
