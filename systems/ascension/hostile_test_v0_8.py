import hashlib, random
import evaluator_fabric_v0_8 as e

def H(x): return hashlib.sha256(x).digest()
def leaf(x): return H(b'\x00'+x)
def node(a,b): return H(b'\x01'+a+b)
def split(n): return 1 << ((n-1).bit_length()-1)
def mth(xs):
    xs=list(xs)
    if len(xs)==1:return leaf(xs[0])
    k=split(len(xs)); return node(mth(xs[:k]),mth(xs[k:]))
def path(i,xs):
    xs=list(xs)
    if len(xs)==1:return []
    k=split(len(xs))
    if i<k:return path(i,xs[:k])+[mth(xs[k:])]
    return path(i-k,xs[k:])+[mth(xs[:k])]

rng=random.Random(8808)
order=0
for _ in range(500):
    while True:
        n=rng.randint(4,128); xs=[f'o:{n}:{j}'.encode() for j in range(n)]; i=rng.randrange(n); p=path(i,xs)
        if len(p)>=2: break
    q=list(p); a,b=rng.sample(range(len(q)),2); q[a],q[b]=q[b],q[a]
    assert not e.verify_strict_inclusion(leaf(xs[i]),i,n,mth(xs),q)['valid']
    order+=1

bad_node_len=0
for _ in range(500):
    n=rng.randint(2,64); xs=[f'l:{n}:{j}'.encode() for j in range(n)]; i=rng.randrange(n); p=path(i,xs)
    q=list(p); j=rng.randrange(len(q)); q[j]=b'x'*rng.choice([0,1,16,31,33,64])
    rr=e.verify_strict_inclusion(leaf(xs[i]),i,n,mth(xs),q)
    assert not rr['valid'] and 'inclusion_path_invalid' in rr['reasons']
    bad_node_len+=1

malformed=0
bad_values=[None, True, False, 1.5, {}, object(), b'', 'nothex']
for _ in range(500):
    which=rng.randrange(5)
    args=[b'0'*32,0,1,b'0'*32,[]]
    args[which]=rng.choice(bad_values)
    try:
        rr=e.verify_strict_inclusion(*args)
    except Exception as exc:
        raise AssertionError((which,type(args[which]),exc))
    assert isinstance(rr,dict) and not rr['valid']
    malformed+=1

print(f'ORDER_ATTACKS_REJECTED={order}')
print(f'BAD_NODE_LENGTHS_REJECTED={bad_node_len}')
print(f'MALFORMED_TOP_LEVEL_FAIL_CLOSED={malformed}')
