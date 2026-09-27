"""Append-only recovery checkpoint chain (V22). Integrity/continuity only; no mutation authority."""
from __future__ import annotations
import hashlib, json, os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from recovery_checkpoint import RecoveryCheckpoint

SCHEMA = "infra-recovery-chain/v1"
GENESIS = "0" * 64

def _canon(x: Mapping[str, Any]) -> bytes:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
def _hash(x: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canon(x)).hexdigest()

@dataclass(frozen=True)
class ChainedRecoveryCheckpoint:
    schema: str
    generation: int
    previous_checkpoint_hash: str
    recovery_checkpoint: RecoveryCheckpoint
    chain_hash: str
    @classmethod
    def issue(cls, recovery_checkpoint: RecoveryCheckpoint, *, generation: int, previous_checkpoint_hash: str):
        if generation < 1: raise ValueError("generation must be >= 1")
        if not recovery_checkpoint.verify(): raise ValueError("invalid recovery checkpoint")
        body={"schema":SCHEMA,"generation":generation,"previous_checkpoint_hash":previous_checkpoint_hash,
              "recovery_checkpoint":recovery_checkpoint.to_mapping()}
        return cls(SCHEMA,generation,previous_checkpoint_hash,recovery_checkpoint,_hash(body))
    def body(self):
        return {"schema":self.schema,"generation":self.generation,"previous_checkpoint_hash":self.previous_checkpoint_hash,
                "recovery_checkpoint":self.recovery_checkpoint.to_mapping()}
    def verify(self):
        return (self.schema==SCHEMA and self.generation>=1 and self.recovery_checkpoint.verify()
                and self.chain_hash==_hash(self.body()))
    def to_mapping(self): return {**self.body(),"chain_hash":self.chain_hash}
    @classmethod
    def from_mapping(cls,m):
        return cls(str(m["schema"]),int(m["generation"]),str(m["previous_checkpoint_hash"]),
                   RecoveryCheckpoint.from_mapping(m["recovery_checkpoint"]),str(m["chain_hash"]))

@dataclass(frozen=True)
class ChainVerdict:
    valid: bool
    reason: str
    generation: int
    head_hash: str | None

class AppendOnlyRecoveryChain:
    """One immutable file per generation plus an atomic head pointer."""
    def __init__(self, directory):
        self.directory=Path(directory); self.head_path=self.directory/"HEAD"
    def _entry_path(self,g): return self.directory/f"checkpoint-{g:020d}.json"
    def _read_entry(self,g):
        try: c=ChainedRecoveryCheckpoint.from_mapping(json.loads(self._entry_path(g).read_text()))
        except Exception: return None
        return c if c.verify() else None
    def head(self):
        try:
            m=json.loads(self.head_path.read_text()); g=int(m["generation"]); h=str(m["chain_hash"])
            c=self._read_entry(g)
            return c if c and c.chain_hash==h else None
        except Exception: return None
    def append(self, recovery_checkpoint: RecoveryCheckpoint, *, fsync=True):
        self.directory.mkdir(parents=True,exist_ok=True)
        prior=self.head(); generation=1 if prior is None else prior.generation+1
        prev=GENESIS if prior is None else prior.chain_hash
        c=ChainedRecoveryCheckpoint.issue(recovery_checkpoint,generation=generation,previous_checkpoint_hash=prev)
        target=self._entry_path(generation)
        if target.exists(): raise FileExistsError("generation already exists")
        tmp=target.with_suffix(".tmp"); payload=_canon(c.to_mapping())+b"\n"
        with tmp.open("xb") as f:
            f.write(payload); f.flush()
            if fsync: os.fsync(f.fileno())
        os.replace(tmp,target)
        htmp=self.head_path.with_suffix(".tmp")
        with htmp.open("wb") as f:
            f.write(_canon({"generation":generation,"chain_hash":c.chain_hash})+b"\n"); f.flush()
            if fsync: os.fsync(f.fileno())
        os.replace(htmp,self.head_path)
        if fsync and os.name!='nt':
            fd=os.open(str(self.directory),os.O_RDONLY)
            try: os.fsync(fd)
            finally: os.close(fd)
        return c
    def verify_chain(self):
        files=sorted(self.directory.glob("checkpoint-*.json")) if self.directory.exists() else []
        if not files: return ChainVerdict(True,"empty",0,None)
        prev=GENESIS
        for i,p in enumerate(files,1):
            if p != self._entry_path(i): return ChainVerdict(False,"generation gap or stale replay",i-1,None)
            c=self._read_entry(i)
            if not c: return ChainVerdict(False,"invalid checkpoint entry",i-1,None)
            if c.generation!=i or c.previous_checkpoint_hash!=prev: return ChainVerdict(False,"fork or linkage mismatch",i-1,None)
            prev=c.chain_hash
        head=self.head()
        if not head or head.generation!=len(files) or head.chain_hash!=prev:
            return ChainVerdict(False,"stale or substituted HEAD",len(files),prev)
        return ChainVerdict(True,"continuous",len(files),prev)

@dataclass(frozen=True)
class AuthChainVerdict:
    valid: bool
    reason: str
    generation: int

