import copy, hashlib, random, unittest
from datetime import datetime, timezone, timedelta
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import evaluator_fabric_v0_7 as e


def H(x): return hashlib.sha256(x).digest()
def leaf(x): return H(b'\x00'+x)
def node(a,b): return H(b'\x01'+a+b)
def largest_pow2_lt(n): return 1 << ((n-1).bit_length()-1)
def mth(items):
    items=list(items)
    if not items: return H(b'')
    if len(items)==1: return leaf(items[0])
    k=largest_pow2_lt(len(items))
    return node(mth(items[:k]),mth(items[k:]))
def subproof(m, items, complete=True):
    n=len(items)
    if m==n:
        return [] if complete else [mth(items)]
    k=largest_pow2_lt(n)
    if m<=k: return subproof(m,items[:k],complete)+[mth(items[k:])]
    return subproof(m-k,items[k:],False)+[mth(items[:k])]
def proof(m,items): return subproof(m,list(items),True)
def iso(dt): return dt.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
def pubhex(sk): return sk.public_key().public_bytes_raw().hex()
def obs(sk,wid,log_id,size,root,when):
    p={'algorithm':'Ed25519','witness_id':wid,'log_id':log_id,'tree_size':size,'root_hash':root,'observed_at':when}
    return {'payload':p,'signature_hex':sk.sign(e.canonical_json(p)).hex()}

