"""NEXUS artifacts -> SuperMesh-X RFC 9162 witnessed transparency log.

SuperMesh-X's ``RFC9162WitnessedCheckpointLedger`` is generic by design: leaves are opaque
bytes under a caller-chosen ``log_id``, and it enforces only append-only / rollback /
split-view invariants with a witness quorum. Recording another system's already-produced
artifact is therefore a faithful use of its declared role ("trusted time and witnessed
transparency"). A witness signature authenticates checkpoint evidence only and grants no
execution, write or trading authority. Witness keys here are ephemeral local Ed25519 keys,
not a production trust root.
"""
import json

from scripts.witnessed_transparency import (GossipReceiptStore, RFC9162WitnessedCheckpointLedger, Witness,
                                            WitnessError, WitnessRegistry, rfc9162_root)

from ._common import SYSTEMS, emit
from ._nexus_instant import build


def _canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


bundle, _ = build()
bundle_leaf = _canonical(bundle.to_dict())
baseline_leaf = (SYSTEMS / "nexus" / "contracts" / "baselines" / "sibling_contract_drift_baseline.v1.15.monorepo.json").read_bytes()

witnesses = [Witness.generate("dp-witness-a"), Witness.generate("dp-witness-b")]
registry = WitnessRegistry(threshold=2)
for w in witnesses:
    registry.add(w.witness_id, w.public_key_bytes())
ledger = RFC9162WitnessedCheckpointLedger(registry, "divine-providence/nexus-artifacts")
gossip = GossipReceiptStore(registry)  # independent verifier: re-checks signatures and consistency proofs

cp1 = ledger.checkpoint([bundle_leaf], witnesses)
cp2 = ledger.checkpoint([bundle_leaf, baseline_leaf], witnesses)
observed = gossip.observe(cp1) and gossip.observe(cp2)


def rejected(leaves) -> str | None:
    try:
        ledger.checkpoint(leaves, witnesses)
    except WitnessError as exc:
        return str(exc)
    return None


tampered = dict(bundle.to_dict(), bundle_hash="0" * 64)
history_rewrite = rejected([_canonical(tampered), baseline_leaf, b"extra"])
rollback = rejected([bundle_leaf])
emit({"connection": "nexus->supermesh-witness",
      "ok": (observed and cp1["root"] == rfc9162_root([bundle_leaf]) and cp2["tree_size"] == 2
             and cp2["witness_quorum"] == 2 and history_rewrite is not None and rollback is not None),
      "log_id": cp2["log_id"], "tree_size": cp2["tree_size"], "root": cp2["root"],
      "witness_quorum": cp2["witness_quorum"], "gossip_verified": observed,
      "nexus_bundle_hash": bundle.bundle_hash,
      "negative_controls": {"history_rewrite_rejected": history_rewrite, "rollback_rejected": rollback},
      "authority": "witness receipts authenticate checkpoint evidence only; no execution/write/trading authority"})
