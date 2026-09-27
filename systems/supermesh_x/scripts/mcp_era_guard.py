#!/usr/bin/env python3
"""MCP protocol-era preflight, conservative tool annotations, and safe traces."""

from __future__ import annotations

from copy import deepcopy

MODERN_ERA = '2026-07-28'
SENSITIVE_KEYS = {
    'authorization', 'api_key', 'apikey', 'access_token', 'refresh_token',
    'token', 'password', 'secret', 'cookie', 'set-cookie', 'credential', 'credentials',
}


def _annotations(tool):
    raw = dict((tool or {}).get('annotations') or {})
    # MCP annotation defaults are intentionally conservative.
    return {
        'readOnlyHint': bool(raw.get('readOnlyHint', raw.get('read_only_hint', False))),
        'destructiveHint': bool(raw.get('destructiveHint', raw.get('destructive_hint', True))),
        'idempotentHint': bool(raw.get('idempotentHint', raw.get('idempotent_hint', False))),
        'openWorldHint': bool(raw.get('openWorldHint', raw.get('open_world_hint', True))),
    }


def normalize_tool_contract(tool, protocol_version, trusted_server=False):
    """Normalize a discovered MCP tool into a cross-runtime safety contract."""
    row = deepcopy(tool or {})
    ann = _annotations(row)
    read_only = ann['readOnlyHint'] and not ann['destructiveHint']
    trusted_read = bool(trusted_server) and read_only
    authority = {
        'mode': 'read' if trusted_read else 'external_write_or_unknown',
        'requires_explicit_authorization': not trusted_read,
        'reason': 'trusted_read_only' if trusted_read else ('untrusted_annotations' if not trusted_server else 'write_or_unknown'),
    }
    return {
        'name': row.get('name'),
        'protocol_version': str(protocol_version),
        'input_schema': row.get('inputSchema') or row.get('input_schema') or {},
        'output_schema': row.get('outputSchema') or row.get('output_schema'),
        'annotations': ann,
        'authority': authority,
    }


def protocol_preflight(protocol_version, request_meta=None):
    """Fail closed on protocol-era mismatch before a provider call."""
    version = str(protocol_version)
    meta = dict(request_meta or {})
    modern = version >= MODERN_ERA
    discovery = 'server/discover' if modern else 'initialize'
    supplied = (meta.get('io.modelcontextprotocol/protocolVersion') or meta.get('protocolVersion') or meta.get('protocol_version'))

    if modern and not supplied:
        return {'allowed': False, 'reason': 'missing_per_request_protocol_version', 'discovery_method': discovery}
    if supplied and str(supplied) != version:
        return {'allowed': False, 'reason': 'protocol_version_mismatch', 'discovery_method': discovery}
    return {'allowed': True, 'reason': 'allowed', 'discovery_method': discovery}


def _redact(attributes):
    clean = {}
    for key, value in dict(attributes or {}).items():
        if str(key).lower() in SENSITIVE_KEYS:
            continue
        clean[key] = value
    return clean


def build_tool_trace(capability, provider, tool, protocol_version, plan_digest, outcome, attributes=None):
    """Build a portable execute_tool trace without persisting credentials."""
    attrs = _redact(attributes)
    attrs.update({
        'capability': str(capability),
        'provider': str(provider),
        'tool': str(tool),
        'protocol_version': str(protocol_version),
        'plan_digest': str(plan_digest),
        'outcome': str(outcome),
    })
    return {'span_name': 'execute_tool', 'attributes': attrs}
