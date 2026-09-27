"""Provider-neutral quota normalization and bounded half-open probe admission."""
import hashlib, json
_SECRET={'token','secret','authorization','api_key','apikey','password','cookie'}
def _hash(body): return hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def normalize_quota(provider, remaining=None, limit=None, remaining_ratio=None, reset_at_ms=None, now_ms=0, detail=None):
    degraded=False
    if remaining_ratio is not None:
        try: h=float(remaining_ratio)
        except (TypeError,ValueError): h=0.0; degraded=True
    elif remaining is not None and limit is not None:
        try:
            lim=float(limit); rem=float(remaining)
            if lim<=0: h=0.0; degraded=True
            else: h=rem/lim
        except (TypeError,ValueError): h=0.0; degraded=True
    else: h=None
    if h is not None:
        if h<0 or h>1: degraded=True
        h=round(max(0.0,min(1.0,h)),6)
    reset=max(0,int(reset_at_ms)-int(now_ms)) if reset_at_ms is not None else None
    body={'provider':str(provider),'headroom':h,'reset_in_ms':reset,'degraded':degraded,'observed_at_ms':int(now_ms)}
    body['receipt_hash']=_hash(body); return body
class HalfOpenProbeGate:
    def __init__(self,base_interval_ms=1000,jitter_fraction=.25,min_headroom=.05,max_concurrent=1):
        self.base=max(1,int(base_interval_ms)); self.jitter=max(0.0,min(1.0,float(jitter_fraction)))
        self.min_headroom=max(0.0,min(1.0,float(min_headroom))); self.max_concurrent=max(1,int(max_concurrent))
    def decide(self,provider,now_ms,quota_headroom=None,in_flight=0):
        q=1.0 if quota_headroom is None else max(0.0,min(1.0,float(quota_headroom)))
        allowed=q>=self.min_headroom and int(in_flight)<self.max_concurrent
        seed=int(hashlib.sha256(str(provider).encode()).hexdigest()[:8],16)/0xffffffff
        delay=self.base+int(self.base*self.jitter*seed)
        reason='allowed' if allowed else ('quota_headroom' if q<self.min_headroom else 'probe_concurrency')
        body={'provider':str(provider),'allowed':allowed,'reason':reason,'quota_headroom':round(q,6),'next_probe_delay_ms':delay,'observed_at_ms':int(now_ms)}
        body['receipt_hash']=_hash(body); return body
