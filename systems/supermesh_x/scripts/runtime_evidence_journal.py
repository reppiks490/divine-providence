"""SuperMesh-X v2.9 provider-neutral runtime evidence journal."""
from __future__ import annotations
import copy, hashlib, ipaddress, json, re

class EvidenceError(RuntimeError): pass

def _canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True)
def _digest(v): return "sha256:"+hashlib.sha256(_canon(v).encode()).hexdigest()
def _secret_safe(v):
    s=_canon(v).lower()
    return not any(x in s for x in ("secretref://","password","private_key","api_key","bearer "))
def _public_ip(v):
    try: ip=ipaddress.ip_address(str(v).strip("[]"))
    except ValueError: return False
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved)

class EvidenceJournal:
    def __init__(self,run_id):
        self.run_id=str(run_id); self._events=[]; self._max_fence=-1; self._reconcile={}
    def append(self,kind,payload):
        if not _secret_safe(payload): raise EvidenceError("secret-bearing evidence forbidden")
        prev=self._events[-1]["digest"] if self._events else "GENESIS"
        e={"schema":1,"run_id":self.run_id,"seq":len(self._events)+1,"kind":str(kind),
           "payload":copy.deepcopy(payload),"prev_digest":prev}
        e["digest"]=_digest({k:e[k] for k in ("schema","run_id","seq","kind","payload","prev_digest")})
        self._events.append(e); return copy.deepcopy(e)
    def verify(self):
        prev="GENESIS"
        for i,e in enumerate(self._events,1):
            if e.get("seq")!=i or e.get("prev_digest")!=prev: raise EvidenceError("journal chain broken")
            want=_digest({k:e[k] for k in ("schema","run_id","seq","kind","payload","prev_digest")})
            if e.get("digest")!=want: raise EvidenceError("journal digest mismatch")
            prev=e["digest"]
        return True
    def reconcile(self,worker_id,fencing_token,action,reason):
        f=int(fencing_token)
        if f<self._max_fence: raise EvidenceError("stale reconciliation fence")
        key=(str(worker_id),f,str(action),str(reason))
        if key in self._reconcile: return copy.deepcopy(self._reconcile[key])
        self._max_fence=max(self._max_fence,f)
        e=self.append("reconcile",{"worker_id":str(worker_id),"fencing_token":f,"action":str(action),"reason":str(reason)})
        self._reconcile[key]=e
        return copy.deepcopy(e)
    def export(self):
        self.verify(); return copy.deepcopy(self._events)

def normalize_resources(v):
    required=("cpu_millicores","memory_bytes","storage_bytes","gpu_units")
    if set(v)!=set(required): raise EvidenceError("resource units must be canonical and explicit")
    out={k:int(v[k]) for k in required}
    if any(x<0 for x in out.values()) or out["cpu_millicores"]<=0 or out["memory_bytes"]<=0 or out["storage_bytes"]<=0:
        raise EvidenceError("invalid normalized resource quantity")
    return out

def verify_termination_tree(root_pid,alive_by_pid,edges):
    root=int(root_pid); children={}
    for p,c in edges: children.setdefault(int(p),set()).add(int(c))
    seen=set(); stack=[root]
    while stack:
        p=stack.pop()
        if p in seen: continue
        seen.add(p); stack.extend(children.get(p,()))
    live=sorted(p for p in seen if bool(alive_by_pid.get(p,False)))
    if live: raise EvidenceError("process descendants still alive: "+",".join(map(str,live)))
    return {"schema":1,"verified":True,"root_pid":root,"observed_pids":sorted(seen),"tree_digest":_digest({"root":root,"edges":sorted((int(a),int(b)) for a,b in edges)})}

class ResolverPinSession:
    def __init__(self,host,answers):
        self.host=str(host); self.pins=self._validate(answers)
    def _validate(self,answers):
        pins=tuple(sorted(set(str(x) for x in answers)))
        if not pins or any(not _public_ip(x) for x in pins): raise EvidenceError("resolver answer contains non-public IP")
        return pins
    def verify_refresh(self,answers):
        fresh=self._validate(answers)
        if not set(fresh).issubset(set(self.pins)): raise EvidenceError("DNS rebinding/new answer outside pinned set")
        return {"schema":1,"allowed":True,"pin_digest":_digest(self.pins)}
    def verify_connect(self,connected_ip):
        ip=str(connected_ip)
        if ip not in self.pins or not _public_ip(ip): raise EvidenceError("socket peer is not pinned public IP")
        return {"schema":1,"allowed":True,"connected_ip":ip,"pin_digest":_digest(self.pins)}
