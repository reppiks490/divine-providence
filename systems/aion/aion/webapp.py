"""Local, read-only cockpit for the market memory."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import json
from urllib.parse import parse_qs, urlsplit

from .federation import export_views
from .replay import Scenario, compare, frame
from .store import EventStore


def _number(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def handler_for(store: EventStore):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            host = self.headers.get("Host", "").lower()
            allowed_hosts = {"127.0.0.1", "localhost", f"127.0.0.1:{self.server.server_port}",
                             f"localhost:{self.server.server_port}"}
            if host not in allowed_hosts:
                body = b'{"error":"invalid host"}'
                self.send_response(403)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            try:
                url = urlsplit(self.path)
                query = parse_qs(url.query)
                at = _number(query.get("at", [0])[0])
                if url.path == "/":
                    body = files("aion").joinpath("cockpit.html").read_bytes()
                    content_type = "text/html; charset=utf-8"
                elif url.path == "/api/timeline":
                    body = json.dumps(store.timeline(), allow_nan=False).encode()
                    content_type = "application/json"
                elif url.path == "/api/sources":
                    body = json.dumps(store.sources(), allow_nan=False).encode()
                    content_type = "application/json"
                elif url.path == "/api/frame":
                    if at <= 0:
                        raise ValueError("positive as-of timestamp required")
                    real = frame(store, at)
                    name = query.get("scenario", [""])[0]
                    if name:
                        if name not in ("drought", "volatility", "macro_shift", "source_blackout"):
                            raise ValueError("unknown scenario")
                        book_sources = tuple(sorted({i["source"] for i in store.asof(at) if i["event"]["kind"].startswith("book_")}))
                        scenario = {
                            "drought": Scenario("drought", depth_multiplier=0),
                            "volatility": Scenario("volatility", volatility_multiplier=2.5),
                            "macro_shift": Scenario("macro_shift", macro_shift=1.0),
                            "source_blackout": Scenario("source_blackout", suppress_sources=book_sources),
                        }[name]
                        altered = frame(store, at, scenario=scenario)
                        result = {"frame": altered, "comparison": compare(real, altered), "actual_frame": real}
                    else:
                        result = {"frame": real, "comparison": None}
                    body = json.dumps(result, allow_nan=False).encode()
                    content_type = "application/json"
                elif url.path == "/api/evidence":
                    body = json.dumps(store.asof(at)[-120:], allow_nan=False).encode()
                    content_type = "application/json"
                elif url.path == "/api/predictions":
                    predictions = []
                    for row in store.predictions():
                        if row["prediction"]["decision_ns"] <= at:
                            if row["settlement"] and row["settlement"]["outcome_ns"] > at:
                                row["settlement"] = None
                            predictions.append(row)
                    body = json.dumps(predictions, allow_nan=False).encode()
                    content_type = "application/json"
                elif url.path == "/api/history":
                    bars = [i for i in store.asof(at) if i["event"]["kind"] == "bar"]
                    body = json.dumps([{"symbol": i["symbol"], "representation_id": i["representation_id"],
                                        "event_ns": i["event"]["event_ns"], "close": i["event"]["payload"].get("close"),
                                        "available_ns": i["event"]["available_ns"]} for i in bars], allow_nan=False).encode()
                    content_type = "application/json"
                elif url.path == "/api/exports":
                    body = json.dumps(export_views(frame(store, at)), allow_nan=False).encode()
                    content_type = "application/json"
                else:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'")
                self.end_headers()
                self.wfile.write(body)
            except (ValueError, TypeError, KeyError) as exc:
                body = json.dumps({"error": str(exc)}).encode()
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    return Handler


def serve(store: EventStore, port: int = 8765):
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("invalid port")
    server = ThreadingHTTPServer(("127.0.0.1", port), handler_for(store))
    print(f"AION cockpit: http://127.0.0.1:{port}/ (read only)")
    try:
        server.serve_forever()
    finally:
        server.server_close()
