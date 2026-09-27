"""Fail-closed provenance vectors for official MCP release conformance requirements."""
from __future__ import annotations
import hashlib, json

OFFICIAL_SOURCE='https://github.com/modelcontextprotocol/conformance'
REVISIONS={
 '2025-11-25': {'lifecycle':'stateful_initialize','required_meta':[]},
 '2026-07-28': {'lifecycle':'stateless_request_meta','required_meta':['io.modelcontextprotocol/protocolVersion','io.modelcontextprotocol/clientCapabilities']},
}
ROLES={'server','client'}
class ConformanceVectorError(ValueError): pass

def _receipt(body):
    raw=json.dumps(body,sort_keys=True,separators=(',',':')).encode()
    return hashlib.sha256(raw).hexdigest()

def build_vector(revision, scenario, *, role, source=OFFICIAL_SOURCE, requirement_set=False):
    if source != OFFICIAL_SOURCE: raise ConformanceVectorError('untrusted conformance source')
    if revision not in REVISIONS: raise ConformanceVectorError('unsupported MCP revision')
    if role not in ROLES: raise ConformanceVectorError('unsupported conformance role')
    if not str(scenario).strip(): raise ConformanceVectorError('scenario required')
    spec=REVISIONS[revision]
    body={'source':source,'revision':revision,'scenario':str(scenario),'role':role,
          'requirement_set':bool(requirement_set),'lifecycle':spec['lifecycle'],
          'required_meta':list(spec['required_meta'])}
    return {**body,'receipt_sha256':_receipt(body)}

def validate_vector(vector, *, release_claim=False):
    if vector.get('source') != OFFICIAL_SOURCE: raise ConformanceVectorError('untrusted conformance source')
    revision=vector.get('revision'); role=vector.get('role')
    if revision not in REVISIONS or role not in ROLES: raise ConformanceVectorError('unsupported vector')
    spec=REVISIONS[revision]
    if vector.get('lifecycle') != spec['lifecycle']: raise ConformanceVectorError('lifecycle mismatch')
    if list(vector.get('required_meta',[])) != spec['required_meta']: raise ConformanceVectorError('required metadata mismatch')
    if release_claim and not vector.get('requirement_set'): raise ConformanceVectorError('release claim requires frozen requirement set')
    body={k:vector[k] for k in ('source','revision','scenario','role','requirement_set','lifecycle','required_meta')}
    if vector.get('receipt_sha256') != _receipt(body): raise ConformanceVectorError('vector receipt mismatch')
    return {'valid':True,'revision':revision,'release_claim_eligible':bool(vector.get('requirement_set'))}
