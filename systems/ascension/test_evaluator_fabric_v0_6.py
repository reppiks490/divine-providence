import unittest, hashlib, copy, random
import evaluator_fabric_v0_6 as e

def H(x): return hashlib.sha256(x).digest()
def leaf(x): return H(b'\x00'+x)
def node(a,b): return H(b'\x01'+a+b)

def tree_root(items):
    hs=[leaf(x) for x in items]
    if not hs: return H(b'')
    while len(hs)>1:
        hs=[node(hs[i],hs[i+1]) if i+1<len(hs) else hs[i] for i in range(0,len(hs),2)]
    return hs[0]

def inclusion_path(items,index):
    hs=[leaf(x) for x in items]; idx=index; path=[]
    while len(hs)>1:
        if idx%2: path.append(('L',hs[idx-1]))
        elif idx+1<len(hs): path.append(('R',hs[idx+1]))
        hs=[node(hs[i],hs[i+1]) if i+1<len(hs) else hs[i] for i in range(0,len(hs),2)]; idx//=2
    return path

class V06(unittest.TestCase):
 def setUp(self): self.items=[f'entry-{i}'.encode() for i in range(7)]
 def test_valid_inclusion(self):
  r=tree_root(self.items); self.assertTrue(e.verify_inclusion(self.items[4],4,len(self.items),inclusion_path(self.items,4),r.hex())['valid'])
 def test_tampered_leaf_rejected(self):
  r=tree_root(self.items); self.assertFalse(e.verify_inclusion(b'evil',4,len(self.items),inclusion_path(self.items,4),r.hex())['valid'])
 def test_bad_index_rejected(self): self.assertIn('leaf_index_out_of_range',e.verify_inclusion(b'x',8,7,[],tree_root(self.items).hex())['reasons'])
 def test_append_only_consistency(self):
  old=self.items[:4]; new=self.items[:7]; self.assertTrue(e.verify_append_only(old,new,tree_root(old).hex(),tree_root(new).hex())['valid'])
 def test_rewrite_rejected(self):
  old=self.items[:4]; new=list(self.items); new[2]=b'rewritten'; self.assertIn('append_only_prefix_mismatch',e.verify_append_only(old,new,tree_root(old).hex(),tree_root(new).hex())['reasons'])
 def test_root_mismatch_rejected(self):
  old=self.items[:4]; new=self.items; self.assertIn('new_root_mismatch',e.verify_append_only(old,new,tree_root(old).hex(),'00'*32)['reasons'])
 def test_split_view_detected(self):
  views=[{'witness':'w1','tree_size':7,'root_hash':'aa'},{'witness':'w2','tree_size':7,'root_hash':'bb'},{'witness':'w3','tree_size':7,'root_hash':'aa'}]
  self.assertIn('split_view_equivocation',e.detect_split_view(views,2)['reasons'])
 def test_consensus_view(self):
  views=[{'witness':'w1','tree_size':7,'root_hash':'aa'},{'witness':'w2','tree_size':7,'root_hash':'aa'}]
  self.assertTrue(e.detect_split_view(views,2)['valid'])
 def test_duplicate_witness_does_not_meet_threshold(self):
  views=[{'witness':'w1','tree_size':7,'root_hash':'aa'},{'witness':'w1','tree_size':7,'root_hash':'aa'}]
  self.assertIn('witness_threshold_not_met',e.detect_split_view(views,2)['reasons'])
 def test_500_inclusion_mutations(self):
  rng=random.Random(606); r=tree_root(self.items).hex(); path=inclusion_path(self.items,3)
  for _ in range(500):
   evil=bytearray(self.items[3]); evil[rng.randrange(len(evil))]^=1
   self.assertFalse(e.verify_inclusion(bytes(evil),3,7,path,r)['valid'])
 def test_300_history_mutations(self):
  rng=random.Random(603); old=self.items[:4]
  for _ in range(300):
   new=list(self.items); j=rng.randrange(4); new[j]=new[j]+b'x'
   self.assertFalse(e.verify_append_only(old,new,tree_root(old).hex(),tree_root(new).hex())['valid'])
if __name__=='__main__': unittest.main()
