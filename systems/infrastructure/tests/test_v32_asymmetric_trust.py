import base64, json, dataclasses
import pytest

from durable_journal import DurableProofJournal
from infrastructure_loop import InfrastructureSupervisoryLoop, LoopConfig
from recovery_auth import AuthenticatedRecoveryEnvelope
from recovery_chain import AppendOnlyRecoveryChain, AuthenticatedRecoveryChain
from recovery_key_policy import RecoveryKeyPolicy, RecoveryKeyPolicyStore, PolicyBoundRecoveryAuthenticator
from test_proof_journal import fixture

from recovery_asymmetric import (
    Ed25519RecoverySigner, Ed25519RecoveryVerifier, Ed25519RecoveryKeyring,
    Ed25519RecoveryKeyPolicyAuthority, RecoveryTrustRootManifest,
    TrustRootKey, public_key_fingerprint,
)

def make_signer(key_id="k1"):
    return Ed25519RecoverySigner.generate("producer", key_id=key_id)

def test_signer_and_public_only_verifier_roundtrip():
    signer=make_signer()
    verifier=signer.verifier()
    ring=Ed25519RecoveryKeyring("producer",{signer.key_id:verifier},signer=signer)
    e=ring.sign({"generation":1,"x":1})
    assert ring.verify(e)
    verify_only=Ed25519RecoveryKeyring("producer",{signer.key_id:verifier})
    assert verify_only.verify(e)
    with pytest.raises(PermissionError): verify_only.sign({"generation":2})

def test_wrong_public_key_rejected():
    a=make_signer("k1"); b=make_signer("k1")
    e=Ed25519RecoveryKeyring("producer",{"k1":a.verifier()},signer=a).sign({"generation":1})
    assert not Ed25519RecoveryKeyring("producer",{"k1":b.verifier()}).verify(e)

def test_algorithm_confusion_rejected():
    s=make_signer()
    ring=Ed25519RecoveryKeyring("producer",{"k1":s.verifier()},signer=s)
    e=ring.sign({"generation":1})
    bad=AuthenticatedRecoveryEnvelope(e.version,e.producer_id,"HMAC-SHA256",e.payload_hash,e.payload,e.signature,e.key_id)
    assert not ring.verify(bad)

def test_public_key_fingerprint_is_bound_and_substitution_rejected():
    s=make_signer()
    ring=Ed25519RecoveryKeyring("producer",{"k1":s.verifier()},signer=s)
    e=ring.sign({"generation":1})
    assert e.payload["public_key_fingerprint"]==s.public_key_fingerprint
    other=make_signer("k1")
    substituted=dict(e.payload); substituted["public_key_fingerprint"]=other.public_key_fingerprint
    bad=AuthenticatedRecoveryEnvelope(e.version,e.producer_id,e.algorithm,e.payload_hash,substituted,e.signature,e.key_id)
    assert not ring.verify(bad)

def test_manifest_roundtrip_contains_no_private_key_and_detects_tamper(tmp_path):
    s=make_signer()
    p=Ed25519RecoverySigner.generate("policy-root",key_id="policy")
    manifest=RecoveryTrustRootManifest.issue(
        producer_id="producer",
        producer_keys=(TrustRootKey.from_verifier(s.verifier(),purpose="recovery-producer"),),
        policy_authority=TrustRootKey.from_verifier(p.verifier(),purpose="policy-authority"),
    )
    path=tmp_path/"trust-root.json"; manifest.write(path,fsync=False)
    raw=path.read_text()
    assert "PRIVATE KEY" not in raw and "private_key" not in raw
    loaded=RecoveryTrustRootManifest.read(path)
    assert loaded is not None and loaded.verify()
    m=json.loads(raw); m["producer_keys"][0]["fingerprint"]="0"*64; path.write_text(json.dumps(m))
    assert RecoveryTrustRootManifest.read(path) is None

def test_manifest_builds_public_only_recovery_keyring():
    s=make_signer()
    p=Ed25519RecoverySigner.generate("policy-root",key_id="policy")
    manifest=RecoveryTrustRootManifest.issue(
        producer_id="producer",
        producer_keys=(TrustRootKey.from_verifier(s.verifier(),purpose="recovery-producer"),),
        policy_authority=TrustRootKey.from_verifier(p.verifier(),purpose="policy-authority"),
    )
    ring=manifest.recovery_keyring()
    signing=Ed25519RecoveryKeyring("producer",{"k1":s.verifier()},signer=s)
    e=signing.sign({"generation":1})
    assert ring.verify(e)
    with pytest.raises(PermissionError): ring.sign({"generation":2})

def test_asymmetric_policy_authority_sign_and_verify_only(tmp_path):
    root_signer=Ed25519RecoverySigner.generate("policy-root",key_id="policy")
    signing_authority=Ed25519RecoveryKeyPolicyAuthority(root_signer)
    verify_authority=Ed25519RecoveryKeyPolicyAuthority(verifier=root_signer.verifier())
    policy=RecoveryKeyPolicy.issue(
        epoch=1,previous_policy_hash="0"*64,producer_id="producer",
        effective_generation=1,active_key_id="k1",trusted_key_ids=("k1",),
    )
    signed=signing_authority.sign(policy)
    assert verify_authority.verify(signed)
    with pytest.raises(PermissionError): verify_authority.sign(policy)

