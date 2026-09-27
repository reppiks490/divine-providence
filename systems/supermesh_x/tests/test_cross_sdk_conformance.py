import pytest
from scripts.cross_sdk_conformance import evaluate_fixture, default_fixture_matrix


def test_modern_typescript_fixture_requires_discover_and_per_request_meta():
    r=evaluate_fixture({'sdk':'typescript-v2','era':'modern','discovery':'server/discover','request_meta':{'io.modelcontextprotocol/protocolVersion':'2026-07-28'},'tasks_extension':True})
    assert r['conformant'] is True


def test_modern_missing_protocol_meta_fails_closed():
    r=evaluate_fixture({'sdk':'typescript-v2','era':'modern','discovery':'server/discover','request_meta':{},'tasks_extension':True})
    assert r['conformant'] is False and 'protocol_meta_missing' in r['failures']


def test_legacy_fixture_requires_initialize_not_discover():
    ok=evaluate_fixture({'sdk':'python-v1','era':'legacy','discovery':'initialize','request_meta':{},'tasks_extension':False})
    bad=evaluate_fixture({'sdk':'python-v1','era':'legacy','discovery':'server/discover','request_meta':{},'tasks_extension':False})
    assert ok['conformant'] is True
    assert 'legacy_discovery_mismatch' in bad['failures']


def test_python_v2_does_not_assume_tasks_extension_support():
    r=evaluate_fixture({'sdk':'python-v2','era':'modern','discovery':'server/discover','request_meta':{'protocolVersion':'2026-07-28'},'tasks_extension':True})
    assert r['conformant'] is False
    assert 'sdk_tasks_extension_unsupported' in r['failures']


def test_fixture_receipt_excludes_secrets():
    r=evaluate_fixture({'sdk':'typescript-v2','era':'modern','discovery':'server/discover','request_meta':{'protocolVersion':'2026-07-28','authorization':'Bearer secret'},'tasks_extension':False})
    assert 'secret' not in str(r).lower()
    assert len(r['receipt_hash'])==64


def test_default_matrix_covers_modern_and_legacy_cross_sdk_paths():
    m=default_fixture_matrix()
    assert {'typescript-v2','python-v2','python-v1'} <= {x['sdk'] for x in m}
    assert {'modern','legacy'} <= {x['era'] for x in m}
