#!/usr/bin/env python3
"""Deterministic adaptive query-family expansion for SuperMesh-X."""
import argparse
import json


def _append(rows, seen, kind, query):
    query = " ".join(query.split())
    if query and query not in seen:
        seen.add(query)
        rows.append({"kind": kind, "query": query})


def expand(query, domain="research"):
    rows, seen = [], set()
    _append(rows, seen, "baseline", query)
    _append(rows, seen, "primary", f'{query} official primary source')
    _append(rows, seen, "temporal", f'{query} date published revised historical timeline')
    _append(rows, seen, "contradiction", f'{query} conflicting evidence correction dispute')

    if domain == "finance":
        _append(rows, seen, "regulatory", f'{query} filing regulatory investor relations')
        _append(rows, seen, "structured", f'{query} fundamentals market data historical')
    elif domain == "crypto":
        _append(rows, seen, "onchain", f'{query} on-chain transaction contract protocol')
        _append(rows, seen, "repository", f'{query} github documentation protocol repository')
    elif domain == "coding":
        _append(rows, seen, "repository", f'{query} repository issue pull request documentation')
    elif domain == "research":
        _append(rows, seen, "scholarly", f'{query} paper study literature review')
        _append(rows, seen, "archive", f'{query} archived earlier version')
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--domain", default="research", choices=["research", "finance", "crypto", "coding"])
    args = ap.parse_args()
    print(json.dumps(expand(args.query, args.domain), indent=2))


if __name__ == "__main__":
    main()
