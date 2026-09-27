"""Fenced isolated-runtime driver contract for SuperMesh-X v2.6.

The included backend is an in-memory conformance harness, not a VM/container
launcher. Real backends must enforce the same lifecycle, resource and fencing
contract before they may be admitted.
"""
from __future__ import annotations
import copy, hashlib, ipaddress, json

class RuntimeDriverError(RuntimeError): pass
class StaleRuntimeFence(RuntimeDriverError): pass

def _digest(v):
    raw=json.dumps(v,sort_keys=True,separators=(',',':')).encode()
    return 'sha256:'+hashlib.sha256(raw).hexdigest()

_REQUIRED=('create','start','heartbeat','stop','destroy','inspect','cleanup_orphans')
def validate_runtime_backend(backend):
    missing=[n for n in _REQUIRED if not callable(getattr(backend,n,None))]
    return {'schema':1,'conformant':not missing,'missing':missing,'fencing_required':True,'resource_enforcement_required':True}

def classify_egress_target(host):
    h=str(host or '').strip().lower().rstrip('.').strip('[]')
    if not h: return {'allowed':False,'reason':'empty'}
    if h in {'localhost','localhost.localdomain'} or h.endswith('.local'):
        return {'allowed':False,'reason':'local_name'}
    try: ip=ipaddress.ip_address(h)
    except ValueError: return {'allowed':True,'reason':'public_hostname'}
    blocked=ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved
    return {'allowed':not blocked,'reason':'non_public_ip' if blocked else 'public_ip'}

class InMemorySandboxBackend:
    """Deterministic enforcement harness used to prove the backend contract."""
    def __init__(self): self._runs={}
    def _current(self,run_id,worker_id,token):
        r=self._runs.get(run_id)
        if not r or r['worker_id']!=worker_id or int(r['fencing_token'])!=int(token):
            raise StaleRuntimeFence('runtime ownership is stale or fenced')
        return r
    def create(self,run_id,worker_id,token,limits,secret_handles):
        if run_id in self._runs and self._runs[run_id]['status']!='destroyed': raise RuntimeDriverError('runtime already exists')
        if not limits or any(int(v)<=0 for v in limits.values()): raise RuntimeDriverError('positive enforced resource limits required')
        self._runs[run_id]={'run_id':run_id,'worker_id':worker_id,'fencing_token':int(token),'status':'created','enforced_limits':copy.deepcopy(limits),'secret_handle_count':len(secret_handles),'orphan':False,'last_heartbeat_ms':None}
    def start(self,run_id,worker_id,token,now_ms): self._current(run_id,worker_id,token).update(status='running',last_heartbeat_ms=int(now_ms))
    def heartbeat(self,run_id,worker_id,token,now_ms):
        r=self._current(run_id,worker_id,token)
        if r['status']!='running': raise RuntimeDriverError('heartbeat requires running runtime')
        r['last_heartbeat_ms']=int(now_ms)
    def stop(self,run_id,worker_id,token,now_ms,reason): self._current(run_id,worker_id,token).update(status='stopped',stopped_at_ms=int(now_ms),stop_reason=str(reason))
    def destroy(self,run_id,worker_id,token,now_ms): self._current(run_id,worker_id,token).update(status='destroyed',destroyed_at_ms=int(now_ms),secret_handle_count=0,orphan=False)
    def inspect(self,run_id): return copy.deepcopy(self._runs[run_id])
    def force_takeover(self,run_id,worker_id,token): self._runs[run_id].update(worker_id=worker_id,fencing_token=int(token))
    def mark_orphan(self,run_id): self._runs[run_id]['orphan']=True
    def cleanup_orphans(self,now_ms):
        cleaned=[]
        for rid,r in self._runs.items():
            if r.get('orphan') and r['status']!='destroyed':
                r.update(status='destroyed',destroyed_at_ms=int(now_ms),secret_handle_count=0,orphan=False); cleaned.append(rid)
        return sorted(cleaned)

class IsolatedRuntimeDriver:
    def __init__(self,backend):
        c=validate_runtime_backend(backend)
        if not c['conformant']: raise TypeError('runtime backend missing: '+','.join(c['missing']))
        self.backend=backend
    def _receipt(self,run_id,worker_id,token,status,**extra):
        out={'schema':1,'run_id':run_id,'worker_id':worker_id,'fencing_token':int(token),'status':status}; out.update(extra); return out
    def create(self,run_id,worker_id,fencing_token,reservation,secret_refs=None):
        if reservation.get('run_id')!=run_id: raise RuntimeDriverError('reservation/run mismatch')
        limits={str(k):int(v) for k,v in (reservation.get('resources') or {}).items()}
        refs=sorted(set(secret_refs or []))
        if any(not isinstance(x,str) or not x.startswith('secretref://') for x in refs): raise RuntimeDriverError('secrets must be secretref:// references')
        # Translate refs to one-way ephemeral handles before crossing backend boundary.
        handles=[_digest({'run_id':run_id,'ref':x,'fence':int(fencing_token)}) for x in refs]
        self.backend.create(run_id,worker_id,fencing_token,limits,handles)
        return self._receipt(run_id,worker_id,fencing_token,'created',enforced_limits=copy.deepcopy(limits),secret_handle_count=len(handles),secret_ref_digest=_digest(refs))
    def start(self,run_id,worker_id,fencing_token,now_ms): self.backend.start(run_id,worker_id,fencing_token,now_ms); return self._receipt(run_id,worker_id,fencing_token,'running',at_ms=int(now_ms))
    def heartbeat(self,run_id,worker_id,fencing_token,now_ms): self.backend.heartbeat(run_id,worker_id,fencing_token,now_ms); return self._receipt(run_id,worker_id,fencing_token,'running',heartbeat_at_ms=int(now_ms))
    def stop(self,run_id,worker_id,fencing_token,now_ms,reason): self.backend.stop(run_id,worker_id,fencing_token,now_ms,reason); return self._receipt(run_id,worker_id,fencing_token,'stopped',at_ms=int(now_ms),reason=str(reason))
    def destroy(self,run_id,worker_id,fencing_token,now_ms): self.backend.destroy(run_id,worker_id,fencing_token,now_ms); return self._receipt(run_id,worker_id,fencing_token,'destroyed',at_ms=int(now_ms))
    def kill_plan(self,run_id,grace_ms=1000):
        grace=int(grace_ms)
        if grace<0: raise RuntimeDriverError('grace_ms must be nonnegative')
        return {'schema':1,'run_id':run_id,'executed':False,'steps':[{'signal':'TERM','after_ms':0},{'signal':'KILL','after_ms':grace}]}
    def cleanup_orphans(self,now_ms):
        cleaned=self.backend.cleanup_orphans(now_ms)
        return {'schema':1,'executed':True,'cleaned':cleaned,'count':len(cleaned),'at_ms':int(now_ms)}
