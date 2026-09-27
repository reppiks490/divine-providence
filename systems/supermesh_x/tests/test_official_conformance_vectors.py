import pytest
from scripts.official_conformance_vectors import build_vector, validate_vector, ConformanceVectorError

OFFICIAL='https://github.com/modelcontextprotocol/conformance'

def test_legacy_vector_requires_stateful_initialize():
    v=build_vector('2025-11-25','server-initialize',role='server',source=OFFICIAL,requirement_set=True)
    assert v['lifecycle']=='stateful_initialize'
    assert validate_vector(v)['valid'] is True

def test_modern_vector_requires_stateless_request_meta():
    v=build_vector('2026-07-28','server-discover',role='server',source=OFFICIAL,requirement_set=True)
    assert v['lifecycle']=='stateless_request_meta'
    assert v['required_meta']==['io.modelcontextprotocol/protocolVersion','io.modelcontextprotocol/clientCapabilities']

def test_release_claim_requires_frozen_requirement_set():
    v=build_vector('2026-07-28','server-discover',role='server',source=OFFICIAL,requirement_set=False)
    with pytest.raises(ConformanceVectorError): validate_vector(v, release_claim=True)

def test_unknown_source_revision_and_role_fail_closed():
    for kwargs in [
        dict(revision='2026-07-28',scenario='x',role='server',source='https://evil.invalid',requirement_set=True),
        dict(revision='2099-01-01',scenario='x',role='server',source=OFFICIAL,requirement_set=True),
        dict(revision='2026-07-28',scenario='x',role='admin',source=OFFICIAL,requirement_set=True),
    ]:
        with pytest.raises(ConformanceVectorError): build_vector(**kwargs)

def test_lifecycle_tampering_fails_closed():
    v=build_vector('2026-07-28','server-discover',role='server',source=OFFICIAL,requirement_set=True)
    v['lifecycle']='stateful_initialize'
    with pytest.raises(ConformanceVectorError): validate_vector(v)
