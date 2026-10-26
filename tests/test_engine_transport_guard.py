"""The documented loopback credential must stay on its intended local origin."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import threading

import pytest

from divine_providence import engine


@pytest.mark.parametrize('base', [
    'https://example.com', 'http://localhost.evil.test',
    'http://user:password@localhost:8791', 'http://localhost:8791/prefix',
    'http://localhost:8791?query=x', 'http://localhost:8791#fragment',
    'file:///tmp/engine', ' http://localhost:8791', 'http://localhost:0',
    'http://localhost:65536',
])
def test_non_origin_or_non_loopback_base_is_rejected_before_transport(monkeypatch, base):
    monkeypatch.setattr(engine, 'BASE', base)
    monkeypatch.setattr(engine, '_token', lambda: 'fixture-local-token')
    monkeypatch.setattr(engine.urllib.request, 'urlopen', lambda *a, **k: BytesIO(b'{}'))
    with pytest.raises(ValueError):
        engine.research()


@contextmanager
def _server(callback):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            callback(self)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)


def _json(handler):
    handler.send_response(200)
    handler.end_headers()
    handler.wfile.write(b'{"ok":true}')


def test_local_engine_request_ignores_ambient_http_proxy(monkeypatch):
    proxied, direct = [], []

    def proxy(handler):
        proxied.append(handler.headers.get('Authorization'))
        _json(handler)

    def local(handler):
        direct.append(handler.headers.get('Authorization'))
        _json(handler)

    with _server(proxy) as proxy_url, _server(local) as origin:
        monkeypatch.setattr(engine, 'BASE', origin)
        monkeypatch.setattr(engine, '_token', lambda: 'fixture-local-token')
        monkeypatch.setattr(engine.urllib.request, '_opener', None)
        for key in ('http_proxy', 'HTTP_PROXY'):
            monkeypatch.setenv(key, proxy_url)
        for key in ('no_proxy', 'NO_PROXY'):
            monkeypatch.setenv(key, '')
        assert engine.research() == {'ok': True}
    assert direct == ['Bearer fixture-local-token']
    assert proxied == []


def test_local_engine_redirect_is_returned_without_second_request(monkeypatch):
    hops = []

    def destination(handler):
        hops.append(handler.path)
        _json(handler)

    with _server(destination) as target:
        def redirect(handler):
            handler.send_response(302)
            handler.send_header('Location', target + '/capture')
            handler.end_headers()

        with _server(redirect) as origin:
            monkeypatch.setattr(engine, 'BASE', origin)
            monkeypatch.setattr(engine, '_token', lambda: 'fixture-local-token')
            monkeypatch.setattr(engine.urllib.request, '_opener', None)
            monkeypatch.setenv('no_proxy', '*')
            monkeypatch.setenv('NO_PROXY', '*')
            result = engine.research()
    assert result.get('error') == 302
    assert hops == []
