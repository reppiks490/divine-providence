import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from mcp_era_guard import normalize_tool_contract, protocol_preflight, build_tool_trace


def test_annotations_default_conservatively_when_missing():
    c = normalize_tool_contract({'name': 'unknown_tool', 'inputSchema': {'type': 'object'}}, '2026-07-28')
    assert c['annotations'] == {
        'readOnlyHint': False,
        'destructiveHint': True,
        'idempotentHint': False,
        'openWorldHint': True,
    }
    assert c['authority']['requires_explicit_authorization'] is True


def test_read_only_annotation_allows_read_authority():
    c = normalize_tool_contract({
        'name': 'search',
        'annotations': {'readOnlyHint': True, 'destructiveHint': False, 'idempotentHint': True, 'openWorldHint': True},
        'inputSchema': {'type': 'object'},
    }, '2026-07-28', trusted_server=True)
    assert c['authority']['mode'] == 'read'
    assert c['authority']['requires_explicit_authorization'] is False


def test_modern_era_requires_per_request_protocol_version():
    r = protocol_preflight('2026-07-28', request_meta={})
    assert r['allowed'] is False
    assert r['reason'] == 'missing_per_request_protocol_version'
    assert r['discovery_method'] == 'server/discover'


def test_modern_era_accepts_matching_per_request_protocol_version():
    r = protocol_preflight('2026-07-28', request_meta={'protocolVersion': '2026-07-28'})
    assert r['allowed'] is True
    assert r['discovery_method'] == 'server/discover'


def test_handshake_era_uses_initialize_without_per_request_version():
    r = protocol_preflight('2025-11-25', request_meta={})
    assert r['allowed'] is True
    assert r['discovery_method'] == 'initialize'


def test_protocol_mismatch_is_blocked():
    r = protocol_preflight('2026-07-28', request_meta={'protocolVersion': '2025-11-25'})
    assert r['allowed'] is False
    assert r['reason'] == 'protocol_version_mismatch'


def test_trace_redacts_sensitive_fields_and_keeps_audit_keys():
    trace = build_tool_trace(
        capability='research.search', provider='exa', tool='web_search', protocol_version='2026-07-28',
        plan_digest='abc123', outcome='ok', attributes={'token': 'secret', 'query': 'mcp safety', 'authorization': 'Bearer x'}
    )
    assert trace['span_name'] == 'execute_tool'
    assert trace['attributes']['capability'] == 'research.search'
    assert trace['attributes']['plan_digest'] == 'abc123'
    assert trace['attributes']['query'] == 'mcp safety'
    assert 'token' not in trace['attributes']
    assert 'authorization' not in trace['attributes']


def test_untrusted_server_annotations_do_not_grant_read_authority():
    c = normalize_tool_contract({
        'name': 'search',
        'annotations': {'readOnlyHint': True, 'destructiveHint': False},
        'inputSchema': {'type': 'object'},
    }, '2026-07-28', trusted_server=False)
    assert c['authority']['requires_explicit_authorization'] is True
    assert c['authority']['reason'] == 'untrusted_annotations'


def test_modern_era_accepts_canonical_namespaced_protocol_meta():
    r = protocol_preflight('2026-07-28', request_meta={'io.modelcontextprotocol/protocolVersion': '2026-07-28'})
    assert r['allowed'] is True
