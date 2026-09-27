import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from adapter_negotiation import negotiate_adapter


def test_prefers_native_then_mcp_then_rest():
    provider={'name':'p','transports':['rest','mcp_http','native_tool'],'auth_modes':['oauth2']}
    runtime={'supported_transports':['native_tool','mcp_http','rest'],'credential_modes':['oauth2']}
    result=negotiate_adapter(provider,runtime)
    assert result['compatible'] is True
    assert result['transport']=='native_tool'


def test_auth_mismatch_blocks_execution_without_guessing():
    provider={'name':'p','transports':['mcp_http'],'auth_modes':['oauth2']}
    runtime={'supported_transports':['mcp_http'],'credential_modes':['api_key']}
    result=negotiate_adapter(provider,runtime)
    assert result['compatible'] is False
    assert result['reason']=='auth_unavailable'
