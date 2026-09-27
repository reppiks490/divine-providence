"""Adaptive provider health feedback from freshness and subscription reliability signals."""
import hashlib, json, math

_WEIGHTS={'cache_refresh_failed':0.12,'cache_stale':0.05,'subscription_lost':0.18,'reconnect_failed':0.22,'schema_drift':0.10}
_SECRET_KEYS={'api_key','apikey','token','secret','authorization','password','cookie'}

class ProviderHealthFeedback:
    def __init__(self, provider, baseline_health=1.0, half_life_ms=60000, open_threshold=0.45, cooldown_ms=30000):
        self.provider=str(provider); self.baseline=max(0.0,min(1.0,float(baseline_health)))
        self.half_life=max(1,int(half_life_ms)); self.open_threshold=max(0.0,min(1.0,float(open_threshold)))
        self.cooldown=max(0,int(cooldown_ms)); self.events=[]; self.opened_at=None; self.probe_ok=False

    def record(self, event, observed_at_ms, detail=None):
        event=str(event); t=int(observed_at_ms)
        if event=='success':
            self.events=[e for e in self.events if e['event']!='success']
            self.events.append({'event':'success','at':t,'weight':-0.10})
            self.opened_at=None; self.probe_ok=True
            return
        w=_WEIGHTS.get(event,0.08)
        self.events.append({'event':event,'at':t,'weight':w})

    def _penalty(self, now):
        total=0.0
        for e in self.events:
            age=max(0,now-e['at']); decay=0.5**(age/self.half_life)
            total += e['weight']*decay
        return max(0.0,total)

    def score(self, now_ms):
        now=int(now_ms); health=max(0.0,min(self.baseline,self.baseline-self._penalty(now)))
        if self.opened_at is None and health < self.open_threshold and not self.probe_ok: self.opened_at=now
        if health >= self.open_threshold: self.probe_ok=False
        circuit='closed'
        if self.opened_at is not None:
            circuit='half_open' if now-self.opened_at>=self.cooldown else 'open'
        body={'provider':self.provider,'health':round(health,6),'baseline_health':round(self.baseline,6),
              'circuit':circuit,'event_count':len(self.events),'observed_at_ms':now}
        body['receipt_hash']=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return body

def rank_providers(providers, now_ms):
    rows=[p.score(now_ms) for p in providers]
    order={'closed':0,'half_open':1,'open':2}
    return sorted(rows,key=lambda r:(order[r['circuit']],-r['health'],r['provider']))
