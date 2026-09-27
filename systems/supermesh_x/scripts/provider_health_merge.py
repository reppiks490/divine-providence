"""Order-safe provider-health state merge and quota-aware scoring."""
import copy, hashlib, json

_CIRCUIT_RISK={'closed':0,'half_open':1,'open':2}

def _receipt(row):
    body={k:v for k,v in row.items() if k not in {'receipt_hash','token','secret','authorization','api_key','password','cookie'}}
    return hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def merge_health_snapshots(rows):
    """Merge distributed snapshots by monotonic sequence, never wall-clock alone."""
    out={}
    for raw in rows:
        row=copy.deepcopy(raw); p=str(row['provider']); seq=int(row.get('sequence',0))
        cur=out.get(p)
        if cur is None or seq>int(cur.get('sequence',0)):
            out[p]=row; continue
        if seq<int(cur.get('sequence',0)):
            continue
        # Same logical generation: converge conservatively.
        if float(row.get('health',1)) < float(cur.get('health',1)):
            cur['health']=float(row.get('health',1))
        if _CIRCUIT_RISK.get(row.get('circuit','open'),2) > _CIRCUIT_RISK.get(cur.get('circuit','open'),2):
            cur['circuit']=row.get('circuit','open')
        cur['observed_at_ms']=max(int(cur.get('observed_at_ms',0)),int(row.get('observed_at_ms',0)))
    for row in out.values(): row['receipt_hash']=_receipt(row)
    return out

def apply_quota_headroom(row, remaining=None, limit=None):
    """Reduce routing health as quota exhausts; never changes authority."""
    out=copy.deepcopy(row)
    if remaining is None or limit is None or float(limit)<=0:
        out['quota_headroom']=None; out['receipt_hash']=_receipt(out); return out
    h=max(0.0,min(1.0,float(remaining)/float(limit)))
    out['quota_headroom']=round(h,6)
    # No penalty above 25%; smoothly penalize below it, max 35%.
    penalty=max(0.0,(0.25-h)/0.25)*0.35
    out['health']=round(max(0.0,float(out.get('health',1.0))-penalty),6)
    out['receipt_hash']=_receipt(out)
    return out