class V07(unittest.TestCase):
    def setUp(self):
        self.items=[f'd{i}'.encode() for i in range(7)]
        self.now=datetime(2026,9,25,23,30,tzinfo=timezone.utc)
    def check(self,m,n):
        p=proof(m,self.items[:n]); return e.verify_compact_consistency(m,n,mth(self.items[:m]).hex(),mth(self.items[:n]).hex(),p)
    def test_rfc_example_3_to_7(self):
        self.assertEqual(len(proof(3,self.items)),4); self.assertTrue(self.check(3,7)['valid'])
    def test_rfc_example_4_to_7(self):
        self.assertEqual(len(proof(4,self.items)),1); self.assertTrue(self.check(4,7)['valid'])
    def test_rfc_example_6_to_7(self):
        self.assertEqual(len(proof(6,self.items)),3); self.assertTrue(self.check(6,7)['valid'])
    def test_mutated_consistency_node_rejected(self):
        p=proof(3,self.items); p[1]=bytes([p[1][0]^1])+p[1][1:]
        self.assertFalse(e.verify_compact_consistency(3,7,mth(self.items[:3]).hex(),mth(self.items).hex(),p)['valid'])
    def test_wrong_roots_rejected(self):
        p=proof(4,self.items)
        self.assertFalse(e.verify_compact_consistency(4,7,'00'*32,mth(self.items).hex(),p)['valid'])
        self.assertFalse(e.verify_compact_consistency(4,7,mth(self.items[:4]).hex(),'11'*32,p)['valid'])
    def test_bad_sizes_rejected(self):
        self.assertFalse(e.verify_compact_consistency(0,7,'00'*32,'00'*32,[])['valid'])
        self.assertFalse(e.verify_compact_consistency(8,7,'00'*32,'00'*32,[])['valid'])
    def test_equal_size_extension(self):
        r=mth(self.items).hex()
        self.assertTrue(e.verify_compact_consistency(7,7,r,r,[])['valid'])
        self.assertFalse(e.verify_compact_consistency(7,7,r,'00'*32,[])['valid'])
        self.assertFalse(e.verify_compact_consistency(7,7,r,r,[b'x'*32])['valid'])
    def test_valid_signed_witness_threshold(self):
        a,b=Ed25519PrivateKey.generate(),Ed25519PrivateKey.generate(); root=mth(self.items).hex(); when=iso(self.now-timedelta(seconds=20))
        rr=e.verify_signed_witness_observations([obs(a,'w1','logA',7,root,when),obs(b,'w2','logA',7,root,when)],{'w1':pubhex(a),'w2':pubhex(b)},2,'logA',7,root,iso(self.now),300)
        self.assertTrue(rr['valid']); self.assertEqual(rr['valid_witnesses'],['w1','w2'])
    def test_duplicate_witness_not_double_counted(self):
        a=Ed25519PrivateKey.generate(); root=mth(self.items).hex(); when=iso(self.now)
        o=obs(a,'w1','logA',7,root,when)
        rr=e.verify_signed_witness_observations([o,copy.deepcopy(o)],{'w1':pubhex(a)},2,'logA',7,root,iso(self.now),300)
        self.assertIn('witness_threshold_not_met',rr['reasons'])
    def test_bad_signature_and_binding_rejected(self):
        a=Ed25519PrivateKey.generate(); root=mth(self.items).hex(); when=iso(self.now); o=obs(a,'w1','logA',7,root,when)
        o['signature_hex']='00'*64
        self.assertIn('witness_signature_invalid',e.verify_signed_witness_observations([o],{'w1':pubhex(a)},1,'logA',7,root,iso(self.now),300)['reasons'])
        o=obs(a,'w1','other',7,root,when)
        self.assertIn('witness_log_mismatch',e.verify_signed_witness_observations([o],{'w1':pubhex(a)},1,'logA',7,root,iso(self.now),300)['reasons'])
    def test_stale_future_and_revoked_rejected(self):
        a=Ed25519PrivateKey.generate(); root=mth(self.items).hex()
        stale=obs(a,'w1','logA',7,root,iso(self.now-timedelta(seconds=1000)))
        self.assertIn('witness_observation_stale',e.verify_signed_witness_observations([stale],{'w1':pubhex(a)},1,'logA',7,root,iso(self.now),300)['reasons'])
        fut=obs(a,'w1','logA',7,root,iso(self.now+timedelta(seconds=1000)))
        self.assertIn('witness_observation_from_future',e.verify_signed_witness_observations([fut],{'w1':pubhex(a)},1,'logA',7,root,iso(self.now),300)['reasons'])
        cur=obs(a,'w1','logA',7,root,iso(self.now))
        self.assertIn('witness_revoked',e.verify_signed_witness_observations([cur],{'w1':{'public_key_hex':pubhex(a),'revoked':True}},1,'logA',7,root,iso(self.now),300)['reasons'])
    def test_combined_transition_gate(self):
        a,b=Ed25519PrivateKey.generate(),Ed25519PrivateKey.generate(); old=self.items[:4]; new=self.items; root=mth(new).hex(); when=iso(self.now)
        os=[obs(a,'w1','logA',7,root,when),obs(b,'w2','logA',7,root,when)]
        rr=e.verify_transparency_transition(4,7,mth(old).hex(),root,proof(4,new),os,{'w1':pubhex(a),'w2':pubhex(b)},2,'logA',iso(self.now),300)
        self.assertTrue(rr['valid'])
    def test_inputs_not_mutated(self):
        a,b=Ed25519PrivateKey.generate(),Ed25519PrivateKey.generate(); root=mth(self.items).hex(); when=iso(self.now)
        observations=[obs(a,'w1','logA',7,root,when),obs(b,'w2','logA',7,root,when)]; keys={'w1':pubhex(a),'w2':pubhex(b)}; before=copy.deepcopy(observations); kbefore=copy.deepcopy(keys)
        e.verify_signed_witness_observations(observations,keys,2,'logA',7,root,iso(self.now),300)
        self.assertEqual(observations,before); self.assertEqual(keys,kbefore)
    def test_malformed_inputs_fail_closed(self):
        self.assertFalse(e.verify_compact_consistency('x',7,'00','11',None)['valid'])
        rr=e.verify_signed_witness_observations([{'payload':{'witness_id':'w1'}}],{'w1':{'bad':'key'}},1,'logA',7,'00'*32,iso(self.now),300)
        self.assertFalse(rr['valid'])
        rr=e.verify_signed_witness_observations(None,None,1,'logA',7,'00'*32,iso(self.now),300)
        self.assertFalse(rr['valid'])

    def test_500_compact_proof_mutations(self):
        rng=random.Random(707); base=proof(3,self.items); old=mth(self.items[:3]).hex(); new=mth(self.items).hex()
        for _ in range(500):
            p=copy.deepcopy(base); i=rng.randrange(len(p)); b=bytearray(p[i]); b[rng.randrange(32)]^=1; p[i]=bytes(b)
            self.assertFalse(e.verify_compact_consistency(3,7,old,new,p)['valid'])
    def test_400_witness_payload_signature_mutations(self):
        rng=random.Random(704); sk=Ed25519PrivateKey.generate(); root=mth(self.items).hex(); base=obs(sk,'w1','logA',7,root,iso(self.now))
        for i in range(400):
            o=copy.deepcopy(base)
            if i%2:
                sig=bytearray.fromhex(o['signature_hex']); sig[rng.randrange(len(sig))]^=1; o['signature_hex']=sig.hex()
            else:
                o['payload']['tree_size']=8
            self.assertFalse(e.verify_signed_witness_observations([o],{'w1':pubhex(sk)},1,'logA',7,root,iso(self.now),300)['valid'])

if __name__=='__main__': unittest.main()
