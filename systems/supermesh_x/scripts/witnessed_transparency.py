"""Witnessed transparency contracts; signatures authenticate evidence, never authority."""
import base64,hashlib,json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey,Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
class WitnessError(RuntimeError):pass
def _h(x):return hashlib.sha256(x).hexdigest()
def _lh(x):return _h(b"\x00"+x)
def _root(leaves):
 n=[bytes.fromhex(_lh(x)) for x in leaves]
 if not n:return _h(b"")
 while len(n)>1:
  n=[hashlib.sha256(b"\x01"+n[i]+(n[i+1] if i+1<len(n) else n[i])).digest() for i in range(0,len(n),2)]
 return n[0].hex()
def consistency_proof(old,new):
 if len(old)>len(new) or list(new[:len(old)])!=list(old):raise WitnessError("not append-only")
 return {"schema":1,"old_size":len(old),"new_size":len(new),"old_root":_root(old),"new_root":_root(new),"old_leaves":[x.hex() for x in old],"new_leaves":[x.hex() for x in new]}
def verify_consistency_proof(p):
 try: old=[bytes.fromhex(x) for x in p["old_leaves"]];new=[bytes.fromhex(x) for x in p["new_leaves"]]
 except Exception as e:raise WitnessError("malformed proof") from e
 if len(old)!=p["old_size"] or len(new)!=p["new_size"] or new[:len(old)]!=old or _root(old)!=p["old_root"] or _root(new)!=p["new_root"]:raise WitnessError("consistency failure")
 return True
def _canon(x):return json.dumps(x,sort_keys=True,separators=(",",":")).encode()
class Witness:
 def __init__(self,wid,key):self.witness_id=str(wid);self._key=key
 @classmethod
 def generate(cls,wid):return cls(wid,Ed25519PrivateKey.generate())
 def public_key_bytes(self):return self._key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
 def sign(self,s):return base64.b64encode(self._key.sign(_canon(s))).decode()
class WitnessRegistry:
 def __init__(self,threshold,allowed_capabilities=()):
  self.threshold=int(threshold);self.allowed_capabilities=set(allowed_capabilities);self.keys={};self.revoked=set()
  if self.threshold<1:raise WitnessError("invalid threshold")
 def add(self,wid,key):
  wid=str(wid);key=bytes(key)
  if wid in self.keys and self.keys[wid]!=key:raise WitnessError("key collision")
  self.keys[wid]=key
 def revoke(self,wid):self.revoked.add(str(wid))
 def verify(self,wid,s,sig):
  wid=str(wid)
  if wid in self.revoked or wid not in self.keys:raise WitnessError("unknown/revoked witness")
  try:Ed25519PublicKey.from_public_bytes(self.keys[wid]).verify(base64.b64decode(sig),_canon(s))
  except Exception as e:raise WitnessError("invalid signature") from e
class WitnessedCheckpointLedger:
 def __init__(self,registry):self.registry=registry;self.last=None
 def checkpoint(self,leaves,witnesses,claimed_capabilities=()):
  if hasattr(self.registry,"assert_current_policy_fresh"):self.registry.assert_current_policy_fresh()
  if not set(claimed_capabilities).issubset(self.registry.allowed_capabilities):raise WitnessError("capability escalation")
  root,size=_root(leaves),len(leaves)
  if self.last and size<self.last["tree_size"]:raise WitnessError("rollback")
  if self.last and size==self.last["tree_size"] and root!=self.last["root"]:raise WitnessError("split view")
  proof=None
  if self.last:
   proof=consistency_proof([bytes.fromhex(x) for x in self.last["_leaves"]],leaves);verify_consistency_proof(proof)
  statement={"schema":1,"tree_size":size,"root":root,"previous_tree_size":self.last["tree_size"] if self.last else 0,"previous_root":self.last["root"] if self.last else None}
  receipts=[];seen=set()
  for w in witnesses:
   if w.witness_id in seen:continue
   sig=w.sign(statement);self.registry.verify(w.witness_id,statement,sig);seen.add(w.witness_id);receipts.append({"witness_id":w.witness_id,"signature":sig})
  if len(receipts)<self.registry.threshold:raise WitnessError("quorum not met")
  out={**statement,"witness_quorum":len(receipts),"receipts":receipts,"consistency_digest":_h(_canon(proof)) if proof else None}
  self.last={**out,"_leaves":[x.hex() for x in leaves]}
  return out


# --- v3.3 additive RFC 9162 compatibility path ---
def _rfc9162_mth(leaves):
    leaves = list(leaves)
    n = len(leaves)
    if n == 0:
        return hashlib.sha256(b"").digest()
    if n == 1:
        return hashlib.sha256(b"\x00" + leaves[0]).digest()
    k = 1 << ((n - 1).bit_length() - 1)
    left = _rfc9162_mth(leaves[:k])
    right = _rfc9162_mth(leaves[k:])
    return hashlib.sha256(b"\x01" + left + right).digest()

