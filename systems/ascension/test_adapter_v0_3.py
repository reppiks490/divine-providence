import copy, hashlib, unittest
from datetime import datetime, timezone, timedelta
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from evaluator_fabric_v0_4 import create_attestation, canonical_json
import evaluator_fabric_v0_7 as ef7
import manifest_trust_collision_adapter_v0_3 as a3

NOW=datetime(2026,9,25,23,45,tzinfo=timezone.utc)

def H(x): return hashlib.sha256(x).digest()
def leaf(x): return H(b'\x00'+x)
def node(a,b): return H(b'\x01'+a+b)
def kpow(n): return 1 << ((n-1).bit_length()-1)
def mth(xs):
    xs=list(xs)
    if not xs:return H(b'')
    if len(xs)==1:return leaf(xs[0])
    k=kpow(len(xs));return node(mth(xs[:k]),mth(xs[k:]))
def sub(m,xs,b=True):
    n=len(xs)
    if m==n:return [] if b else [mth(xs)]
    k=kpow(n)
    return (sub(m,xs[:k],b)+[mth(xs[k:])]) if m<=k else (sub(m-k,xs[k:],False)+[mth(xs[:k])])
def proof(m,xs):return sub(m,list(xs),True)
def ipath(xs,index):
    xs=list(xs)
    if len(xs)==1:return []
    k=kpow(len(xs))
    if index<k:return ipath(xs[:k],index)+[('R',mth(xs[k:]))]
    return ipath(xs[k:],index-k)+[('L',mth(xs[:k]))]
def iso(dt):return dt.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
def pubhex(sk):return sk.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw).hex()
def observation(sk,wid,log_id,size,root,when):
    p={'algorithm':'Ed25519','witness_id':wid,'log_id':log_id,'tree_size':size,'root_hash':root,'observed_at':when}
    return {'payload':p,'signature_hex':sk.sign(ef7.canonical_json(p)).hex()}

def fixture(sid='S1'):
    signer=Ed25519PrivateKey.generate(); pub=pubhex(signer)
    w1,w2=Ed25519PrivateKey.generate(),Ed25519PrivateKey.generate()
    m={'system_id':sid,'owned_domains':[sid+'.domain'],'mutation_rights':[],
       'interfaces':[{'name':'handoff','version':'1','required_inputs':['manifest'],'emitted_outputs':['packet'],'assumptions':['signed'],'invariants':['read-only']}],
       'requires':[],'forbids':[],'shared_state':[],'coordination_contracts':[]}
    prior={'detector':'Collision Detector','version':'0.2.1','collision_free':True,'findings':[],'boundary_gate':True,'non_interference_gate':True}
    art=(sid+' artifact').encode()
    old=[b'a',b'b',b'c',b'd']; item=canonical_json(m); new=old+[item]
    old_root=mth(old).hex(); new_root=mth(new).hex(); when=iso(NOW-timedelta(seconds=20))
    tp={'required':True,'hash_algorithm':'SHA-256','witness_algorithm':'Ed25519','log_id':'ascension-test-log',
        'trusted_checkpoint':{'tree_size':len(old),'root_hash':old_root},
        'witness_keys':{'w1':pubhex(w1),'w2':pubhex(w2)},'minimum_witnesses':2,
        'max_witness_age_seconds':300,'future_tolerance_seconds':60}
    policy={'policy_version':1,'minimum_policy_version':1,'allowed_algorithms':['Ed25519'],'max_age_seconds':3600,
            'signers':{'root':{'public_key_hex':pub,'allowed_subjects':[sid],'roles':['root']}},
            'thresholds':{sid:{'role':'root','minimum':1}},'transparency_policy':tp}
    att=create_attestation(signer_id='root',subject=sid,manifest=m,artifact_bytes=art,collision_report=prior,
                           issued_at=NOW-timedelta(minutes=1),private_key=signer,policy_version=1,evidence_class='manifest')
    evidence={'inclusion':{'leaf_index':len(new)-1,'tree_size':len(new),'path':ipath(new,len(new)-1),'root_hash':new_root},
              'transition':{'first_size':len(old),'second_size':len(new),'first_root_hash':old_root,'second_root_hash':new_root,
                            'consistency_path':proof(len(old),new),
                            'witness_observations':[observation(w1,'w1',tp['log_id'],len(new),new_root,when),observation(w2,'w2',tp['log_id'],len(new),new_root,when)]}}
    f=dict(manifest=m,artifact_bytes=art,prior_collision_report=prior,attestations=[att],trust_policy=policy,now=NOW,
           transparency_evidence=evidence)
    f['backend_contract']=a3.build_backend_contract(policy)
    return f

