import copy, hashlib, unittest
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
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
    if not (0 <= m < n): raise ValueError('index')
    if n==1: return []
    k=split(n)
    if m < k: return path(m,items[:k])+[mth(items[k:])]
    return path(m-k,items[k:])+[mth(items[:k])]
def subproof(m,items,complete=True):
    items=list(items); n=len(items)
    if m==n: return [] if complete else [mth(items)]
    k=split(n)
    if m<=k: return subproof(m,items[:k],complete)+[mth(items[k:])]
    return subproof(m-k,items[k:],False)+[mth(items[:k])]
def consistency(m,items): return subproof(m,list(items),True)
def pubhex(sk): return sk.public_key().public_bytes_raw().hex()
def obs(sk,wid,log_id,size,root,when):
    p={'algorithm':'Ed25519','witness_id':wid,'log_id':log_id,'tree_size':size,'root_hash':root,'observed_at':when}
    return {'payload':p,'signature_hex':sk.sign(e.canonical_json(p)).hex()}


class V08(unittest.TestCase):
    def setUp(self):
        self.items=[f'd{i}'.encode() for i in range(7)]
        self.root=mth(self.items)
        self.now='2026-09-25T23:45:00Z'

    def check(self,i):
        return e.verify_strict_inclusion(leaf(self.items[i]),i,len(self.items),self.root,path(i,self.items))

    def test_single_leaf_empty_proof(self):
        d=b'only'; lh=leaf(d)
        r=e.verify_strict_inclusion(lh,0,1,lh,[])
        self.assertTrue(r['valid']); self.assertEqual(r['expected_proof_nodes'],0)

    def test_rfc_7_leaf_examples(self):
        for i,expected in [(0,3),(3,3),(4,3),(6,2)]:
            r=self.check(i)
            self.assertTrue(r['valid'],(i,r)); self.assertEqual(r['proof_nodes'],expected); self.assertEqual(r['expected_proof_nodes'],expected)

    def test_merkle_leaf_domain_separation(self):
        data=b'd0'
        self.assertEqual(e.merkle_leaf_hash(data),leaf(data))
        self.assertNotEqual(e.merkle_leaf_hash(data),H(data))

    def test_out_of_range_and_zero_tree_rejected(self):
        self.assertIn('leaf_index_out_of_range',e.verify_strict_inclusion(b'0'*32,7,7,b'1'*32,[])['reasons'])
        self.assertIn('tree_size_invalid',e.verify_strict_inclusion(b'0'*32,0,0,b'1'*32,[])['reasons'])

    def test_uint64_and_type_bounds_rejected(self):
        for idx,size in [(True,1),(0,True),('0',1),(0,'1'),(-1,1),(0,2**64)]:
            self.assertFalse(e.verify_strict_inclusion(b'0'*32,idx,size,b'1'*32,[])['valid'])

    def test_bad_hash_and_path_types_rejected(self):
        self.assertFalse(e.verify_strict_inclusion(b'x',0,1,b'1'*32,[])['valid'])
        self.assertFalse(e.verify_strict_inclusion(b'0'*32,0,1,b'x',[])['valid'])
        self.assertFalse(e.verify_strict_inclusion(b'0'*32,0,1,b'1'*32,b'not-a-path')['valid'])
        self.assertFalse(e.verify_strict_inclusion(b'0'*32,0,2,b'1'*32,[b'x'])['valid'])

    def test_padded_proof_rejected_by_geometry(self):
        p=path(0,self.items)+[b'Z'*32]
        r=e.verify_strict_inclusion(leaf(self.items[0]),0,7,self.root,p)
        self.assertIn('inclusion_path_length_mismatch',r['reasons'])

    def test_truncated_proof_rejected_by_geometry(self):
        p=path(0,self.items)[:-1]
        r=e.verify_strict_inclusion(leaf(self.items[0]),0,7,self.root,p)
        self.assertIn('inclusion_path_length_mismatch',r['reasons'])

    def test_mutated_node_rejected(self):
        p=path(4,self.items); b=bytearray(p[0]); b[3]^=1; p[0]=bytes(b)
        r=e.verify_strict_inclusion(leaf(self.items[4]),4,7,self.root,p)
        self.assertIn('inclusion_root_mismatch',r['reasons'])

    def test_wrong_leaf_or_root_rejected(self):
        p=path(3,self.items)
        self.assertFalse(e.verify_strict_inclusion(leaf(b'wrong'),3,7,self.root,p)['valid'])
        self.assertFalse(e.verify_strict_inclusion(leaf(self.items[3]),3,7,b'R'*32,p)['valid'])

    def test_expected_length_matches_generator(self):
        for i in range(7): self.assertEqual(e.expected_inclusion_path_length(i,7),len(path(i,self.items)))

    def test_false_index_relabel_rejected(self):
        p=path(6,self.items)
        for claimed in range(7):
            if claimed == 6:
                continue
            self.assertFalse(e.verify_strict_inclusion(leaf(self.items[6]),claimed,7,self.root,p)['valid'])

    def test_uint64_max_geometry_is_bounded(self):
        n=e.MAX_UINT64
        self.assertLessEqual(e.expected_inclusion_path_length(0,n),64)
        self.assertLessEqual(e.expected_inclusion_path_length(n-1,n),64)

    def test_inputs_not_mutated(self):
        p=path(2,self.items); before=copy.deepcopy(p)
        e.verify_strict_inclusion(leaf(self.items[2]),2,7,self.root,p)
        self.assertEqual(p,before)

    def test_combined_transparency_evidence_valid(self):
        a,b=Ed25519PrivateKey.generate(),Ed25519PrivateKey.generate(); when=self.now
        observations=[obs(a,'w1','logA',7,self.root.hex(),when),obs(b,'w2','logA',7,self.root.hex(),when)]
        r=e.verify_transparency_evidence(
            leaf(self.items[4]),4,7,self.root,path(4,self.items),
            4,mth(self.items[:4]),consistency(4,self.items),
            observations,{'w1':pubhex(a),'w2':pubhex(b)},2,'logA',self.now,300)
        self.assertTrue(r['valid'],r)

    def test_combined_gate_rejects_bad_inclusion(self):
        a=Ed25519PrivateKey.generate(); observations=[obs(a,'w1','logA',7,self.root.hex(),self.now)]
        bad=path(4,self.items); bad=bad[:-1]
        r=e.verify_transparency_evidence(
            leaf(self.items[4]),4,7,self.root,bad,
            4,mth(self.items[:4]),consistency(4,self.items),
            observations,{'w1':pubhex(a)},1,'logA',self.now,300)
        self.assertFalse(r['valid']); self.assertTrue(any(x.startswith('inclusion:') for x in r['reasons']))

    def test_combined_gate_rejects_bad_transition_or_witness(self):
        a=Ed25519PrivateKey.generate(); observations=[obs(a,'w1','logA',7,self.root.hex(),self.now)]
        cp=consistency(4,self.items); b=bytearray(cp[0]); b[0]^=1; cp[0]=bytes(b)
        r=e.verify_transparency_evidence(
            leaf(self.items[4]),4,7,self.root,path(4,self.items),
            4,mth(self.items[:4]),cp,
            observations,{'w1':pubhex(a)},1,'logA',self.now,300)
        self.assertFalse(r['valid']); self.assertTrue(any(x.startswith('transition:') for x in r['reasons']))

    def test_hash_hex_inputs_supported_but_strict(self):
        p=[x.hex() for x in path(6,self.items)]
        r=e.verify_strict_inclusion(leaf(self.items[6]).hex(),6,7,self.root.hex(),p)
        self.assertTrue(r['valid'])
        self.assertFalse(e.verify_strict_inclusion('gg',0,1,'00'*32,[])['valid'])

    def test_malformed_combined_inputs_fail_closed(self):
        r=e.verify_transparency_evidence(None,'x','y',None,None,None,None,None,None,None,None,None,None,None)
        self.assertFalse(r['valid']); self.assertTrue(r['reasons'])

if __name__=='__main__': unittest.main()
