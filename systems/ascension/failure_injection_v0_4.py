import copy, random
import manifest_trust_collision_adapter_v0_4 as a4
from test_adapter_v0_4 import fixture

rng=random.Random(20260925)
counts={}

def reject(f):
    r=a4.normalize_trusted_manifest(**f)
    return (not r['accepted']) and r['safe_for_siblings']

n=500; ok=0
for _ in range(n):
    f=fixture(); k=rng.choice(['inclusion','transition','transparency','collision','inclusion_schema'])
    f['backend_contract'][k]='SUBSTITUTED-'+str(rng.randrange(10**12))
    ok += reject(f)
counts['backend_substitutions_rejected']=(ok,n)

n=500; ok=0
for _ in range(n):
    f=fixture(); tp=f['trust_policy']['transparency_policy']
    if rng.randrange(2): tp['minimum_witnesses']=1
    else: tp['log_id']='substituted-'+str(rng.randrange(10**12))
    r=a4.normalize_trusted_manifest(**f)
    ok += ((not r['accepted']) and 'transparency_policy_digest_mismatch' in r['reasons'])
counts['pinned_policy_substitutions_rejected']=(ok,n)

n=500; ok=0
for _ in range(n):
    f=fixture(); path=f['transparency_evidence']['inclusion']['path']; j=rng.randrange(len(path)); b=bytearray(path[j]); b[rng.randrange(32)]^=1 << rng.randrange(8); path[j]=bytes(b)
    ok += reject(f)
counts['strict_inclusion_node_mutations_rejected']=(ok,n)

n=500; ok=0
for _ in range(n):
    f=fixture(); f['transparency_evidence']['inclusion']['leaf_index']=rng.randrange(0,4)
    ok += reject(f)
counts['false_index_relabels_rejected']=(ok,n)

n=400; ok=0
for _ in range(n):
    f=fixture(); sig=f['transparency_evidence']['transition']['witness_observations'][0]['signature_hex']; pos=rng.randrange(len(sig)); ch='0' if sig[pos]!='0' else '1'; f['transparency_evidence']['transition']['witness_observations'][0]['signature_hex']=sig[:pos]+ch+sig[pos+1:]
    ok += reject(f)
counts['witness_mutations_rejected']=(ok,n)

n=300; ok=0
for i in range(n):
    f=fixture(); mode=i%5
    if mode==0: f['manifest']='bad'
    elif mode==1: f['artifact_bytes']=rng.randrange(1000)
    elif mode==2: f['trust_policy']=[]
    elif mode==3: f['attestations']={'bad':'mapping'}
    else: f['prior_collision_report']=None
    r=a4.normalize_trusted_manifest(**f)
    ok += ((not r['accepted']) and r['safe_for_siblings'])
counts['malformed_inputs_fail_closed_safe_for_siblings']=(ok,n)

n=500; ok=0
for _ in range(n):
    f=fixture(); key=rng.choice(['trust','inclusion','transition','collision'])
    f['backend_contract']['backend_artifact_sha256'][key]='00'*32
    ok += reject(f)
counts['dependency_digest_contract_substitutions_rejected']=(ok,n)

f=fixture(); r=a4.normalize_trusted_manifest(**f); assert r['accepted'],r['reasons']; original=r['normalized_manifest']
required=list(a4.PROVENANCE_REQUIRED); ok=0
for key in required:
    nrm=copy.deepcopy(original); nrm['provenance'].pop(key,None)
    v=a4.validate_normalized_manifest(nrm,f['backend_contract'])
    ok += (not v['valid'])
counts['provenance_deletions_detected']=(ok,len(required))

for k,(a,b) in counts.items():
    print(f'{k.upper()}={a}/{b}')
    if a!=b: raise SystemExit(f'failure: {k} {a}/{b}')
print('TOTAL_ATTACKS='+str(sum(b for a,b in counts.values())))