def rfc9162_root(leaves):
    """RFC 9162 Merkle Tree Hash, returned as lowercase hex."""
    return _rfc9162_mth(leaves).hex()

def _rfc9162_subproof(m, leaves, complete):
    n = len(leaves)
    if not (0 < m <= n):
        raise WitnessError("invalid consistency proof range")
    if m == n:
        return [] if complete else [_rfc9162_mth(leaves)]
    k = 1 << ((n - 1).bit_length() - 1)
    if m <= k:
        return _rfc9162_subproof(m, leaves[:k], complete) + [_rfc9162_mth(leaves[k:])]
    return _rfc9162_subproof(m - k, leaves[k:], False) + [_rfc9162_mth(leaves[:k])]

def _rfc9162_proof_for_size(old_size, new_leaves, old_root=None):
    n = len(new_leaves)
    if old_size < 0 or old_size > n:
        raise WitnessError("invalid consistency proof range")
    new_root = rfc9162_root(new_leaves)
    if old_size == 0:
        return {
            "schema": 2, "tree_algorithm": "RFC9162_SHA256",
            "old_size": 0, "new_size": n,
            "old_root": rfc9162_root([]) if old_root is None else old_root,
            "new_root": new_root, "path": [],
        }
    if old_size == n:
        current = new_root
        if old_root is not None and old_root != current:
            raise WitnessError("same-size root mismatch")
        return {
            "schema": 2, "tree_algorithm": "RFC9162_SHA256",
            "old_size": n, "new_size": n,
            "old_root": current if old_root is None else old_root,
            "new_root": current, "path": [],
        }
    path = [x.hex() for x in _rfc9162_subproof(old_size, list(new_leaves), True)]
    return {
        "schema": 2, "tree_algorithm": "RFC9162_SHA256",
        "old_size": old_size, "new_size": n,
        "old_root": rfc9162_root(list(new_leaves)[:old_size]) if old_root is None else old_root,
        "new_root": new_root, "path": path,
    }

def rfc9162_consistency_proof(old, new):
    """Generate a compact RFC 9162 consistency proof without embedding leaves."""
    old, new = list(old), list(new)
    if len(old) > len(new) or new[:len(old)] != old:
        raise WitnessError("not append-only")
    return _rfc9162_proof_for_size(len(old), new, rfc9162_root(old))

def _node_hash(left, right):
    return hashlib.sha256(b"\x01" + left + right).digest()

def verify_rfc9162_consistency_proof(proof):
    """Verify RFC 9162 §2.1.4.2 using only roots, sizes, and compact path."""
    try:
        first = int(proof["old_size"])
        second = int(proof["new_size"])
        first_hash = bytes.fromhex(proof["old_root"])
        second_hash = bytes.fromhex(proof["new_root"])
        path = [bytes.fromhex(x) for x in proof["path"]]
    except Exception as e:
        raise WitnessError("malformed RFC9162 proof") from e

    if first < 0 or second < 0 or first > second:
        raise WitnessError("invalid tree sizes")
    if first == 0:
        if proof["old_root"] != rfc9162_root([]):
            raise WitnessError("invalid empty-tree root")
        return True
    if first == second:
        if path or first_hash != second_hash:
            raise WitnessError("same-size inconsistency")
        return True
    if not path:
        raise WitnessError("empty consistency path")

    cp = list(path)
    if first & (first - 1) == 0:
        cp.insert(0, first_hash)

    fn = first - 1
    sn = second - 1
    if fn & 1:
        while fn & 1:
            fn >>= 1
            sn >>= 1

    fr = sr = cp[0]
    for c in cp[1:]:
        if sn == 0:
            raise WitnessError("consistency path too long")
        if (fn & 1) or fn == sn:
            fr = _node_hash(c, fr)
            sr = _node_hash(c, sr)
            if not (fn & 1):
                while fn != 0 and not (fn & 1):
                    fn >>= 1
                    sn >>= 1
        else:
            sr = _node_hash(sr, c)
        fn >>= 1
        sn >>= 1

    if fr != first_hash or sr != second_hash or sn != 0:
        raise WitnessError("RFC9162 consistency verification failed")
    return True

