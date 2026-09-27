"""Authenticated runtime evidence for SuperMesh-X v3.0."""
from __future__ import annotations
import base64, copy, hashlib, json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
try:
    from scripts.runtime_evidence_journal import EvidenceJournal
except ImportError:
    from runtime_evidence_journal import EvidenceJournal

class SignatureError(RuntimeError): pass

def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",",":"), ensure_ascii=True).encode()

def _digest(value):
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()

class Ed25519Signer:
    def __init__(self,key_id,private_key): self.key_id=str(key_id); self._key=private_key
    @classmethod
    def generate(cls,key_id): return cls(key_id,Ed25519PrivateKey.generate())
    def public_key_bytes(self):
        return self._key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    def sign(self,statement):
        st=copy.deepcopy(statement); raw=_canonical(st)
        return {"schema":1,"algorithm":"Ed25519","key_id":self.key_id,"statement":st,
                "statement_digest":"sha256:"+hashlib.sha256(raw).hexdigest(),
                "signature":base64.b64encode(self._key.sign(raw)).decode("ascii")}

class TrustStore:
    def __init__(self): self._keys={}; self._revoked=set()
    def add(self,key_id,public_key_bytes):
        kid=str(key_id)
        if kid in self._revoked: raise SignatureError("revoked key id cannot be reactivated")
        raw=bytes(public_key_bytes)
        if kid in self._keys and self._keys[kid]!=raw: raise SignatureError("key id collision")
        self._keys[kid]=raw
    def revoke(self,key_id):
        kid=str(key_id)
        if kid not in self._keys: raise SignatureError("unknown key")
        self._revoked.add(kid)
    def verify(self,envelope):
        e=copy.deepcopy(envelope)
        if e.get("schema")!=1 or e.get("algorithm")!="Ed25519": raise SignatureError("unsupported signature envelope")
        kid=str(e.get("key_id",""))
        if kid not in self._keys or kid in self._revoked: raise SignatureError("untrusted signing key")
        raw=_canonical(e.get("statement"))
        if e.get("statement_digest") != "sha256:"+hashlib.sha256(raw).hexdigest(): raise SignatureError("statement digest mismatch")
        try:
            sig=base64.b64decode(e.get("signature",""),validate=True)
            Ed25519PublicKey.from_public_bytes(self._keys[kid]).verify(sig,raw)
        except Exception as exc: raise SignatureError("signature verification failed") from exc
        return {"schema":1,"key_id":kid,"statement_digest":e["statement_digest"]}

class SignedEvidenceJournal:
    def __init__(self,run_id,trust_store,allowed_capabilities=()):
        self.run_id=str(run_id); self.trust=trust_store; self.allowed=set(allowed_capabilities)
        self.journal=EvidenceJournal(self.run_id); self._seen=set(); self._max_fence=-1
    def admit(self,envelope):
        verified=self.trust.verify(envelope)
        st=copy.deepcopy(envelope["statement"])
        if st.get("run_id")!=self.run_id: raise SignatureError("run identity mismatch")
        try: fence=int(st["fencing_token"])
        except Exception as exc: raise SignatureError("invalid fencing token") from exc
        if fence < self._max_fence: raise SignatureError("stale fencing token")
        identity=(verified["key_id"],verified["statement_digest"])
        if identity in self._seen: raise SignatureError("signed evidence replay")
        caps=set(st.get("payload",{}).get("capabilities",[]))
        if not caps.issubset(self.allowed): raise SignatureError("signed claim exceeds existing authority")
        self._max_fence=max(self._max_fence,fence); self._seen.add(identity)
        receipt={"signer_key_id":verified["key_id"],"statement_digest":verified["statement_digest"],
                 "fencing_token":fence,"payload":st.get("payload",{})}
        return self.journal.append("signed:"+str(st.get("kind","event")),receipt)
    def verify(self): return self.journal.verify()