class AdapterV03(unittest.TestCase):
    def test_valid_full_chain_accepts(self):
        r=a3.normalize_trusted_manifest(**fixture());self.assertTrue(r['accepted'],r['reasons'])
        self.assertEqual(r['normalized_manifest']['provenance']['transparency_backend'],a3.TRANSPARENCY_BACKEND)
    def test_backend_contract_is_required(self):
        f=fixture();f['backend_contract']=None;r=a3.normalize_trusted_manifest(**f)
        self.assertFalse(r['accepted']);self.assertIn('backend_contract_required',r['reasons'])
    def test_transparency_backend_downgrade_rejected(self):
        f=fixture();f['backend_contract']['transparency']='evaluator-fabric-transparency-v0.6-full-history'
        r=a3.normalize_trusted_manifest(**f);self.assertIn('backend_contract_mismatch:transparency',r['reasons'])
    def test_collision_backend_substitution_rejected(self):
        f=fixture();f['backend_contract']['collision']='collision-detector-v0.2.1'
        r=a3.normalize_trusted_manifest(**f);self.assertIn('backend_contract_mismatch:collision',r['reasons'])
    def test_hash_algorithm_downgrade_rejected(self):
        f=fixture();f['trust_policy']['transparency_policy']['hash_algorithm']='SHA-1'
        r=a3.normalize_trusted_manifest(**f);self.assertIn('transparency_hash_algorithm_not_allowed',r['reasons'])
    def test_witness_algorithm_downgrade_rejected(self):
        f=fixture();f['trust_policy']['transparency_policy']['witness_algorithm']='RSA'
        r=a3.normalize_trusted_manifest(**f);self.assertIn('witness_algorithm_not_allowed',r['reasons'])
    def test_witness_policy_substitution_rejected_by_pinned_digest(self):
        f=fixture();f['trust_policy']['transparency_policy']['minimum_witnesses']=1
        r=a3.normalize_trusted_manifest(**f);self.assertIn('transparency_policy_digest_mismatch',r['reasons'])
    def test_trusted_checkpoint_evidence_substitution_rejected(self):
        f=fixture();f['transparency_evidence']['transition']['first_root_hash']='00'*32
        r=a3.normalize_trusted_manifest(**f);self.assertIn('trusted_checkpoint_root_mismatch',r['reasons'])
    def test_current_checkpoint_must_bind_inclusion_and_transition(self):
        f=fixture();f['transparency_evidence']['inclusion']['root_hash']='11'*32
        r=a3.normalize_trusted_manifest(**f);self.assertFalse(r['accepted'])
        self.assertIn('inclusion_transition_root_mismatch',r['reasons'])
    def test_duplicate_witness_does_not_satisfy_threshold(self):
        f=fixture();obs=f['transparency_evidence']['transition']['witness_observations'][0]
        f['transparency_evidence']['transition']['witness_observations']=[obs,copy.deepcopy(obs)]
        r=a3.normalize_trusted_manifest(**f);self.assertIn('transition:witness:witness_threshold_not_met',r['reasons'])
    def test_bad_signature_blocks_but_siblings_fail_open(self):
        f=fixture();f['attestations'][0]['signature_hex']='00'
        r=a3.analyze_trusted_ecosystem({'S1':f},{'S1':[]})
        self.assertFalse(r['analysis_performed']);self.assertTrue(r['safe_for_siblings'])
    def test_trust_result_schema_drift_fails_closed(self):
        self.assertIn('trust_result_schema_incompatible',a3.validate_trust_result({'trusted':True})['reasons'])
    def test_provenance_binds_all_upstream_evidence_digests(self):
        f=fixture();r=a3.normalize_trusted_manifest(**f);p=r['normalized_manifest']['provenance']
        self.assertEqual(p['attestations_sha256'],a3.hash_evidence(f['attestations']))
        self.assertEqual(p['prior_collision_report_sha256'],a3.hash_evidence(f['prior_collision_report']))
        self.assertEqual(p['transparency_evidence_sha256'],a3.hash_evidence(f['transparency_evidence']))
        self.assertEqual(p['trust_result_sha256'],a3.hash_evidence(r['trust_evidence']))

    def test_provenance_validates(self):
        f=fixture();r=a3.normalize_trusted_manifest(**f);v=a3.validate_normalized_manifest(r['normalized_manifest'],f['backend_contract'])
        self.assertTrue(v['valid'],v['reasons'])
    def test_provenance_loss_is_detected(self):
        f=fixture();r=a3.normalize_trusted_manifest(**f);n=copy.deepcopy(r['normalized_manifest']);del n['provenance']['transparency_policy_sha256']
        v=a3.validate_normalized_manifest(n,f['backend_contract']);self.assertFalse(v['valid']);self.assertIn('provenance_incomplete:transparency_policy_sha256',v['reasons'])
    def test_semantic_collision_reaches_v03_through_v07_gate(self):
        fa,fb=fixture('A'),fixture('B')
        # Build B from scratch after changing its semantic contract so every signature/proof binds the changed manifest.
        fb=fixture('B'); fb['manifest']['interfaces'][0]['invariants']=['may-mutate']
        # Reconstruct all manifest-bound evidence using the helper's private signing material is impossible after fixture creation; instead create a fresh changed fixture locally.
        # Use a same-version conflict in owned interface fields by changing A before its fixture is signed via a dedicated helper below.
        # This assertion is completed via make_fixture_with_invariant().
        fa=make_fixture_with_invariant('A','read-only');fb=make_fixture_with_invariant('B','may-mutate')
        r=a3.analyze_trusted_ecosystem({'A':fa,'B':fb},{'A':[],'B':[]})
        self.assertTrue(r['analysis_performed'],r.get('rejected'))
        self.assertIn('SEMANTIC_INTERFACE_CONTRACT_CONFLICT',[x['code'] for x in r['collision_report']['findings']])
    def test_identity_mismatch_blocks_fail_open(self):
        f=fixture('S1');r=a3.analyze_trusted_ecosystem({'WRONG':f},{'WRONG':[]})
        self.assertFalse(r['analysis_performed']);self.assertTrue(r['safe_for_siblings']);self.assertIn('manifest_map_identity_mismatch',r['rejected']['WRONG'])
    def test_malformed_top_level_inputs_fail_closed_not_crash(self):
        f=fixture();f['trust_policy']='not-a-policy';f['backend_contract']={}
        r=a3.normalize_trusted_manifest(**f)
        self.assertFalse(r['accepted']);self.assertTrue(r['safe_for_siblings']);self.assertIn('adapter_input_invalid',r['reasons'])

    def test_integer_artifact_type_rejected_not_coerced(self):
        f=fixture();f['artifact_bytes']=1
        r=a3.normalize_trusted_manifest(**f)
        self.assertFalse(r['accepted']);self.assertIn('adapter_input_invalid',r['reasons'])

    def test_attestation_mapping_type_rejected_not_iterated_as_sequence(self):
        f=fixture();f['attestations']={'unexpected':'mapping'}
        r=a3.normalize_trusted_manifest(**f)
        self.assertFalse(r['accepted']);self.assertIn('adapter_input_invalid',r['reasons'])

    def test_inputs_immutable(self):
        f=fixture();before=copy.deepcopy(f);a3.normalize_trusted_manifest(**f);self.assertEqual(f,before)
    def test_evidence_packet_deterministic(self):
        fa=fixture('A');r1=a3.analyze_trusted_ecosystem({'A':fa},{'A':[]});r2=a3.analyze_trusted_ecosystem({'A':copy.deepcopy(fa)},{'A':[]})
        self.assertEqual(r1['evidence_packet'],r2['evidence_packet'])