def _rfc_signed_statement(cp):
    statement = {
        "schema": cp["schema"],
        "log_id": cp["log_id"],
        "tree_algorithm": cp["tree_algorithm"],
        "tree_size": cp["tree_size"],
        "root": cp["root"],
        "previous_tree_size": cp["previous_tree_size"],
        "previous_root": cp["previous_root"],
        "consistency_digest": cp["consistency_digest"],
    }
    # v3.4 policy-bound receipts are additive. Legacy v3.3 receipts omit both.
    if "policy_epoch" in cp or "policy_digest" in cp:
        if "policy_epoch" not in cp or "policy_digest" not in cp:
            raise WitnessError("incomplete witness policy binding")
        statement["policy_epoch"] = cp["policy_epoch"]
        statement["policy_digest"] = cp["policy_digest"]
    return statement

class RFC9162WitnessedCheckpointLedger:
    """Additive RFC 9162 ledger. Legacy WitnessedCheckpointLedger remains unchanged."""
    def __init__(self, registry, log_id):
        self.registry = registry
        self.log_id = str(log_id)
        self.last = None

    def checkpoint(self, leaves, witnesses, claimed_capabilities=()):
        if hasattr(self.registry, "assert_current_policy_fresh"):
            self.registry.assert_current_policy_fresh()
        leaves = list(leaves)
        if not set(claimed_capabilities).issubset(self.registry.allowed_capabilities):
            raise WitnessError("capability escalation")
        size = len(leaves)
        root = rfc9162_root(leaves)
        previous_size = self.last["tree_size"] if self.last else 0
        previous_root = self.last["root"] if self.last else None
        if self.last and size < previous_size:
            raise WitnessError("rollback")
        if self.last and size == previous_size and root != previous_root:
            raise WitnessError("split view")

        proof = None
        path = []
        if self.last and size > previous_size:
            proof = _rfc9162_proof_for_size(previous_size, leaves, previous_root)
            verify_rfc9162_consistency_proof(proof)
            path = proof["path"]
        elif self.last and size == previous_size:
            proof = _rfc9162_proof_for_size(previous_size, leaves, previous_root)
            verify_rfc9162_consistency_proof(proof)

        consistency_digest = _h(_canon(proof)) if proof else None
        statement = {
            "schema": 3,
            "log_id": self.log_id,
            "tree_algorithm": "RFC9162_SHA256",
            "tree_size": size,
            "root": root,
            "previous_tree_size": previous_size,
            "previous_root": previous_root,
            "consistency_digest": consistency_digest,
        }
        policy_epoch = getattr(self.registry, "policy_epoch", None)
        policy_digest = getattr(self.registry, "policy_digest", None)
        if (policy_epoch is None) != (policy_digest is None):
            raise WitnessError("incomplete witness policy registry")
        if policy_epoch is not None:
            statement["policy_epoch"] = int(policy_epoch)
            statement["policy_digest"] = str(policy_digest)
        receipts, seen = [], set()
        for w in witnesses:
            if w.witness_id in seen:
                continue
            sig = w.sign(statement)
            self.registry.verify(w.witness_id, statement, sig)
            seen.add(w.witness_id)
            receipts.append({"witness_id": w.witness_id, "signature": sig})
        if len(receipts) < self.registry.threshold:
            raise WitnessError("quorum not met")
        out = {
            **statement,
            "consistency_path": path,
            "witness_quorum": len(receipts),
            "receipts": receipts,
        }
        self.last = out
        return dict(out)

    def save_snapshot(self, path):
        """Atomically persist public witness state; no private keys are serialized."""
        import os
        from pathlib import Path
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema": 1, "log_id": self.log_id, "last": self.last}
        envelope = {"payload": payload, "sha256": _h(_canon(payload))}
        data = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
        tmp = target.with_name(target.name + ".tmp")
        try:
            with tmp.open("w") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, target)
        finally:
            if tmp.exists():
                tmp.unlink()

    def checkpoint_and_persist(self, leaves, witnesses, path, claimed_capabilities=()):
        """Return a cosigned checkpoint only after its new state is durably persisted."""
        previous = self.last
        try:
            out = self.checkpoint(leaves, witnesses, claimed_capabilities)
            self.save_snapshot(path)
            return out
        except Exception as e:
            self.last = previous
            if isinstance(e, WitnessError):
                raise
            raise WitnessError("checkpoint persistence failed") from e

    @classmethod
    def load_snapshot(cls, path, registry):
        from pathlib import Path
        try:
            envelope = json.loads(Path(path).read_text())
            payload = envelope["payload"]
        except Exception as e:
            raise WitnessError("malformed witness snapshot") from e
        if envelope.get("sha256") != _h(_canon(payload)):
            raise WitnessError("witness snapshot integrity failure")
        obj = cls(registry, payload["log_id"])
        last = payload.get("last")
        if last is not None:
            # Revalidate persisted compact evidence, not only the envelope checksum.
            # This prevents a re-checksummed snapshot from carrying a path that no
            # longer matches the signed consistency digest.
            if last.get("consistency_digest") is not None:
                proof = {
                    "schema": 2,
                    "tree_algorithm": "RFC9162_SHA256",
                    "old_size": int(last["previous_tree_size"]),
                    "new_size": int(last["tree_size"]),
                    "old_root": last["previous_root"],
                    "new_root": last["root"],
                    "path": list(last.get("consistency_path", [])),
                }
                verify_rfc9162_consistency_proof(proof)
                if last["consistency_digest"] != _h(_canon(proof)):
                    raise WitnessError("snapshot consistency digest mismatch")
            statement = _rfc_signed_statement(last)
            seen = set()
            for receipt in last.get("receipts", []):
                wid = receipt["witness_id"]
                if wid in seen:
                    continue
                registry.verify(wid, statement, receipt["signature"])
                seen.add(wid)
            required = registry.threshold_for_statement(statement) if hasattr(registry, "threshold_for_statement") else registry.threshold
            if len(seen) < required:
                raise WitnessError("snapshot witness quorum invalid")
            if last.get("witness_quorum") != len(last.get("receipts", [])):
                raise WitnessError("snapshot quorum metadata mismatch")
            obj.last = last
        return obj

