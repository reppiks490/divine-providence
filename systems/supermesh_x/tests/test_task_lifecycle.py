import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from task_lifecycle import normalize_task, build_poll_directive, build_task_receipt

def task(**kw):
    x={'taskId':'0123456789abcdef0123456789abcdef','status':'working','createdAt':'2026-09-25T00:00:00Z','lastUpdatedAt':'2026-09-25T00:00:01Z','ttlMs':60000,'pollIntervalMs':5000}
    x.update(kw); return x

def test_normalize_preserves_server_poll_and_ttl_and_routes_by_task_id():
    n=normalize_task(task(), now='2026-09-25T00:00:10Z')
    assert n['usable'] is True
    assert n['routing_headers']=={'Mcp-Name':'0123456789abcdef0123456789abcdef','Mcp-Method':'tasks/get'}
    assert n['poll_interval_ms']==5000 and n['ttl_ms']==60000

def test_expired_task_fails_closed():
    n=normalize_task(task(ttlMs=1000), now='2026-09-25T00:00:02.001Z')
    assert n['usable'] is False and n['reason']=='ttl_elapsed'

def test_poll_directive_honors_server_interval_and_terminal_state():
    assert build_poll_directive(task(createdAt='2099-01-01T00:00:00Z'))['wait_ms']==5000
    assert build_poll_directive(task(status='completed'))['poll'] is False

def test_receipt_correlates_one_logical_operation_without_secrets():
    r=build_task_receipt(task(), logical_operation_id='op-7', trace_id='trace-9', secrets={'token':'nope'})
    assert r['logical_operation_id']=='op-7' and r['trace_id']=='trace-9'
    assert 'secrets' not in r and 'token' not in str(r)
