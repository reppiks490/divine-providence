"""Read-only client for the live ICARUS engine HTTP API (icarus-bridge, port 8791).

Only GET routes are exposed. Nothing here can pause, flatten, change inputs or
place orders; those remain with the engine's own admin surface and its owner.
The engine accepts loopback Host headers only; research routes need the bearer
token from ``ICARUS_ENGINE_TOKEN``.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("ICARUS_ENGINE_URL", "http://127.0.0.1:8791").rstrip("/")


def _token() -> str:
    return os.environ.get("ICARUS_ENGINE_TOKEN", "")


_SYMBOL = re.compile(r"[A-Za-z0-9!_-]{1,20}")


def _symbol(symbol: str) -> str:
    if not _SYMBOL.fullmatch(symbol or ""):
        raise ValueError(f"invalid asset symbol {symbol!r}")
    return urllib.parse.quote(symbol.upper(), safe="")


def get(path: str, timeout: float = 10.0, **params) -> dict | list:
    q = {k: v for k, v in params.items() if v is not None}
    url = BASE + path + ("?" + urllib.parse.urlencode(q) if q else "")
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    if _token() and path.startswith("/api/research"):
        # Only the research routes need the token; unredirected so a 30x never forwards it.
        req.add_unredirected_header("Authorization", f"Bearer {_token()}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as ex:
        return {"error": ex.code, "detail": ex.read().decode("utf-8", "replace")[:500]}
    except (urllib.error.URLError, TimeoutError, ConnectionError) as ex:
        return {"error": "engine_unreachable", "base": BASE, "detail": str(getattr(ex, "reason", ex)),
                "hint": "start it with: py -3 -m icarus_engine.cli run ... (cwd C:\\Users\\tripl\\icarus-bridge)"}


def health() -> dict:
    return get("/healthz")


def status() -> dict:
    return get("/status/public")


def assets() -> dict:
    return get("/api/assets")


def presets() -> list:
    return get("/api/presets")


def trades(symbol: str, limit: int = 100) -> list:
    return get(f"/api/trades/{_symbol(symbol)}", limit=max(1, min(2000, int(limit))))


def chart(symbol: str, n: int = 240) -> dict:
    return get(f"/api/chart/{_symbol(symbol)}", n=max(20, min(800, int(n))))


def inputs(symbol: str) -> dict:
    return get(f"/api/inputs/{_symbol(symbol)}")


RESEARCH_VIEWS = {"status": "/api/research", "adaptation": "/api/research/adaptation", "source-watch": "/api/research/source-watch",
                  "analysis": "/api/research/analysis", "activation": "/api/research/activation", "sources": "/api/research/sources"}


def research(view: str = "status") -> dict:
    if view not in RESEARCH_VIEWS:
        return {"error": "unknown_view", "views": sorted(RESEARCH_VIEWS)}
    return get(RESEARCH_VIEWS[view])
