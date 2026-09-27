"""ASCENSION Collision Detector v0.3.
Read-only CANDIDATE: semantic interface-contract conflicts + expanded path evidence.
"""
from __future__ import annotations
from itertools import combinations
import copy, json

DEFAULT_POLICY={"missing_manifest":"high","dependency_cycle":"high"}
SEV={"info","low","medium","high","critical"}

def _severity(policy,key):
    v=policy.get(key,DEFAULT_POLICY[key])
    if v not in SEV: raise ValueError(f"invalid severity for {key}: {v}")
    return v

def _all_simple_paths(graph, origin, max_depth=32):
    paths={}; cycles=[]
    def dfs(node,path):
        if len(path)>max_depth: return
        for nxt in sorted(graph.get(node,[])):
            if nxt in path:
                i=path.index(nxt); cycles.append(path[i:]+[nxt]); continue
            np=path+[nxt]; paths.setdefault(nxt,[]).append(np); dfs(nxt,np)
    dfs(origin,[origin]); return paths,cycles

def _iface_map(m):
    out={}
    for x in m.get("interfaces",[]):
        if not isinstance(x,dict) or "name" not in x or "version" not in x: continue
        out[(x["name"],str(x["version"]))]=x
    return out

def _semantic_contract_findings(a_name,a,b_name,b):
    out=[]; A=_iface_map(a); B=_iface_map(b)
    for key in sorted(set(A)&set(B)):
        ia,ib=A[key],B[key]
        # Same interface identity/version must not silently disagree on contract surface.
        for field in ("required_inputs","emitted_outputs","assumptions","invariants"):
            va=set(map(str,ia.get(field,[]))); vb=set(map(str,ib.get(field,[])))
            if va != vb:
                out.append({"code":"SEMANTIC_INTERFACE_CONTRACT_CONFLICT","systems":[a_name,b_name],
                    "interface":key[0],"version":key[1],"field":field,
                    "left_only":sorted(va-vb),"right_only":sorted(vb-va),"severity":"high"})
    return out

def _direct_findings(a_name,a,b_name,b):
    f=[]
    for r in sorted(set(a.get("mutation_rights",[]))&set(b.get("mutation_rights",[]))):
        f.append({"code":"MUTATION_RIGHT_COLLISION","systems":[a_name,b_name],"resource":r,"severity":"critical"})
    for r in sorted(set(a.get("owned_domains",[]))&set(b.get("owned_domains",[]))):
        f.append({"code":"OWNERSHIP_COLLISION","systems":[a_name,b_name],"resource":r,"severity":"high"})
    ia={x["name"]:x["version"] for x in a.get("interfaces",[]) if isinstance(x,dict) and "name" in x and "version" in x}
    ib={x["name"]:x["version"] for x in b.get("interfaces",[]) if isinstance(x,dict) and "name" in x and "version" in x}
    for n in sorted(set(ia)&set(ib)):
        if ia[n]!=ib[n]: f.append({"code":"INTERFACE_VERSION_CONFLICT","systems":[a_name,b_name],"resource":n,"versions":[ia[n],ib[n]],"severity":"high"})
    req=set(a.get("requires",[]))|set(b.get("requires",[])); forb=set(a.get("forbids",[]))|set(b.get("forbids",[]))
    for r in sorted(req&forb): f.append({"code":"INVARIANT_CONTRADICTION","systems":[a_name,b_name],"resource":r,"severity":"critical"})
    shared=set(a.get("shared_state",[]))&set(b.get("shared_state",[])); coord=set(a.get("coordination_contracts",[]))&set(b.get("coordination_contracts",[]))
    for r in sorted(shared-coord): f.append({"code":"UNCOORDINATED_SHARED_STATE","systems":[a_name,b_name],"resource":r,"severity":"high"})
    f.extend(_semantic_contract_findings(a_name,a,b_name,b)); return f

def analyze_ecosystem(manifests,dependency_graph,policy=None):
    manifests=copy.deepcopy(manifests); graph=copy.deepcopy(dependency_graph); policy={**DEFAULT_POLICY,**copy.deepcopy(policy or {})}
    findings=[]
    for a,b in combinations(sorted(manifests),2): findings.extend(_direct_findings(a,manifests[a],b,manifests[b]))
    seen_cycles=set()
    for origin in sorted(manifests):
        paths,cycles=_all_simple_paths(graph,origin)
        for cyc in cycles:
            core=cyc[:-1]; rots=[tuple(core[i:]+core[:i]) for i in range(len(core))]; canon=min(rots) if rots else tuple()
            if canon not in seen_cycles:
                seen_cycles.add(canon); findings.append({"code":"DEPENDENCY_CYCLE","path":list(canon)+([canon[0]] if canon else []),"severity":_severity(policy,"dependency_cycle")})
        om=manifests[origin]
        for dep,allpaths in sorted(paths.items()):
            if dep not in manifests:
                for path in allpaths: findings.append({"code":"MISSING_DEPENDENCY_MANIFEST","origin":origin,"dependency":dep,"path":path,"severity":_severity(policy,"missing_manifest")})
                continue
            dm=manifests[dep]
            for path in allpaths:
                if len(path)>2:
                    for r in sorted(set(om.get("mutation_rights",[]))&set(dm.get("mutation_rights",[]))):
                        findings.append({"code":"TRANSITIVE_MUTATION_COLLISION","origin":origin,"dependency":dep,"path":path,"resource":r,"severity":"critical"})
                    for r in sorted(set(om.get("requires",[]))&set(dm.get("forbids",[]))):
                        findings.append({"code":"TRANSITIVE_INVARIANT_CONTRADICTION","origin":origin,"dependency":dep,"path":path,"resource":r,"severity":"critical"})
    uniq={json.dumps(x,sort_keys=True,separators=(",",":")):x for x in findings}; findings=[uniq[k] for k in sorted(uniq)]
    critical=[x for x in findings if x["severity"]=="critical"]; boundary={"MUTATION_RIGHT_COLLISION","OWNERSHIP_COLLISION","TRANSITIVE_MUTATION_COLLISION"}
    return {"safe":not critical,"collision_free":not findings,"boundary_gate":not any(x["code"] in boundary for x in findings),
            "non_interference_gate":not critical,"findings":findings}