class GossipReceiptStore:
    """Public checkpoint gossip cache.

    With a registry, witness signatures and compact consistency evidence are
    authenticated before observation. Without one, this class is intentionally
    limited to monotonicity/equivocation detection and grants no trust.
    """
    def __init__(self, registry=None):
        self.registry = registry
        self._by_log = {}

    def _authenticate(self, checkpoint):
        if self.registry is None:
            return True
        try:
            statement = _rfc_signed_statement(checkpoint)
            receipts = checkpoint["receipts"]
        except Exception as e:
            raise WitnessError("malformed authenticated gossip receipt") from e
        seen = set()
        for receipt in receipts:
            wid = receipt["witness_id"]
            if wid in seen:
                continue
            self.registry.verify(wid, statement, receipt["signature"])
            seen.add(wid)
        required = self.registry.threshold_for_statement(statement) if hasattr(self.registry, "threshold_for_statement") else self.registry.threshold
        if len(seen) < required:
            raise WitnessError("gossip witness quorum invalid")
        if checkpoint.get("witness_quorum") != len(receipts):
            raise WitnessError("gossip quorum metadata mismatch")
        first = int(checkpoint["previous_tree_size"])
        second = int(checkpoint["tree_size"])
        if first > 0 and second > first:
            proof = {
                "schema": 2,
                "tree_algorithm": "RFC9162_SHA256",
                "old_size": first,
                "new_size": second,
                "old_root": checkpoint["previous_root"],
                "new_root": checkpoint["root"],
                "path": list(checkpoint.get("consistency_path", [])),
            }
            verify_rfc9162_consistency_proof(proof)
            if checkpoint.get("consistency_digest") != _h(_canon(proof)):
                raise WitnessError("gossip consistency digest mismatch")
        elif first == second and first > 0:
            if checkpoint["previous_root"] != checkpoint["root"] or checkpoint.get("consistency_path"):
                raise WitnessError("same-size gossip inconsistency")
        return True

    def observe(self, checkpoint):
        self._authenticate(checkpoint)
        try:
            log_id = str(checkpoint["log_id"])
            size = int(checkpoint["tree_size"])
            root = str(checkpoint["root"])
        except Exception as e:
            raise WitnessError("malformed gossip receipt") from e
        if size < 0 or not root:
            raise WitnessError("malformed gossip receipt")
        log = self._by_log.setdefault(log_id, {})
        if size in log and log[size]["root"] != root:
            raise WitnessError("gossip equivocation detected")
        if log and size < max(log):
            raise WitnessError("gossip rollback detected")
        log[size] = dict(checkpoint)
        return True

    def latest(self, log_id):
        log = self._by_log.get(str(log_id), {})
        if not log:
            return None
        return dict(log[max(log)])

    def export(self):
        out = []
        for log_id in sorted(self._by_log):
            for size in sorted(self._by_log[log_id]):
                out.append(dict(self._by_log[log_id][size]))
        return out

    def merge(self, receipts):
        # Accept stale duplicates during partition recovery, but never equivocation.
        for cp in sorted((dict(x) for x in receipts), key=lambda x: (str(x["log_id"]), int(x["tree_size"]))):
            self._authenticate(cp)
            log_id, size, root = str(cp["log_id"]), int(cp["tree_size"]), str(cp["root"])
            log = self._by_log.setdefault(log_id, {})
            if size in log:
                if log[size]["root"] != root:
                    raise WitnessError("gossip equivocation detected")
                continue
            latest = max(log) if log else -1
            if size < latest:
                continue
            log[size] = cp
        return True
