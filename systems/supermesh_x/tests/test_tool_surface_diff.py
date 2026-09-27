import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from tool_surface_diff import fingerprint_tool, diff_tool_surfaces


def tool(name, props=None, required=None, description=''):
    return {
        'name': name,
        'description': description,
        'inputSchema': {
            'type': 'object',
            'properties': props or {},
            'required': required or [],
        },
    }


def test_fingerprint_is_stable_for_key_order():
    a = tool('quote', {'symbol': {'type':'string'}, 'limit': {'type':'integer'}}, ['symbol'])
    b = tool('quote', {'limit': {'type':'integer'}, 'symbol': {'type':'string'}}, ['symbol'])
    assert fingerprint_tool(a) == fingerprint_tool(b)


def test_detects_added_tool_as_nonbreaking():
    before = [tool('quote')]
    after = [tool('quote'), tool('history')]
    diff = diff_tool_surfaces(before, after)
    assert diff['added'] == ['history']
    assert diff['breaking'] is False


def test_removed_tool_is_breaking():
    diff = diff_tool_surfaces([tool('quote')], [])
    assert diff['removed'] == ['quote']
    assert diff['breaking'] is True


def test_new_required_parameter_is_breaking():
    before = [tool('quote', {'symbol': {'type':'string'}}, ['symbol'])]
    after = [tool('quote', {'symbol': {'type':'string'}, 'exchange': {'type':'string'}}, ['symbol','exchange'])]
    diff = diff_tool_surfaces(before, after)
    assert diff['changed'][0]['name'] == 'quote'
    assert diff['changed'][0]['classification'] == 'breaking'
    assert diff['breaking'] is True


def test_optional_parameter_addition_is_compatible():
    before = [tool('quote', {'symbol': {'type':'string'}}, ['symbol'])]
    after = [tool('quote', {'symbol': {'type':'string'}, 'currency': {'type':'string'}}, ['symbol'])]
    diff = diff_tool_surfaces(before, after)
    assert diff['changed'][0]['classification'] == 'compatible'
    assert diff['breaking'] is False
