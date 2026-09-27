import copy, hashlib, random
import evaluator_fabric_v0_8 as e


def H(x): return hashlib.sha256(x).digest()
def leaf(x): return H(b'\x00'+x)
def node(a,b): return H(b'\x01'+a+b)
def split(n): return 1 << ((n-1).bit_length()-1)
def mth(items):
    items=list(items)
    if not items: return H(b'')
    if len(items)==1: return leaf(items[0])
    k=split(len(items)); return node(mth(items[:k]),mth(items[k:]))
def path(m,items):
    items=list(items); n=len(items)
    if n==1: return []
    k=split(n)
    if m<k: return path(m,items[:k])+[mth(items[k:])]
    return path(m-k,items[k:])+[mth(items[:k])]

valid=0; max_nodes=0
for n in range(1,129):
    items=[f'n={n}:i={i}'.encode() for i in range(n)]
    root=mth(items)
    for i in range(n):
        p=path(i,items)
        r=e.verify_strict_inclusion(leaf(items[i]),i,n,root,p)
        assert r['valid'], (n,i,r)
        assert r['expected_proof_nodes']==len(p), (n,i,len(p),r)
        valid+=1; max_nodes=max(max_nodes,len(p))

rng=random.Random(808)
mutated=0
for _ in range(1500):
    n=rng.randint(2,128); items=[f'm:{n}:{i}'.encode() for i in range(n)]; i=rng.randrange(n); root=mth(items); p=path(i,items)
    q=copy.deepcopy(p); j=rng.randrange(len(q)); b=bytearray(q[j]); b[rng.randrange(32)]^=1; q[j]=bytes(b)
    assert not e.verify_strict_inclusion(leaf(items[i]),i,n,root,q)['valid']
    mutated+=1

geometry=0
for _ in range(1000):
    n=rng.randint(2,128); items=[f'g:{n}:{i}'.encode() for i in range(n)]; i=rng.randrange(n); root=mth(items); p=path(i,items)
    if rng.randrange(2)==0 and p:
        q=p[:-1]
    else:
        q=p+[H(f'extra:{rng.random()}'.encode())]
    rr=e.verify_strict_inclusion(leaf(items[i]),i,n,root,q)
    assert not rr['valid'] and 'inclusion_path_length_mismatch' in rr['reasons']
    geometry+=1

binding=0
for _ in range(1000):
    n=rng.randint(1,128); items=[f'b:{n}:{i}'.encode() for i in range(n)]; i=rng.randrange(n); root=mth(items); p=path(i,items)
    mode=rng.randrange(3)
    if mode==0:
        bad=bytearray(root); bad[rng.randrange(32)]^=1
        rr=e.verify_strict_inclusion(leaf(items[i]),i,n,bytes(bad),p)
    elif mode==1:
        lh=bytearray(leaf(items[i])); lh[rng.randrange(32)]^=1
        rr=e.verify_strict_inclusion(bytes(lh),i,n,root,p)
    else:
        wrong=(i+1)%n if n>1 else 1
        rr=e.verify_strict_inclusion(leaf(items[i]),wrong,n,root,p)
    assert not rr['valid']
    binding+=1

print(f'VALID_INCLUSIONS={valid}')
print(f'MAX_PROOF_NODES={max_nodes}')
print(f'MUTATED_NODES_REJECTED={mutated}')
print(f'GEOMETRY_ATTACKS_REJECTED={geometry}')
print(f'BINDING_ATTACKS_REJECTED={binding}')

# Comparative index-binding probe: v0.6 side-labelled proofs do not bind the
# declared index. v0.8 must reject every false in-range relabel for the same
# actual leaf/proof in the RFC-shaped 7-leaf tree.
import evaluator_fabric_v0_6 as v6

def v6_root(items):
    hs=[leaf(x) for x in items]
    if not hs: return H(b'')
    while len(hs)>1:
        hs=[node(hs[i],hs[i+1]) if i+1<len(hs) else hs[i] for i in range(0,len(hs),2)]
    return hs[0]
def v6_path(items,index):
    hs=[leaf(x) for x in items]; idx=index; out=[]
    while len(hs)>1:
        if idx%2: out.append(('L',hs[idx-1]))
        elif idx+1<len(hs): out.append(('R',hs[idx+1]))
        hs=[node(hs[i],hs[i+1]) if i+1<len(hs) else hs[i] for i in range(0,len(hs),2)]; idx//=2
    return out
items=[f'relabel-{i}'.encode() for i in range(7)]; root=v6_root(items); old_accept=0; new_reject=0
for actual in range(7):
    p6=v6_path(items,actual); p8=path(actual,items)
    for claimed in range(7):
        if claimed==actual: continue
        if v6.verify_inclusion(items[actual],claimed,7,p6,root.hex())['valid']: old_accept+=1
        if not e.verify_strict_inclusion(leaf(items[actual]),claimed,7,root,p8)['valid']: new_reject+=1
assert old_accept==42
assert new_reject==42
print(f'V06_FALSE_INDEX_RELABELS_ACCEPTED={old_accept}')
print(f'V08_FALSE_INDEX_RELABELS_REJECTED={new_reject}')
