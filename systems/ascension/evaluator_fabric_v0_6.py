from __future__ import annotations
import hashlib
from collections import defaultdict

def _h(x:bytes)->bytes:return hashlib.sha256(x).digest()
def _leaf(x:bytes)->bytes:return _h(b'\x00'+x)
def _node(a:bytes,b:bytes)->bytes:return _h(b'\x01'+a+b)
def merkle_root(items):
    hs=[_leaf(bytes(x)) for x in items]
    if not hs:return _h(b'')
    while len(hs)>1:
        hs=[_node(hs[i],hs[i+1]) if i+1<len(hs) else hs[i] for i in range(0,len(hs),2)]
    return hs[0]

def verify_inclusion(item,leaf_index,tree_size,inclusion_path,root_hash_hex):
    reasons=[]
    try:
        idx=int(leaf_index); size=int(tree_size)
        if idx<0 or idx>=size: reasons.append('leaf_index_out_of_range')
        r=_leaf(bytes(item))
        for side,p in inclusion_path:
            p=bytes(p)
            if side=='L':r=_node(p,r)
            elif side=='R':r=_node(r,p)
            else: reasons.append('inclusion_path_invalid'); break
        if not reasons and r.hex()!=str(root_hash_hex):reasons.append('inclusion_root_mismatch')
    except (TypeError,ValueError,OverflowError):reasons.append('inclusion_proof_invalid')
    return {'valid':not reasons,'reasons':sorted(set(reasons))}

def verify_append_only(old_entries,new_entries,old_root_hex,new_root_hex):
    reasons=[]
    try:
        old=[bytes(x) for x in old_entries]; new=[bytes(x) for x in new_entries]
        if len(new)<len(old): reasons.append('tree_size_rollback')
        if new[:len(old)]!=old: reasons.append('append_only_prefix_mismatch')
        if merkle_root(old).hex()!=str(old_root_hex): reasons.append('old_root_mismatch')
        if merkle_root(new).hex()!=str(new_root_hex): reasons.append('new_root_mismatch')
    except (TypeError,ValueError):reasons.append('consistency_input_invalid')
    return {'valid':not reasons,'reasons':sorted(set(reasons))}

def detect_split_view(views,minimum_witnesses):
    reasons=[]; by_size=defaultdict(lambda:defaultdict(set)); unique=set()
    try:
        minimum=int(minimum_witnesses)
        for v in views:
            w=str(v['witness']); size=int(v['tree_size']); root=str(v['root_hash']); unique.add(w); by_size[size][root].add(w)
        if len(unique)<minimum:reasons.append('witness_threshold_not_met')
        for size,roots in by_size.items():
            if len(roots)>1:reasons.append('split_view_equivocation')
    except (KeyError,TypeError,ValueError):reasons.append('witness_view_invalid')
    return {'valid':not reasons,'reasons':sorted(set(reasons)),'unique_witnesses':sorted(unique)}
