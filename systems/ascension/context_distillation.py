"""ASCENSION Context Distillation Engine v0.1 — read-only SHADOW reference."""
import json, hashlib
REQUIRED=["provenance","authority_boundaries","contradictions","decisions","dependencies","confidence","revalidation"]
def distill(records):
    packet={k:[] for k in REQUIRED}; packet["schema_version"]="0.1"; packet["source_ids"]=[]; packet["omissions"]=[]
    for r in records:
        sid=r["source_id"]; packet["source_ids"].append(sid)
        packet["provenance"].append({"source_id":sid,"digest":hashlib.sha256(json.dumps(r,sort_keys=True,separators=(",",":")).encode()).hexdigest()})
        for k in REQUIRED[1:]:
            vals=r.get(k,[]); vals=vals if isinstance(vals,list) else [vals]
            for v in vals: packet[k].append({"source_id":sid,"value":v})
    for k in REQUIRED[1:]:
        seen=set(); out=[]
        for item in packet[k]:
            key=json.dumps(item,sort_keys=True)
            if key not in seen: seen.add(key); out.append(item)
        packet[k]=out
    return packet
def audit_loss(records,packet):
    expected=distill(records); losses={}
    for k in REQUIRED:
        if k=="provenance":
            exp={(x["source_id"],x["digest"]) for x in expected[k]}; got={(x["source_id"],x["digest"]) for x in packet.get(k,[])}
        else:
            exp={json.dumps(x,sort_keys=True) for x in expected[k]}; got={json.dumps(x,sort_keys=True) for x in packet.get(k,[])}
        miss=exp-got
        if miss: losses[k]=len(miss)
    return {"loss_free":not losses,"losses":losses}