def test_policy_bound_ed25519_rotation():
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as d:
        d=__import__("pathlib").Path(d)
        root_signer=Ed25519RecoverySigner.generate("policy-root",key_id="policy")
        store=RecoveryKeyPolicyStore(d/"policy",Ed25519RecoveryKeyPolicyAuthority(root_signer))
        s1=make_signer("k1"); s2=make_signer("k2")
        p1=RecoveryKeyPolicy.issue(
            epoch=1,previous_policy_hash="0"*64,producer_id="producer",
            effective_generation=1,active_key_id="k1",trusted_key_ids=("k1",),
        )
        store.append(p1,fsync=False)
        ring1=Ed25519RecoveryKeyring("producer",{"k1":s1.verifier(),"k2":s2.verifier()},signer=s1)
        bound1=PolicyBoundRecoveryAuthenticator(ring1,store)
        e1=bound1.sign({"generation":1})
        assert bound1.verify(e1)
        p2=RecoveryKeyPolicy.issue(
            epoch=2,previous_policy_hash=p1.policy_hash,producer_id="producer",
            effective_generation=2,active_key_id="k2",trusted_key_ids=("k1","k2"),retired_key_ids=("k1",),
        )
        store.append(p2,fsync=False)
        ring2=Ed25519RecoveryKeyring("producer",{"k1":s1.verifier(),"k2":s2.verifier()},signer=s2)
        bound2=PolicyBoundRecoveryAuthenticator(ring2,store)
        assert bound2.verify(e1)
        e2=bound2.sign({"generation":2})
        assert e2.key_id=="k2" and bound2.verify(e2)

def seed(tmp_path):
    journal=tmp_path/"proof.journal"; tx=fixture()
    DurableProofJournal(journal).append(dataclasses.asdict(tx),fsync=False)
    return journal,tx

def cfg(tmp_path,journal,auth):
    return LoopConfig(
        durable_proof_journal_path=str(journal),startup_recovery_enabled=True,
        startup_recovery_now=20,recovery_chain_dir=str(tmp_path/"chain"),
        recovery_checkpoint_fsync=False,recovery_chain_lock_timeout_seconds=.01,
        recovery_authenticator=auth,
    )

def test_startup_can_verify_with_public_only_ed25519_keyring(tmp_path):
    journal,tx=seed(tmp_path)
    s=make_signer()
    signing=Ed25519RecoveryKeyring("producer",{"k1":s.verifier()},signer=s)
    first=InfrastructureSupervisoryLoop([],config=cfg(tmp_path,journal,signing))
    assert first._recovered_proof_transactions==()
    verify_only=Ed25519RecoveryKeyring("producer",{"k1":s.verifier()})
    second=InfrastructureSupervisoryLoop([],config=cfg(tmp_path,journal,verify_only))
    assert [x.transaction_hash for x in second._recovered_proof_transactions]==[tx.transaction_hash]
    # Read-only verifier cannot append a new generation; fail-open supervision, fail-closed advancement.
    assert AppendOnlyRecoveryChain(tmp_path/"chain").verify_chain().generation==1

def test_asymmetric_components_have_no_infrastructure_authority():
    s=make_signer()
    objs=[s,s.verifier(),Ed25519RecoveryKeyring("producer",{"k1":s.verifier()},signer=s)]
    forbidden={"execute","mutate","promote","rollback","acquire","release"}
    for obj in objs:
        assert forbidden.isdisjoint(dir(obj))

def test_stale_manifest_cannot_verify_new_rotated_key():
    old=make_signer("old"); new=make_signer("new")
    policy_root=Ed25519RecoverySigner.generate("policy-root",key_id="policy")
    stale=RecoveryTrustRootManifest.issue(
        producer_id="producer",
        producer_keys=(TrustRootKey.from_verifier(old.verifier(),purpose="recovery-producer"),),
        policy_authority=TrustRootKey.from_verifier(policy_root.verifier(),purpose="policy-authority"),
    )
    newest=Ed25519RecoveryKeyring(
        "producer",{"old":old.verifier(),"new":new.verifier()},signer=new
    ).sign({"generation":2})
    assert not stale.recovery_keyring().verify(newest)

def test_policy_store_can_be_reopened_with_public_only_authority(tmp_path):
    root_signer=Ed25519RecoverySigner.generate("policy-root",key_id="policy")
    signing=Ed25519RecoveryKeyPolicyAuthority(root_signer)
    store=RecoveryKeyPolicyStore(tmp_path/"policy",signing)
    p1=RecoveryKeyPolicy.issue(
        epoch=1,previous_policy_hash="0"*64,producer_id="producer",
        effective_generation=1,active_key_id="k1",trusted_key_ids=("k1",),
    )
    store.append(p1,fsync=False)
    verify_only=RecoveryKeyPolicyStore(
        tmp_path/"policy",
        Ed25519RecoveryKeyPolicyAuthority(verifier=root_signer.verifier())
    )
    assert verify_only.verify_chain().valid
