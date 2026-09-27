from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import JanusTwin


def pp(obj):
    print(json.dumps(obj, indent=2, sort_keys=True))


def main() -> None:
    p = argparse.ArgumentParser(prog="janus_infinity")
    sub = p.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("init")
    q.add_argument("db")

    q = sub.add_parser("seed")
    q.add_argument("manifest")
    q.add_argument("db")

    q = sub.add_parser("status")
    q.add_argument("db")

    q = sub.add_parser("prioritize")
    q.add_argument("db")

    q = sub.add_parser("snapshot")
    q.add_argument("root")
    q.add_argument("--db", required=True)
    q.add_argument("--label", default="snapshot")

    q = sub.add_parser("reconcile")
    q.add_argument("root")
    q.add_argument("--db", required=True)

    q = sub.add_parser("import-handoff")
    q.add_argument("handoff_json")
    q.add_argument("--db", required=True)

    q = sub.add_parser("handoff")
    q.add_argument("db")
    q.add_argument("--out", required=True)

    args = p.parse_args()

    if args.cmd == "init":
        t = JanusTwin(args.db)
        pp(t.status())
        t.close()
        return

    if args.cmd == "seed":
        t = JanusTwin(args.db)
        t.seed_manifest(args.manifest)
        pp(t.status())
        t.close()
        return

    if args.cmd == "status":
        t = JanusTwin(args.db)
        pp(t.status())
        t.close()
        return

    if args.cmd == "prioritize":
        t = JanusTwin(args.db)
        pp(t.prioritized_candidates())
        t.close()
        return

    if args.cmd == "snapshot":
        t = JanusTwin(args.db)
        pp(t.snapshot(args.root, args.label))
        t.close()
        return

    if args.cmd == "reconcile":
        t = JanusTwin(args.db)
        pp(t.reconcile_root(args.root))
        t.close()
        return

    if args.cmd == "import-handoff":
        t = JanusTwin(args.db)
        pp(t.import_handoff(args.handoff_json))
        t.close()
        return

    if args.cmd == "handoff":
        t = JanusTwin(args.db)
        pp(t.export_handoff(args.out))
        t.close()
        return


if __name__ == "__main__":
    main()
