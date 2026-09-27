
from __future__ import annotations

def validate_event_time(result):
    if result.available_at is None:
        return {"passed":False,"violations":["missing_available_at"]}
    if len(result.available_at)!=len(result.timestamps):
        return {"passed":False,"violations":["length_mismatch"]}
    violations=[]
    for i,(event_ts,avail_ts,val) in enumerate(zip(result.timestamps,result.available_at,result.values)):
        if val is not None and avail_ts < event_ts:
            violations.append({"index":i,"event_ts":event_ts,"available_at":avail_ts})
    return {"passed":len(violations)==0,"violations":violations}
