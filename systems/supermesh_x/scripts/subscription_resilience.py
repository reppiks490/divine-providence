"""Resilient MCP subscription restart semantics for 2026-07-28 streams."""
import hashlib, json

class SubscriptionResilience:
    def __init__(self, base_backoff_ms=1000, max_backoff_ms=30000):
        self.base=max(0,int(base_backoff_ms)); self.cap=max(self.base,int(max_backoff_ms))
        self._failures={}; self._closed=set(); self._active=set()

    def acknowledged(self, subscription_id, provider='default'):
        sid=str(subscription_id); p=str(provider)
        self._active.add(sid); self._closed.discard(sid); self._failures[p]=0
        return {'subscription_id':sid,'provider':p,'active':True}

    def stream_ended(self, subscription_id, provider='default', now_ms=0, abrupt=False):
        sid=str(subscription_id); p=str(provider); now=int(now_ms)
        self._active.discard(sid); self._closed.add(sid)
        n=self._failures.get(p,0)+1; self._failures[p]=n
        backoff=min(self.cap, self.base*(2**(n-1)))
        body={'subscription_id':sid,'provider':p,'ended_at_ms':now,'abrupt':bool(abrupt),
              'backoff_ms':backoff,'refetch_required':True,'replay_allowed':False,
              'reuse_subscription_id':False}
        digest=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return {**body,'retry_after_ms':now+backoff,'receipt_hash':digest}

    def accept_event(self, subscription_id, observed_at_ms):
        sid=str(subscription_id)
        if sid in self._closed: raise ValueError('event belongs to closed subscription')
        if sid not in self._active: raise ValueError('subscription acknowledgment required')
        return {'accepted':True,'subscription_id':sid,'observed_at_ms':int(observed_at_ms)}
