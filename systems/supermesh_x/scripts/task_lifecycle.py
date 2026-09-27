from datetime import datetime, timezone
import hashlib, json
TERMINAL={'completed','failed','cancelled'}
VALID=TERMINAL|{'working','input_required'}

def _dt(v):
    return datetime.fromisoformat(v.replace('Z','+00:00'))

def normalize_task(task, now=None, method='tasks/get'):
    t=dict(task or {})
    tid=t.get('taskId',''); status=t.get('status')
    if len(tid)<24 or status not in VALID:
        return {'usable':False,'reason':'invalid_task'}
    ttl=t.get('ttlMs')
    if ttl is not None:
        current=_dt(now) if now else datetime.now(timezone.utc)
        if current > _dt(t['createdAt']) + __import__('datetime').timedelta(milliseconds=int(ttl)):
            return {'usable':False,'reason':'ttl_elapsed','task_id':tid,'status':status}
    return {'usable':True,'reason':'ok','task_id':tid,'status':status,
            'ttl_ms':ttl,'poll_interval_ms':t.get('pollIntervalMs'),
            'routing_headers':{'Mcp-Name':tid,'Mcp-Method':method},
            'terminal':status in TERMINAL}

def build_poll_directive(task, default_ms=1000, min_ms=100, max_ms=60000):
    n=normalize_task(task)
    if not n['usable'] or n.get('terminal'):
        return {'poll':False,'reason':n['reason'] if not n['usable'] else 'terminal'}
    wait=task.get('pollIntervalMs',default_ms)
    wait=max(min_ms,min(max_ms,int(wait)))
    return {'poll':True,'wait_ms':wait,'routing_headers':n['routing_headers']}

def build_task_receipt(task, logical_operation_id, trace_id=None, secrets=None):
    n=normalize_task(task)
    payload={'logical_operation_id':logical_operation_id,'trace_id':trace_id,'task_id':n.get('task_id'),
             'status':n.get('status'),'usable':n.get('usable'),'reason':n.get('reason'),
             'last_updated_at':task.get('lastUpdatedAt'),'ttl_ms':task.get('ttlMs')}
    payload['receipt_hash']=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return payload