def make_fixture_with_invariant(sid,invariant):
    signer=Ed25519PrivateKey.generate(); pub=pubhex(signer);w1,w2=Ed25519PrivateKey.generate(),Ed25519PrivateKey.generate()
    m={'system_id':sid,'owned_domains':[sid+'.domain'],'mutation_rights':[],
       'interfaces':[{'name':'handoff','version':'1','required_inputs':['manifest'],'emitted_outputs':['packet'],'assumptions':['signed'],'invariants':[invariant]}],
       'requires':[],'forbids':[],'shared_state':[],'coordination_contracts':[]}
    prior={'detector':'Collision Detector','version':'0.2.1','collision_free':True,'findings':[],'boundary_gate':True,'non_interference_gate':True};art=(sid+' artifact').encode()
    old=[b'a',b'b',b'c',b'd'];item=canonical_json(m);new=old+[item];old_root=mth(old).hex();new_root=mth(new).hex();when=iso(NOW-timedelta(seconds=20))
    tp={'required':True,'hash_algorithm':'SHA-256','witness_algorithm':'Ed25519','log_id':'ascension-test-log','trusted_checkpoint':{'tree_size':4,'root_hash':old_root},'witness_keys':{'w1':pubhex(w1),'w2':pubhex(w2)},'minimum_witnesses':2,'max_witness_age_seconds':300,'future_tolerance_seconds':60}
    pol={'policy_version':1,'minimum_policy_version':1,'allowed_algorithms':['Ed25519'],'max_age_seconds':3600,'signers':{'root':{'public_key_hex':pub,'allowed_subjects':[sid],'roles':['root']}},'thresholds':{sid:{'role':'root','minimum':1}},'transparency_policy':tp}
    att=create_attestation(signer_id='root',subject=sid,manifest=m,artifact_bytes=art,collision_report=prior,issued_at=NOW-timedelta(minutes=1),private_key=signer,policy_version=1,evidence_class='manifest')
    evidence={'inclusion':{'leaf_index':4,'tree_size':5,'path':ipath(new,4),'root_hash':new_root},'transition':{'first_size':4,'second_size':5,'first_root_hash':old_root,'second_root_hash':new_root,'consistency_path':proof(4,new),'witness_observations':[observation(w1,'w1',tp['log_id'],5,new_root,when),observation(w2,'w2',tp['log_id'],5,new_root,when)]}}
    return {'manifest':m,'artifact_bytes':art,'prior_collision_report':prior,'attestations':[att],'trust_policy':pol,'now':NOW,'transparency_evidence':evidence,'backend_contract':a3.build_backend_contract(pol)}

if __name__=='__main__':unittest.main()
