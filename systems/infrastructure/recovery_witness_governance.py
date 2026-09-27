"""Signed witness-set governance and transparency checkpoints (V35).

Evidence trust only. Governance configures which witnesses can attest recovery trust-root
history; it never grants infrastructure mutation authority.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from recovery_asymmetric import (
    ALGORITHM as ED25519_ALGORITHM,
    Ed25519RecoverySigner,
    Ed25519RecoveryVerifier,
    TrustRootKey,
)
from recovery_trust_root import RecoveryTrustRootVerdict
from recovery_witness import TrustRootWitnessVerifier, WitnessQuorumVerifier

GOVERNANCE_SCHEMA = "infra-recovery-witness-governance/v1"
TRANSPARENCY_SCHEMA = "infra-recovery-transparency-checkpoint/v1"
GENESIS = "0" * 64


def _canon(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _hash(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _atomic_write(path: Path, payload: Mapping[str, Any], *, fsync: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with tmp.open("xb") as f:
            f.write(_canon(payload) + b"\n")
            f.flush()
            if fsync:
                os.fsync(f.fileno())
        os.replace(tmp, path)
        if fsync and os.name != "nt":
            fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
    finally:
        if tmp.exists():
            tmp.unlink()


@dataclass(frozen=True)
class WitnessGovernanceEpoch:
    schema: str
    epoch: int
    previous_epoch_hash: str
    effective_trust_root_generation: int
    threshold: int
    witness_keys: tuple[TrustRootKey, ...]
    epoch_hash: str

    @classmethod
    def issue(
        cls, *, epoch: int, previous_epoch_hash: str, effective_trust_root_generation: int,
        threshold: int, witness_keys: tuple[TrustRootKey, ...],
    ):
        keys = tuple(sorted(tuple(witness_keys), key=lambda x: (x.subject_id, x.key_id, x.fingerprint)))
        if epoch < 1 or effective_trust_root_generation < 1:
            raise ValueError("invalid governance epoch")
        if threshold < 1 or threshold > len(keys):
            raise ValueError("threshold must fit witness set")
        identities=[(k.subject_id,k.key_id,k.fingerprint) for k in keys]
        subjects=[k.subject_id for k in keys]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate witness identity/key")
        if len(subjects) != len(set(subjects)):
            raise ValueError("one public key identity per witness subject is required")
        if any(not k.verify() or k.purpose != "trust-root-witness" for k in keys):
            raise ValueError("invalid witness public key")
        body={
            "schema":GOVERNANCE_SCHEMA,
            "epoch":epoch,
            "previous_epoch_hash":str(previous_epoch_hash),
            "effective_trust_root_generation":effective_trust_root_generation,
            "threshold":threshold,
            "witness_keys":[k.to_mapping() for k in keys],
        }
        return cls(
            GOVERNANCE_SCHEMA,epoch,str(previous_epoch_hash),effective_trust_root_generation,
            threshold,keys,_hash(body)
        )

    def body(self):
        return {
            "schema":self.schema,
            "epoch":self.epoch,
            "previous_epoch_hash":self.previous_epoch_hash,
            "effective_trust_root_generation":self.effective_trust_root_generation,
            "threshold":self.threshold,
            "witness_keys":[k.to_mapping() for k in self.witness_keys],
        }

    def verify(self):
        try:
            ids=[(k.subject_id,k.key_id,k.fingerprint) for k in self.witness_keys]
            return (
                self.schema==GOVERNANCE_SCHEMA
                and self.epoch>=1
                and self.effective_trust_root_generation>=1
                and 1<=self.threshold<=len(self.witness_keys)
                and len(ids)==len(set(ids))
                and all(k.verify() and k.purpose=="trust-root-witness" for k in self.witness_keys)
                and self.epoch_hash==_hash(self.body())
            )
        except Exception:
            return False

    def to_mapping(self):
        return {**self.body(),"epoch_hash":self.epoch_hash}

    @classmethod
    def from_mapping(cls,m):
        return cls(
            str(m["schema"]),int(m["epoch"]),str(m["previous_epoch_hash"]),
            int(m["effective_trust_root_generation"]),int(m["threshold"]),
            tuple(TrustRootKey.from_mapping(x) for x in m["witness_keys"]),
            str(m["epoch_hash"]),
        )

    def verifier_map(self):
        return {
            k.subject_id: TrustRootWitnessVerifier.from_ed25519_verifier(k.verifier())
            for k in self.witness_keys
        }


@dataclass(frozen=True)
class SignedWitnessGovernanceEpoch:
    epoch: WitnessGovernanceEpoch
    authority_id: str
    algorithm: str
    public_key_fingerprint: str
    signature: str

    def to_mapping(self):
        return {
            "epoch":self.epoch.to_mapping(),
            "authority_id":self.authority_id,
            "algorithm":self.algorithm,
            "public_key_fingerprint":self.public_key_fingerprint,
            "signature":self.signature,
        }

    @classmethod
    def from_mapping(cls,m):
        return cls(
            WitnessGovernanceEpoch.from_mapping(m["epoch"]),str(m["authority_id"]),
            str(m["algorithm"]),str(m["public_key_fingerprint"]),str(m["signature"])
        )


class WitnessGovernanceAuthority:
    """Independent governance signer or public-only verifier."""
    def __init__(
        self, signer: Ed25519RecoverySigner | None = None,
        *, verifier: Ed25519RecoveryVerifier | None = None,
    ):
        if signer is None and verifier is None:
            raise ValueError("signer or verifier required")
        if signer is not None:
            own=signer.verifier()
            if verifier is not None and verifier.public_key_fingerprint!=own.public_key_fingerprint:
                raise ValueError("governance signer/verifier mismatch")
            verifier=own
        self._signer=signer
        self._verifier=verifier
        self.authority_id=verifier.producer_id

    @property
    def can_sign(self):
        return self._signer is not None

    def _epoch_message(self,epoch):
        return _canon({
            "domain":"witness-governance",
            "authority_id":self.authority_id,
            "algorithm":ED25519_ALGORITHM,
            "public_key_fingerprint":self._verifier.public_key_fingerprint,
            "epoch":epoch.to_mapping(),
        })

    def sign(self,epoch:WitnessGovernanceEpoch):
        if self._signer is None:
            raise PermissionError("verification-only witness governance authority")
        if not epoch.verify():
            raise ValueError("invalid governance epoch")
        return SignedWitnessGovernanceEpoch(
            epoch,self.authority_id,ED25519_ALGORITHM,self._verifier.public_key_fingerprint,
            self._signer.sign_bytes(self._epoch_message(epoch))
        )

    def verify(self,signed:SignedWitnessGovernanceEpoch):
        return bool(
            signed.authority_id==self.authority_id
            and signed.algorithm==ED25519_ALGORITHM
            and signed.public_key_fingerprint==self._verifier.public_key_fingerprint
            and signed.epoch.verify()
            and self._verifier.verify_bytes(self._epoch_message(signed.epoch),signed.signature)
        )

    def sign_transparency(self,checkpoint):
        if self._signer is None:
            raise PermissionError("verification-only witness governance authority")
        if not checkpoint.verify():
            raise ValueError("invalid transparency checkpoint")
        message=_canon({
            "domain":"witness-transparency",
            "authority_id":self.authority_id,
            "algorithm":ED25519_ALGORITHM,
            "public_key_fingerprint":self._verifier.public_key_fingerprint,
            "checkpoint":checkpoint.to_mapping(),
        })
        return SignedTransparencyCheckpoint(
            checkpoint,self.authority_id,ED25519_ALGORITHM,self._verifier.public_key_fingerprint,
            self._signer.sign_bytes(message)
        )

    def verify_transparency(self,signed):
        message=_canon({
            "domain":"witness-transparency",
            "authority_id":signed.authority_id,
            "algorithm":signed.algorithm,
            "public_key_fingerprint":signed.public_key_fingerprint,
            "checkpoint":signed.checkpoint.to_mapping(),
        })
        return bool(
            signed.authority_id==self.authority_id
            and signed.algorithm==ED25519_ALGORITHM
            and signed.public_key_fingerprint==self._verifier.public_key_fingerprint
            and signed.checkpoint.verify()
            and self._verifier.verify_bytes(message,signed.signature)
        )


@dataclass(frozen=True)
class WitnessGovernanceVerdict:
    valid: bool
    reason: str
    epoch: int


class WitnessGovernanceStore:
    """Append-only signed witness membership and quorum policy."""
    def __init__(self,directory,authority:WitnessGovernanceAuthority):
        self.directory=Path(directory)
        self.authority=authority

    def _path(self,epoch):
        return self.directory/f"witness-governance-{epoch:020d}.json"

    @property
    def head_path(self):
        return self.directory/"HEAD"

    def _read_signed(self,epoch):
        try:
            signed=SignedWitnessGovernanceEpoch.from_mapping(json.loads(self._path(epoch).read_text()))
            return signed if self.authority.verify(signed) else None
        except Exception:
            return None

    def _read_head(self):
        try:
            m=json.loads(self.head_path.read_text())
            return int(m["epoch"]),str(m["epoch_hash"])
        except Exception:
            return None

    @staticmethod
    def _transition(previous,current):
        if not current.verify():
            return False,"invalid witness governance epoch"
        if previous is None:
            if current.epoch!=1 or current.previous_epoch_hash!=GENESIS:
                return False,"invalid witness governance genesis"
            return True,"genesis"
        if current.epoch!=previous.epoch+1:
            return False,"witness governance epoch gap"
        if current.previous_epoch_hash!=previous.epoch_hash:
            return False,"witness governance linkage mismatch"
        if current.effective_trust_root_generation<=previous.effective_trust_root_generation:
            return False,"effective trust-root generation must increase"
        if current.threshold<previous.threshold:
            return False,"witness quorum threshold reduction rejected"
        prior={(k.subject_id,k.key_id,k.fingerprint) for k in previous.witness_keys}
        nxt={(k.subject_id,k.key_id,k.fingerprint) for k in current.witness_keys}
        if len(prior & nxt)<previous.threshold:
            return False,"witness-set rotation lacks prior-quorum overlap"
        return True,"transition valid"

    def append(self,epoch,*,fsync=True):
        verdict=self.verify_chain(allow_empty=True)
        if not verdict.valid:
            raise ValueError(f"invalid existing governance chain: {verdict.reason}")
        previous=self.epoch_at(verdict.epoch) if verdict.epoch else None
        ok,reason=self._transition(previous,epoch)
        if not ok:
            raise ValueError(reason)
        signed=self.authority.sign(epoch)
        target=self._path(epoch.epoch)
        if target.exists():
            raise FileExistsError("witness governance epoch already exists")
        _atomic_write(target,signed.to_mapping(),fsync=fsync)
        head={"epoch":epoch.epoch,"epoch_hash":epoch.epoch_hash}
        tmp=self.head_path.with_suffix(".tmp")
        try:
            with tmp.open("xb") as f:
                f.write(_canon(head)+b"\n"); f.flush()
                if fsync: os.fsync(f.fileno())
            os.replace(tmp,self.head_path)
            if fsync and os.name!='nt':
                fd=os.open(str(self.directory),os.O_RDONLY)
                try: os.fsync(fd)
                finally: os.close(fd)
        finally:
            if tmp.exists(): tmp.unlink()
        return signed

    def verify_chain(self,*,allow_empty=False):
        files=sorted(self.directory.glob("witness-governance-*.json")) if self.directory.exists() else []
        if not files:
            if allow_empty and not self.head_path.exists():
                return WitnessGovernanceVerdict(True,"empty",0)
            return WitnessGovernanceVerdict(False,"missing witness governance",0)
        previous=None
        for expected,path in enumerate(files,1):
            if path!=self._path(expected):
                return WitnessGovernanceVerdict(False,"witness governance epoch gap",expected-1)
            signed=self._read_signed(expected)
            if signed is None:
                return WitnessGovernanceVerdict(False,"witness governance signature/integrity invalid",expected-1)
            ok,reason=self._transition(previous,signed.epoch)
            if not ok:
                return WitnessGovernanceVerdict(False,reason,expected-1)
            previous=signed.epoch
        head=self._read_head()
        if head!=(len(files),previous.epoch_hash):
            return WitnessGovernanceVerdict(False,"witness governance HEAD rollback/replay mismatch",len(files))
        return WitnessGovernanceVerdict(True,"witness governance valid",len(files))

    def epoch_at(self,epoch):
        signed=self._read_signed(epoch) if epoch>=1 else None
        return signed.epoch if signed is not None else None

    def epoch_for_trust_root_generation(self,generation):
        verdict=self.verify_chain()
        if not verdict.valid:
            return None
        candidate=None
        for epoch in range(1,verdict.epoch+1):
            item=self.epoch_at(epoch)
            if item is None:
                return None
            if item.effective_trust_root_generation<=generation:
                candidate=item
            else:
                break
        return candidate


class GovernedWitnessedTrustRootStore:
    """Witness-quorum trust-root view whose membership and threshold come from signed governance."""
    def __init__(self,trust_root_store,receipt_store,governance_store:WitnessGovernanceStore):
        self.trust_root_store=trust_root_store
        self.receipt_store=receipt_store
        self.governance_store=governance_store

    def verify_chain(self,*,allow_empty=False):
        base=self.trust_root_store.verify_chain(allow_empty=allow_empty)
        if not base.valid:
            return base
        if base.generation==0:
            return RecoveryTrustRootVerdict(False,"governed witnessed trust-root cannot be empty",0)
        gv=self.governance_store.verify_chain()
        if not gv.valid:
            return RecoveryTrustRootVerdict(False,gv.reason,base.generation)
        policy=self.governance_store.epoch_for_trust_root_generation(base.generation)
        if policy is None:
            return RecoveryTrustRootVerdict(False,"no witness governance for trust-root HEAD",base.generation)
        q=WitnessQuorumVerifier(policy.verifier_map(),threshold=policy.threshold)
        verdict=q.verify_head(self.trust_root_store,self.receipt_store)
        if not verdict.valid:
            return RecoveryTrustRootVerdict(False,verdict.reason,base.generation)
        return RecoveryTrustRootVerdict(True,"trust-root and governed witness quorum valid",base.generation)

    def generation_at(self,generation):
        if not self.verify_chain().valid:
            return None
        return self.trust_root_store.generation_at(generation)

    def root_for_recovery_generation(self,recovery_generation):
        if not self.verify_chain().valid:
            return None
        return self.trust_root_store.root_for_recovery_generation(recovery_generation)


@dataclass(frozen=True)
class TransparencyCheckpoint:
    schema: str
    sequence: int
    previous_checkpoint_hash: str
    trust_root_generation: int
    trust_root_generation_hash: str
    governance_epoch: int
    governance_epoch_hash: str
    witness_receipt_hashes: tuple[str,...]
    checkpoint_hash: str

    @classmethod
    def issue(
        cls,*,sequence,previous_checkpoint_hash,trust_root_generation,
        trust_root_generation_hash,governance_epoch,governance_epoch_hash,
        witness_receipt_hashes,
    ):
        receipts=tuple(sorted(set(map(str,witness_receipt_hashes))))
        if sequence<1 or trust_root_generation<1 or governance_epoch<1:
            raise ValueError("invalid transparency checkpoint")
        if any(len(x)!=64 for x in (str(previous_checkpoint_hash),str(trust_root_generation_hash),str(governance_epoch_hash))):
            raise ValueError("invalid transparency hash")
        if not receipts or any(len(x)!=64 for x in receipts):
            raise ValueError("invalid witness receipt hashes")
        body={
            "schema":TRANSPARENCY_SCHEMA,"sequence":int(sequence),
            "previous_checkpoint_hash":str(previous_checkpoint_hash),
            "trust_root_generation":int(trust_root_generation),
            "trust_root_generation_hash":str(trust_root_generation_hash),
            "governance_epoch":int(governance_epoch),
            "governance_epoch_hash":str(governance_epoch_hash),
            "witness_receipt_hashes":list(receipts),
        }
        return cls(
            TRANSPARENCY_SCHEMA,int(sequence),str(previous_checkpoint_hash),
            int(trust_root_generation),str(trust_root_generation_hash),
            int(governance_epoch),str(governance_epoch_hash),receipts,_hash(body)
        )

    def body(self):
        return {
            "schema":self.schema,"sequence":self.sequence,
            "previous_checkpoint_hash":self.previous_checkpoint_hash,
            "trust_root_generation":self.trust_root_generation,
            "trust_root_generation_hash":self.trust_root_generation_hash,
            "governance_epoch":self.governance_epoch,
            "governance_epoch_hash":self.governance_epoch_hash,
            "witness_receipt_hashes":list(self.witness_receipt_hashes),
        }

    def verify(self):
        return bool(
            self.schema==TRANSPARENCY_SCHEMA and self.sequence>=1
            and self.trust_root_generation>=1 and self.governance_epoch>=1
            and self.checkpoint_hash==_hash(self.body())
        )

    def to_mapping(self):
        return {**self.body(),"checkpoint_hash":self.checkpoint_hash}

    @classmethod
    def from_mapping(cls,m):
        return cls(
            str(m["schema"]),int(m["sequence"]),str(m["previous_checkpoint_hash"]),
            int(m["trust_root_generation"]),str(m["trust_root_generation_hash"]),
            int(m["governance_epoch"]),str(m["governance_epoch_hash"]),
            tuple(map(str,m["witness_receipt_hashes"])),str(m["checkpoint_hash"])
        )


@dataclass(frozen=True)
class SignedTransparencyCheckpoint:
    checkpoint: TransparencyCheckpoint
    authority_id: str
    algorithm: str
    public_key_fingerprint: str
    signature: str

    def to_mapping(self):
        return {
            "checkpoint":self.checkpoint.to_mapping(),"authority_id":self.authority_id,
            "algorithm":self.algorithm,"public_key_fingerprint":self.public_key_fingerprint,
            "signature":self.signature,
        }

    @classmethod
    def from_mapping(cls,m):
        return cls(
            TransparencyCheckpoint.from_mapping(m["checkpoint"]),str(m["authority_id"]),
            str(m["algorithm"]),str(m["public_key_fingerprint"]),str(m["signature"])
        )


@dataclass(frozen=True)
class TransparencyVerdict:
    valid: bool
    reason: str
    sequence: int


class TransparencyCheckpointStore:
    def __init__(self,directory,authority:WitnessGovernanceAuthority):
        self.directory=Path(directory)
        self.authority=authority

    def _path(self,sequence):
        return self.directory/f"checkpoint-{sequence:020d}.json"

    @property
    def head_path(self):
        return self.directory/"HEAD"

    def _read_signed(self,sequence):
        try:
            signed=SignedTransparencyCheckpoint.from_mapping(json.loads(self._path(sequence).read_text()))
            return signed if self.authority.verify_transparency(signed) else None
        except Exception:
            return None

    def _read_head(self):
        try:
            m=json.loads(self.head_path.read_text())
            return int(m["sequence"]),str(m["checkpoint_hash"])
        except Exception:
            return None

    def append_current(self,trust_root_store,governance_store,receipt_store,*,fsync=True):
        base=trust_root_store.verify_chain()
        if not base.valid or base.generation<1:
            raise ValueError("cannot checkpoint invalid trust-root history")
        root=trust_root_store.generation_at(base.generation)
        gv=governance_store.verify_chain()
        if not gv.valid:
            raise ValueError("cannot checkpoint invalid witness governance")
        policy=governance_store.epoch_for_trust_root_generation(base.generation)
        if policy is None:
            raise ValueError("no applicable witness governance")
        quorum=WitnessQuorumVerifier(policy.verifier_map(),threshold=policy.threshold)
        qv=quorum.verify_head(trust_root_store,receipt_store)
        if not qv.valid:
            raise ValueError(f"witness quorum unavailable: {qv.reason}")
        receipt_hashes=[]
        for witness_id in sorted(policy.verifier_map()):
            ok,history=quorum._verify_history(witness_id,receipt_store)
            if not ok or not history:
                continue
            latest=history[-1]
            if (latest.trust_root_generation==root.generation
                    and latest.trust_root_generation_hash==root.generation_hash):
                receipt_hashes.append(latest.receipt_hash)
        if len(receipt_hashes)<policy.threshold:
            raise ValueError("insufficient verified witness receipts for transparency checkpoint")
        verdict=self.verify_chain(allow_empty=True)
        if not verdict.valid:
            raise ValueError(f"invalid existing transparency history: {verdict.reason}")
        previous=self.checkpoint_at(verdict.sequence) if verdict.sequence else None
        checkpoint=TransparencyCheckpoint.issue(
            sequence=verdict.sequence+1,
            previous_checkpoint_hash=(previous.checkpoint_hash if previous is not None else GENESIS),
            trust_root_generation=root.generation,
            trust_root_generation_hash=root.generation_hash,
            governance_epoch=policy.epoch,
            governance_epoch_hash=policy.epoch_hash,
            witness_receipt_hashes=tuple(receipt_hashes),
        )
        return self.append(checkpoint,fsync=fsync)

    def append(self,checkpoint,*,fsync=True):
        verdict=self.verify_chain(allow_empty=True)
        if not verdict.valid:
            raise ValueError(f"invalid transparency history: {verdict.reason}")
        if checkpoint.sequence!=verdict.sequence+1:
            raise ValueError("transparency sequence gap")
        previous=self.checkpoint_at(verdict.sequence) if verdict.sequence else None
        expected=previous.checkpoint_hash if previous is not None else GENESIS
        if checkpoint.previous_checkpoint_hash!=expected:
            raise ValueError("transparency checkpoint linkage mismatch")
        signed=self.authority.sign_transparency(checkpoint)
        target=self._path(checkpoint.sequence)
        if target.exists():
            raise FileExistsError("transparency checkpoint exists")
        _atomic_write(target,signed.to_mapping(),fsync=fsync)
        head={"sequence":checkpoint.sequence,"checkpoint_hash":checkpoint.checkpoint_hash}
        tmp=self.head_path.with_suffix(".tmp")
        try:
            with tmp.open("xb") as f:
                f.write(_canon(head)+b"\n"); f.flush()
                if fsync: os.fsync(f.fileno())
            os.replace(tmp,self.head_path)
            if fsync and os.name!='nt':
                fd=os.open(str(self.directory),os.O_RDONLY)
                try: os.fsync(fd)
                finally: os.close(fd)
        finally:
            if tmp.exists(): tmp.unlink()
        return signed

    def verify_chain(self,*,allow_empty=False):
        files=sorted(self.directory.glob("checkpoint-*.json")) if self.directory.exists() else []
        if not files:
            if allow_empty and not self.head_path.exists():
                return TransparencyVerdict(True,"empty",0)
            return TransparencyVerdict(False,"missing transparency history",0)
        previous=None
        for expected,path in enumerate(files,1):
            if path!=self._path(expected):
                return TransparencyVerdict(False,"transparency sequence gap",expected-1)
            signed=self._read_signed(expected)
            if signed is None:
                return TransparencyVerdict(False,"transparency signature/integrity invalid",expected-1)
            cp=signed.checkpoint
            expected_prior=previous.checkpoint_hash if previous is not None else GENESIS
            if cp.sequence!=expected or cp.previous_checkpoint_hash!=expected_prior:
                return TransparencyVerdict(False,"transparency linkage mismatch",expected-1)
            previous=cp
        if self._read_head()!=(len(files),previous.checkpoint_hash):
            return TransparencyVerdict(False,"transparency HEAD rollback/replay mismatch",len(files))
        return TransparencyVerdict(True,"transparency history valid",len(files))

    def checkpoint_at(self,sequence):
        signed=self._read_signed(sequence) if sequence>=1 else None
        return signed.checkpoint if signed is not None else None

    def export_digest(self):
        verdict=self.verify_chain()
        if not verdict.valid:
            return None
        cp=self.checkpoint_at(verdict.sequence)
        return {
            "sequence":cp.sequence,
            "checkpoint_hash":cp.checkpoint_hash,
            "trust_root_generation":cp.trust_root_generation,
            "trust_root_generation_hash":cp.trust_root_generation_hash,
            "governance_epoch":cp.governance_epoch,
            "governance_epoch_hash":cp.governance_epoch_hash,
        }


@dataclass(frozen=True)
class GossipVerdict:
    valid: bool
    reason: str
    equivocation: bool
    stale: bool


def compare_transparency_gossip(left,right):
    try:
        ls,rs=int(left["sequence"]),int(right["sequence"])
        lh,rh=str(left["checkpoint_hash"]),str(right["checkpoint_hash"])
    except Exception:
        return GossipVerdict(False,"malformed transparency gossip",False,False)
    if ls==rs:
        if lh==rh:
            return GossipVerdict(True,"matching transparency checkpoint",False,False)
        return GossipVerdict(False,"same-sequence split-view/equivocation",True,False)
    return GossipVerdict(False,"peer transparency checkpoint is stale",False,True)
