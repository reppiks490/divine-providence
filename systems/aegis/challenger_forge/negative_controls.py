from __future__ import annotations

def deterministic_random_direction(index: int, seed: int = 12345) -> int:
    x=(index*1103515245 + seed) & 0x7fffffff
    return 1 if (x & 1)==0 else -1

def randomized_signal_control(signal_values, seed=12345):
    out=[]
    for i,v in enumerate(signal_values):
        if not v or not v.get("direction"):
            out.append(None)
        else:
            out.append({"direction":deterministic_random_direction(i,seed),"negative_control":True,"event_time_index":i})
    return out
