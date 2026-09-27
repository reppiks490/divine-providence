"""Deterministic cross-SDK MCP conformance fixtures.

Fixtures model wire behavior only; they never grant tool/write authority.
"""
import hashlib, json

_SECRET_KEYS={'authorization','token','secret','api_key','password','cookie'}
_TASKS_EXTENSION_SDKS={'typescript-v2'}

def _safe_meta(meta):
    return {str(k):v for k,v in (meta or {}).items() if str(k).lower() not in _SECRET_KEYS}

def _receipt(body):
    return hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def evaluate_fixture(fixture):
    sdk=str(fixture.get('sdk','unknown'))
    era=str(fixture.get('era','unknown'))
    discovery=str(fixture.get('discovery',''))
    meta=_safe_meta(fixture.get('request_meta',{}))
    failures=[]
    if era=='modern':
        if discovery!='server/discover': failures.append('modern_discovery_mismatch')
        pv=meta.get('io.modelcontextprotocol/protocolVersion') or meta.get('protocolVersion') or meta.get('protocol_version')
        if not pv: failures.append('protocol_meta_missing')
        elif pv!='2026-07-28': failures.append('protocol_version_mismatch')
    elif era=='legacy':
        if discovery!='initialize': failures.append('legacy_discovery_mismatch')
    else:
        failures.append('unknown_protocol_era')
    if bool(fixture.get('tasks_extension')) and sdk not in _TASKS_EXTENSION_SDKS:
        failures.append('sdk_tasks_extension_unsupported')
    body={'sdk':sdk,'era':era,'discovery':discovery,'request_meta':meta,'tasks_extension':bool(fixture.get('tasks_extension')),'failures':failures,'conformant':not failures}
    body['receipt_hash']=_receipt(body)
    return body

def default_fixture_matrix():
    return [
      {'sdk':'typescript-v2','era':'modern','discovery':'server/discover','request_meta':{'protocolVersion':'2026-07-28'},'tasks_extension':True},
      {'sdk':'python-v2','era':'modern','discovery':'server/discover','request_meta':{'protocolVersion':'2026-07-28'},'tasks_extension':False},
      {'sdk':'python-v1','era':'legacy','discovery':'initialize','request_meta':{},'tasks_extension':False},
    ]
