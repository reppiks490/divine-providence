from __future__ import annotations

import json
import sys
from pathlib import Path

SYSTEMS = Path(__file__).resolve().parents[3] / "systems"


def emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, sort_keys=True, default=str) + "\n")


def sibling_roots() -> dict[str, Path]:
    return {name: SYSTEMS / name for name in ("aion", "argus", "athena", "daedalus")}
