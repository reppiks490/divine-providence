"""Resolve sibling subsystems from the Divine Providence monorepo layout.

The sibling tests were written against the original handoff workspace
(`<BASE>/ARGUS-MICROSTRUCTURE-OS_HANDOFF/...`). In the monorepo the siblings
live next to ORACLE under `systems/`. Sibling code is only imported by tests
to validate exact contracts; ORACLE runtime code never imports siblings.
"""
import sys
from pathlib import Path

SYSTEMS = Path(__file__).resolve().parents[2]
for p in (SYSTEMS / "argus" / "src", SYSTEMS / "athena" / "src", SYSTEMS / "daedalus" / "src", SYSTEMS / "aion"):
    if p.is_dir() and str(p) not in sys.path:
        sys.path.insert(0, str(p))