class AuthenticatedRecoveryChain:
    """Authenticated recovery evidence sidecar; never grants mutation authority."""
    def __init__(self, directory, authenticator):
        self.directory = Path(directory)
        self.authenticator = authenticator
    def _path(self, generation):
        return self.directory / f"auth-{generation:020d}.json"
    def append(self, recovery_checkpoint, *, fsync=True):
        self.directory.mkdir(parents=True, exist_ok=True)
        files = sorted(self.directory.glob("auth-*.json"))
        generation = len(files) + 1
        payload = {
            "generation": generation,
            "checkpoint_hash": recovery_checkpoint.checkpoint_hash,
            "recovery_checkpoint": recovery_checkpoint.to_mapping(),
        }
        envelope = self.authenticator.sign(payload)
        record = {"envelope": {
            "version": envelope.version,
            "producer_id": envelope.producer_id,
            "algorithm": envelope.algorithm,
            "key_id": envelope.key_id,
            "payload_hash": envelope.payload_hash,
            "payload": dict(envelope.payload),
            "signature": envelope.signature,
        }}
        target = self._path(generation)
        if target.exists():
            raise FileExistsError("authenticated generation already exists")
        tmp = target.with_suffix(".tmp")
        with tmp.open("xb") as f:
            f.write(_canon(record) + b"\n")
            f.flush()
            if fsync: os.fsync(f.fileno())
        os.replace(tmp, target)
        return envelope
    def verify_chain(self):
        from recovery_auth import AuthenticatedRecoveryEnvelope
        files = sorted(self.directory.glob("auth-*.json")) if self.directory.exists() else []
        for expected, path in enumerate(files, 1):
            if path != self._path(expected):
                return AuthChainVerdict(False, "generation gap", expected - 1)
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                x = record["envelope"]
                envelope = AuthenticatedRecoveryEnvelope(
                    int(x["version"]), str(x["producer_id"]), str(x["algorithm"]),
                    str(x["payload_hash"]), x["payload"], str(x["signature"]), str(x.get("key_id", ""))
                )
                if int(envelope.payload["generation"]) != expected:
                    return AuthChainVerdict(False, "generation mismatch", expected - 1)
                if not self.authenticator.verify(envelope):
                    return AuthChainVerdict(False, "authentication failed", expected - 1)
                checkpoint = RecoveryCheckpoint.from_mapping(envelope.payload["recovery_checkpoint"])
                if not checkpoint.verify():
                    return AuthChainVerdict(False, "checkpoint integrity failed", expected - 1)
                if checkpoint.checkpoint_hash != envelope.payload["checkpoint_hash"]:
                    return AuthChainVerdict(False, "checkpoint binding failed", expected - 1)
            except Exception:
                return AuthChainVerdict(False, "unsigned or malformed authenticated entry", expected - 1)
        return AuthChainVerdict(True, "authenticated", len(files))

    def checkpoint_at(self, generation):
        """Return an independently verified authenticated checkpoint, or None."""
        from recovery_auth import AuthenticatedRecoveryEnvelope
        try:
            raw = json.loads(self._path(generation).read_text(encoding="utf-8"))["envelope"]
            envelope = AuthenticatedRecoveryEnvelope(
                int(raw["version"]), str(raw["producer_id"]), str(raw["algorithm"]),
                str(raw["payload_hash"]), raw["payload"], str(raw["signature"]), str(raw.get("key_id", ""))
            )
            if int(envelope.payload["generation"]) != generation or not self.authenticator.verify(envelope):
                return None
            checkpoint = RecoveryCheckpoint.from_mapping(envelope.payload["recovery_checkpoint"])
            return checkpoint if checkpoint.verify() and checkpoint.checkpoint_hash == envelope.payload["checkpoint_hash"] else None
        except Exception:
            return None

    def entry_hash(self, generation):
        """Hash the exact canonical authenticated entry after independent verification."""
        if self.checkpoint_at(generation) is None:
            return ""
        try:
            raw = json.loads(self._path(generation).read_text(encoding="utf-8"))
            return hashlib.sha256(_canon(raw)).hexdigest()
        except Exception:
            return ""

    def verify_against(self, checkpoint_chain):
        """Require one authenticated evidence entry for every integrity-chain checkpoint."""
        own = self.verify_chain()
        base = checkpoint_chain.verify_chain()
        if not own.valid:
            return own
        if not base.valid:
            return AuthChainVerdict(False, "checkpoint chain invalid", own.generation)
        if own.generation != base.generation:
            return AuthChainVerdict(False, "authenticated generation mismatch", min(own.generation, base.generation))
        from recovery_auth import AuthenticatedRecoveryEnvelope
        for generation in range(1, base.generation + 1):
            try:
                raw = json.loads(self._path(generation).read_text(encoding="utf-8"))["envelope"]
                envelope = AuthenticatedRecoveryEnvelope(
                    int(raw["version"]), str(raw["producer_id"]), str(raw["algorithm"]),
                    str(raw["payload_hash"]), raw["payload"], str(raw["signature"]), str(raw.get("key_id", ""))
                )
                auth_cp = RecoveryCheckpoint.from_mapping(envelope.payload["recovery_checkpoint"])
                base_entry = checkpoint_chain._read_entry(generation)
                if base_entry is None or auth_cp.checkpoint_hash != base_entry.recovery_checkpoint.checkpoint_hash:
                    return AuthChainVerdict(False, "authenticated checkpoint mismatch", generation - 1)
            except Exception:
                return AuthChainVerdict(False, "authenticated checkpoint unreadable", generation - 1)
        return AuthChainVerdict(True, "authenticated and aligned", base.generation)
