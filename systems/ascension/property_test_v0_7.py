import hashlib, math, random, copy
import evaluator_fabric_v0_7 as e

def H(x): return hashlib.sha256(x).digest()
def leaf(x): return H(b'\x00'+x)
def node(a,b): return H(b'\x01'+a+b)
def kpow(n): return 1 << ((n-1).bit_length()-1)
def mth(xs):
    xs=list(xs)
    if not xs: return H(b'')
    if len(xs)==1:return leaf(xs[0])
    k=kpow(len(xs)); return node(mth(xs[:k]),mth(xs[k:]))
def sub(m,xs,b=True):
    n=len(xs)
    if m==n:return [] if b else [mth(xs)]
    k=kpow(n)
    return (sub(m,xs[:k],b)+[mth(xs[k:])]) if m<=k else (sub(m-k,xs[k:],False)+[mth(xs[:k])])
def proof(m,xs):return sub(m,list(xs),True)

transitions=0; max_nodes=0
for n in range(2,65):
    xs=[f'leaf-{i}'.encode() for i in range(n)]
    for m in range(1,n):
        p=proof(m,xs); transitions+=1; max_nodes=max(max_nodes,len(p))
        assert len(p) <= math.ceil(math.log2(n))+1
        r=e.verify_compact_consistency(m,n,mth(xs[:m]).hex(),mth(xs).hex(),p)
        assert r['valid'], (m,n,r)

rng=random.Random(1707); mutations=0
for _ in range(1000):
    n=rng.randrange(3,65); m=rng.randrange(1,n); xs=[f'x{i}'.encode() for i in range(n)]; p=proof(m,xs)
    if not p: continue
    q=copy.deepcopy(p); i=rng.randrange(len(q)); b=bytearray(q[i]); b[rng.randrange(32)]^=1; q[i]=bytes(b); mutations+=1
    assert not e.verify_compact_consistency(m,n,mth(xs[:m]).hex(),mth(xs).hex(),q)['valid']
print({'valid_transitions':transitions,'max_proof_nodes':max_nodes,'mutated_proofs_rejected':mutations})
