import copy, random, string
import sibling_manifest_conformance_v0_1 as c
from test_conformance_v0_1 import full_export

rng=random.Random(20260925)

def del_path(obj,path):
    x=obj
    for k in path[:-1]: x=x[k]
    del x[path[-1]]

structural_paths=[
 ("export_version",),("sibling_id",),("manifest","system_id"),("manifest","owned_domains"),("manifest","mutation_rights"),("manifest","interfaces"),("manifest","requires"),("manifest","forbids"),("manifest","shared_state"),("manifest","coordination_contracts"),
 ("artifact","sha256"),("artifact","content_ref"),("authority","owner_system"),("authority","attestation","plugin_evidence_id"),("authority","attestation","subject_sha256"),("authority","attestation","predicate_type"),("authority","attestation","envelope_ref"),("authority","attestation","envelope_sha256"),("authority","attestation","verification_material_sha256"),("authority","attestation","signer_identity"),("authority","attestation","attestation_format"),("authority","attestation","artifact_id"),
 ("authority","verification_receipt","attestation_id"),("authority","verification_receipt","verifier_id"),("authority","verification_receipt","trusted_root_id"),("authority","verification_receipt","verification_policy_id"),("authority","verification_receipt","checks"),("authority","verification_receipt","external_verification_ref")
]
adapter_paths=[
 ("adapter_v0_4_evidence","prior_collision_report"),("adapter_v0_4_evidence","trust_policy"),("adapter_v0_4_evidence","attestations"),("adapter_v0_4_evidence","transparency_evidence"),("adapter_v0_4_evidence","backend_contract"),
 ("adapter_v0_4_evidence","transparency_evidence","inclusion"),("adapter_v0_4_evidence","transparency_evidence","transition")
]
counts={}
# 1000 structural deletions must remove structural conformance.
n=0
for i in range(1000):
    x=full_export(); p=rng.choice(structural_paths); del_path(x,p); r=c.validate_export(x)
    if not r["conformant"]: n+=1
assert n==1000; counts["structural_deletions_rejected"]=n
# 1000 adapter evidence deletions must remove adapter readiness (may remain structurally conformant).
n=0
for i in range(1000):
    x=full_export(); p=rng.choice(adapter_paths); del_path(x,p); r=c.validate_export(x)
    if not r["ready_for_adapter_v0_4"]: n+=1
assert n==1000; counts["adapter_deletions_not_ready"]=n
# 750 digest corruptions.
n=0
for i in range(750):
    x=full_export(); target=rng.choice([("artifact","sha256"),("authority","attestation","subject_sha256"),("authority","attestation","envelope_sha256"),("authority","attestation","verification_material_sha256")])
    y=x
    for k in target[:-1]: y=y[k]
    y[target[-1]]=rng.choice(["x"*64,"0"*63,"G"*64,"deadbeef"])
    r=c.validate_export(x)
    if not r["conformant"]: n+=1
assert n==750; counts["digest_corruptions_rejected"]=n
# 750 identity substitutions.
n=0
for i in range(750):
    x=full_export(); which=rng.randrange(4)
    if which==0: x["manifest"]["system_id"]="VECTOR"
    elif which==1: x["authority"]["owner_system"]="JANUS"
    elif which==2: x["authority"]["verification_receipt"]["attestation_id"]="external-attestation:"+"0"*64
    else: x["authority"]["attestation"]["plugin_evidence_id"]="plugin-evidence:"+"0"*64
    if not c.validate_export(x)["conformant"]: n+=1
assert n==750; counts["identity_substitutions_rejected"]=n
# 500 backend substitutions.
n=0
keys=list(c.ADAPTER_BACKENDS)
for i in range(500):
    x=full_export(); k=rng.choice(keys); x["adapter_v0_4_evidence"]["backend_contract"][k]="substituted-"+str(i)
    if not c.validate_export(x)["ready_for_adapter_v0_4"]: n+=1
assert n==500; counts["backend_substitutions_not_ready"]=n
# 500 receipt attacks: false, duplicate, or missing mandatory checks.
n=0
for i in range(500):
    x=full_export(); checks=x["authority"]["verification_receipt"]["checks"]; j=rng.randrange(3)
    if j==0: checks[rng.randrange(len(checks))][1]=False
    elif j==1: checks.append(list(rng.choice(checks)))
    else: checks.pop(rng.randrange(len(checks)))
    if not c.validate_export(x)["conformant"]: n+=1
assert n==500; counts["receipt_attacks_rejected"]=n
# 300 secret injections anywhere inside extensions.
n=0
secret_names=list(c.FORBIDDEN_SECRET_NAMES)
for i in range(300):
    x=full_export(); x["extensions"]={rng.choice(secret_names):"TOP-SECRET-"+str(i)}
    if not c.validate_export(x)["conformant"]: n+=1
assert n==300; counts["secret_injections_rejected"]=n
# 500 malformed top-level values must not crash and must remain unauthenticated.
malformed=[None, 3, "x", [], [1,2], b"x", {"export_version":0}, {"sibling_id":[]}, {"manifest":"bad"}]
n=0
for i in range(500):
    x=copy.deepcopy(rng.choice(malformed)); r=c.validate_export(x)
    if (not r["authenticated"]) and (not r["ready_for_adapter_v0_4"]): n+=1
assert n==500; counts["malformed_fail_closed"]=n

# 500 backend dependency-digest substitutions.
n=0
for i in range(500):
    x=full_export(); k=rng.choice(list(c.ADAPTER_DEPENDENCY_SHA256)); x["adapter_v0_4_evidence"]["backend_contract"]["backend_artifact_sha256"][k]="0"*64
    if not c.validate_export(x)["ready_for_adapter_v0_4"]: n+=1
assert n==500; counts["backend_digest_substitutions_not_ready"]=n

# 500 transparency-policy digest substitutions.
n=0
for i in range(500):
    x=full_export(); x["adapter_v0_4_evidence"]["backend_contract"]["transparency_policy_sha256"]=("0" if i%2==0 else "1")*64
    if not c.validate_export(x)["ready_for_adapter_v0_4"]: n+=1
assert n==500; counts["policy_digest_substitutions_not_ready"]=n

# 500 signed-attestation shape corruptions.
n=0
for i in range(500):
    x=full_export(); att=x["adapter_v0_4_evidence"]["attestations"][0]
    if i%2==0: att.pop("signature_hex",None)
    else: att["payload"].pop(rng.choice(list(att["payload"])),None)
    if not c.validate_export(x)["ready_for_adapter_v0_4"]: n+=1
assert n==500; counts["attestation_shape_corruptions_not_ready"]=n

print(counts)
print("TOTAL_ATTACK_CASES",sum(counts.values()))
