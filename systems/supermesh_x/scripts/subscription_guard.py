"""Modern MCP subscription event dedupe, debounce, and invalidation receipts."""
import hashlib, json

class SubscriptionGuard:
    def __init__(self, debounce_ms=250):
        self.debounce_ms=max(0,int(debounce_ms)); self._acks={}; self._seen=set(); self._last={}
    def acknowledge(self, subscription_id, notifications):
        self._acks[str(subscription_id)]={k for k,v in (notifications or {}).items() if v}
    def ingest(self, event):
        sid=str(event['subscription_id']); typ=str(event['type']); eid=str(event['event_id']); ts=int(event['observed_at_ms'])
        if sid not in self._acks: raise ValueError('subscription acknowledgment required before delivery')
        if typ not in self._acks[sid]: raise ValueError('notification type not acknowledged')
        key=(sid,eid)
        if key in self._seen: return {'accepted':False,'invalidate':False,'reason':'duplicate'}
        self._seen.add(key)
        last=self._last.get((sid,typ))
        if last is not None and ts-last < self.debounce_ms:
            return {'accepted':False,'invalidate':False,'reason':'debounced'}
        self._last[(sid,typ)]=ts
        body={'subscription_id':sid,'notification_type':typ,'event_id':eid,'observed_at_ms':ts,'action':'invalidate'}
        digest=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return {'accepted':True,'invalidate':True,'reason':'accepted','receipt':{**body,'receipt_hash':digest}}
