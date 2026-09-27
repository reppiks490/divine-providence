"""AION commands. The HTTP cockpit is read-only and binds loopback only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contracts import Observation, SourceSpec
from .demo import install
from .federation import export_views
from .replay import Scenario, frame
from .store import EventStore


def main(argv=None):
    parser = argparse.ArgumentParser(description="AION market memory (research and shadow only)")
    parser.add_argument("--db", default="run/aion.sqlite3")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("demo")
    sub.add_parser("verify")
    sub.add_parser("timeline")
    register = sub.add_parser("register")
    register.add_argument("file", type=Path)
    append = sub.add_parser("append")
    append.add_argument("file", type=Path)
    state = sub.add_parser("frame")
    state.add_argument("asof_ns", type=int)
    state.add_argument("--symbol")
    state.add_argument("--view", choices=("raw", "athena", "argus", "daedalus", "icarus"), default="raw")
    state.add_argument("--scenario")
    state.add_argument("--depth", type=float, default=1.0)
    state.add_argument("--volatility", type=float, default=1.0)
    state.add_argument("--suppress", action="append", default=[])
    sub.add_parser("predictions")
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    store = EventStore(args.db)
    if args.command == "init":
        output = {"database": str(args.db), "schema": 1, "execution_authorized": False}
    elif args.command == "demo":
        output = install(store)
    elif args.command == "verify":
        output = store.verify_chain()
    elif args.command == "timeline":
        output = store.timeline()
    elif args.command == "register":
        output = {"source_hash": store.register(SourceSpec.from_dict(json.loads(args.file.read_text())))}
    elif args.command == "append":
        output = store.append(Observation.from_dict(json.loads(args.file.read_text())))
    elif args.command == "frame":
        scenario = Scenario(args.scenario, args.volatility, args.depth, tuple(args.suppress)) if args.scenario else None
        result = frame(store, args.asof_ns, symbol=args.symbol, scenario=scenario)
        output = result if args.view == "raw" else export_views(result)[args.view]
    elif args.command == "predictions":
        output = store.predictions()
    else:
        from .webapp import serve as serve_cockpit
        serve_cockpit(store, args.port)
        return 0
    print(json.dumps(output, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
