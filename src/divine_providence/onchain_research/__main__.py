"""CLI for the read-only CCTP V2 research clock."""

from __future__ import annotations

import argparse
import json

from . import asof, fetch, timeline, validate_query, verify


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m divine_providence.onchain_research")
    parser.add_argument("--db", required=True, help="SQLite snapshot file")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("fetch", "timeline", "asof"):
        cmd = sub.add_parser(command)
        cmd.add_argument("--environment", choices=("mainnet", "sandbox"), required=True)
        cmd.add_argument("--source-domain", type=int, required=True)
        cmd.add_argument("--transaction-hash", required=True)
        if command == "asof":
            cmd.add_argument("--decision-time", required=True)
    sub.add_parser("verify")
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            result = verify(args.db)
        else:
            validate_query(args.source_domain, args.transaction_hash)
            query = {"environment": args.environment, "source_domain": args.source_domain,
                     "transaction_hash": args.transaction_hash}
            if args.command == "fetch":
                result = fetch(args.db, **query)
            elif args.command == "timeline":
                result = timeline(args.db, **query)
            else:
                result = asof(args.db, **query, decision_time=args.decision_time)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"error: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
