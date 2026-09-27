
import pytest
import json
from scripts.witnessed_transparency import WitnessError,Witness,WitnessRegistry,WitnessedCheckpointLedger,consistency_proof,verify_consistency_proof

def pair():
 a,b=Witness.generate("a"),Witness.generate("b"); r=WitnessRegistry(2)
 for w in (a,b): r.add(w.witness_id,w.public_key_bytes())
 return a,b,r
def test_append_only_growth_proof():
 p=consistency_proof([b"a"],[b"a",b"b"]); assert verify_consistency_proof(p)
def test_mutated_proof_rejected():
 p=consistency_proof([b"a"],[b"a",b"b"]); p["new_leaves"][0]="00"*32
 with pytest.raises(WitnessError): verify_consistency_proof(p)
def test_quorum_and_duplicate_resistance():
 a,b,r=pair(); l=WitnessedCheckpointLedger(r); assert l.checkpoint([b"x"],[a,b])["witness_quorum"]==2
 with pytest.raises(WitnessError): WitnessedCheckpointLedger(r).checkpoint([b"x"],[a,a])
def test_revoked_witness_rejected():
 a,b,r=pair(); r.revoke("b")
 with pytest.raises(WitnessError): WitnessedCheckpointLedger(r).checkpoint([b"x"],[a,b])
def test_split_view_and_rollback_rejected():
 a,b,r=pair(); l=WitnessedCheckpointLedger(r); l.checkpoint([b"x"],[a,b])
 with pytest.raises(WitnessError): l.checkpoint([b"fork"],[a,b])
 with pytest.raises(WitnessError): l.checkpoint([],[a,b])
def test_growth_is_chained():
 a,b,r=pair(); l=WitnessedCheckpointLedger(r); l.checkpoint([b"x"],[a,b]); cp=l.checkpoint([b"x",b"y"],[a,b])
 assert cp["previous_tree_size"]==1 and cp["consistency_digest"]
def test_signatures_cannot_escalate_authority():
 a,b,r=pair(); r.allowed_capabilities={"observe"}
 with pytest.raises(WitnessError): WitnessedCheckpointLedger(r).checkpoint([b"x"],[a,b],claimed_capabilities={"execute"})
def test_receipts_exclude_private_material():
 a,b,r=pair(); cp=WitnessedCheckpointLedger(r).checkpoint([b"x"],[a,b])
 s=json.dumps(cp).lower(); assert "private_key" not in s and "secretref://" not in s
