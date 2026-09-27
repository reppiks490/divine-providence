import base64, copy, hashlib, json, unittest
import sibling_manifest_conformance_v0_1 as c

SHA=lambda b: hashlib.sha256(b).hexdigest()

def manifest():
    return {
      "system_id":"PROMETHEUS",
      "owned_domains":["research_orchestration"],
      "mutation_rights":[],
      "interfaces":[{"name":"research-provenance","version":"0.5","required_inputs":["plugin_evidence"],"emitted_outputs":["research_manifest"],"assumptions":["external_verifier_receipt"],"invariants":["research_only"]}],
      "requires":["external_attestation_receipt"],"forbids":["production_authority"],
      "shared_state":[],"coordination_contracts":[]
    }

def attestation():
    subj="a"*64
    return {
      "plugin_evidence_id":"plugin-evidence:"+subj,
      "subject_sha256":subj,
      "predicate_type":"https://example.invalid/prometheus/plugin-execution/v1",
      "envelope_ref":"file://attestation.dsse",
      "envelope_sha256":"b"*64,
      "verification_material_sha256":"c"*64,
      "signer_identity":"prometheus-authority@example.invalid",
      "attestation_format":"DSSE",
      "artifact_id":"external-attestation:"+"d"*64,
    }

def receipt():
    return {
      "attestation_id":"external-attestation:"+"d"*64,
      "verifier_id":"external-verifier-v1",
      "trusted_root_id":"prometheus-root-v1",
      "verification_policy_id":"require-verified-v1",
      "checks":[["signature",True],["subject_digest",True],["signer_identity",True],["trusted_root",True]],
      "external_verification_ref":"file://verification-receipt.json"
    }

def full_export(with_bytes=True):
    raw=b"PROMETHEUS-RUNTIME-ARTIFACT"
    x={
      "export_version":"0.1",
      "sibling_id":"PROMETHEUS",
      "manifest":manifest(),
      "artifact":{"sha256":SHA(raw),"content_ref":"file://prometheus-runtime.bin"},
      "authority":{"owner_system":"PROMETHEUS","attestation":attestation(),"verification_receipt":receipt()},
      "adapter_v0_4_evidence":{}
    }
    tp={"required":True,"hash_algorithm":"SHA-256","witness_algorithm":"Ed25519","log_id":"prometheus-log-v1","trusted_checkpoint":{"tree_size":4,"root_hash":"e"*64},"witness_keys":{"w1":"1"*64,"w2":"2"*64},"minimum_witnesses":2,"max_witness_age_seconds":300,"future_tolerance_seconds":60}
    policy={"policy_version":1,"minimum_policy_version":1,"allowed_algorithms":["Ed25519"],"max_age_seconds":3600,"signers":{"prometheus-key-1":{"public_key_hex":"3"*64,"allowed_subjects":["PROMETHEUS"],"roles":["root"]}},"thresholds":{"PROMETHEUS":{"role":"root","minimum":1}},"transparency_policy":tp}
    prior={"detector":"Collision Detector","version":"0.2.1","collision_free":True,"findings":[],"boundary_gate":True,"non_interference_gate":True}
    payload={"algorithm":"Ed25519","signer_id":"prometheus-key-1","subject":"PROMETHEUS","issued_at":"2026-09-25T23:59:00Z","policy_version":1,"evidence_class":"manifest","manifest_sha256":"4"*64,"artifact_sha256":SHA(raw),"collision_report_sha256":"5"*64}
    signed_attestation={"payload":payload,"signature_hex":"6"*128}
    witness=lambda wid,key: {"payload":{"algorithm":"Ed25519","witness_id":wid,"log_id":"prometheus-log-v1","tree_size":5,"root_hash":"f"*64,"observed_at":"2026-09-25T23:59:10Z"},"signature_hex":key*128}
    transparency={"inclusion":{"leaf_index":4,"tree_size":5,"root_hash":"f"*64,"path":[bytes.fromhex("7"*64)]},"transition":{"first_size":4,"first_root_hash":"e"*64,"second_size":5,"second_root_hash":"f"*64,"consistency_path":[bytes.fromhex("8"*64)],"witness_observations":[witness("w1","9"),witness("w2","a")]}}
    dep={"trust":"b189d3c21516ee62ee15da764f9bbedd0c036d180a4cb316d81c2426717d238e","inclusion":"8c40d16061bbc436cf78d3029f6b4d04b507dad8779e3dba74fd6ce51746de4b","transition":"eb8b4ad9990f8b57530aa88415827a762c6b1ff136996a33fe158ea8a72c33b6","collision":"fda90e02b3774219d0b52640e58f35510f5834c1065a2729cb563f1b303f5abb"}
    tp_sha=hashlib.sha256(json.dumps(tp,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    backend={"adapter":"manifest-trust-collision-adapter-v0.4","trust":"evaluator-fabric-attestation-v0.4","inclusion":"evaluator-fabric-inclusion-v0.8-strict-rfc9162","transition":"evaluator-fabric-transition-v0.7-compact-witness","transparency":"evaluator-fabric-transparency-v0.8-strict-inclusion+v0.7-compact-witness","collision":"collision-detector-v0.3","inclusion_schema":"rfc9162-index-bound-hash-path-v0.8","hash_algorithm":"SHA-256","witness_algorithm":"Ed25519","backend_artifact_sha256":dep,"transparency_policy_sha256":tp_sha}
    x["adapter_v0_4_evidence"]={"prior_collision_report":prior,"trust_policy":policy,"attestations":[signed_attestation],"transparency_evidence":transparency,"backend_contract":backend}
    if with_bytes: x["artifact"]["content_b64"]=base64.b64encode(raw).decode()
    return x

class TestConformance(unittest.TestCase):
  def test_full_export_is_adapter_ready_unverified(self):
    r=c.validate_export(full_export()); self.assertTrue(r["conformant"]); self.assertTrue(r["ready_for_adapter_v0_4"]); self.assertFalse(r["authenticated"]); self.assertEqual(r["status"],"ADAPTER_READY_UNVERIFIED")
  def test_descriptor_only_is_structural_not_adapter_ready(self):
    r=c.validate_export(full_export(False)); self.assertTrue(r["conformant"]); self.assertFalse(r["ready_for_adapter_v0_4"]); self.assertEqual(r["status"],"STRUCTURALLY_CONFORMANT")
  def test_manifest_missing_collision_field_rejects(self):
    x=full_export(); del x["manifest"]["owned_domains"]; self.assertFalse(c.validate_export(x)["conformant"])
  def test_system_identity_must_match(self):
    x=full_export(); x["manifest"]["system_id"]="VECTOR"; self.assertIn("manifest_system_id_mismatch",c.validate_export(x)["reasons"])
  def test_artifact_digest_shape_rejects(self):
    x=full_export(); x["artifact"]["sha256"]="bad"; self.assertFalse(c.validate_export(x)["conformant"])
  def test_artifact_content_digest_mismatch_rejects(self):
    x=full_export(); x["artifact"]["content_b64"]=base64.b64encode(b"tamper").decode(); self.assertIn("artifact_content_digest_mismatch",c.validate_export(x)["reasons"])
  def test_attestation_subject_binding(self):
    x=full_export(); x["authority"]["attestation"]["subject_sha256"]="f"*64; self.assertIn("attestation_subject_digest_mismatch",c.validate_export(x)["reasons"])
  def test_attestation_evidence_id_binding(self):
    x=full_export(); x["authority"]["attestation"]["plugin_evidence_id"]="plugin-evidence:"+"0"*64; self.assertIn("attestation_plugin_evidence_binding_mismatch",c.validate_export(x)["reasons"])
  def test_receipt_missing_mandatory_check_rejects(self):
    x=full_export(); x["authority"]["verification_receipt"]["checks"]=x["authority"]["verification_receipt"]["checks"][:-1]; self.assertIn("verification_receipt_missing_check:trusted_root",c.validate_export(x)["reasons"])
  def test_receipt_false_check_rejects(self):
    x=full_export(); x["authority"]["verification_receipt"]["checks"][0][1]=False; self.assertIn("verification_receipt_failed_check:signature",c.validate_export(x)["reasons"])
  def test_receipt_duplicate_check_rejects(self):
    x=full_export(); x["authority"]["verification_receipt"]["checks"].append(["signature",True]); self.assertIn("verification_receipt_duplicate_check:signature",c.validate_export(x)["reasons"])
  def test_receipt_attestation_id_binding(self):
    x=full_export(); x["authority"]["verification_receipt"]["attestation_id"]="external-attestation:"+"0"*64; self.assertIn("receipt_attestation_id_mismatch",c.validate_export(x)["reasons"])
  def test_empty_signer_rejects(self):
    x=full_export(); x["authority"]["attestation"]["signer_identity"]=""; self.assertFalse(c.validate_export(x)["conformant"])
  def test_adapter_evidence_missing_is_structural_only(self):
    x=full_export(); del x["adapter_v0_4_evidence"]; r=c.validate_export(x); self.assertTrue(r["conformant"]); self.assertFalse(r["ready_for_adapter_v0_4"])
  def test_backend_contract_must_target_v04_chain(self):
    x=full_export(); x["adapter_v0_4_evidence"]["backend_contract"]["inclusion"]="evaluator-fabric-inclusion-v0.6"; self.assertIn("adapter_backend_mismatch:inclusion",c.validate_export(x)["reasons"])
  def test_adapter_evidence_requires_transparency_parts(self):
    x=full_export(); del x["adapter_v0_4_evidence"]["transparency_evidence"]["inclusion"]; self.assertIn("adapter_transparency_evidence_incomplete",c.validate_export(x)["reasons"])
  def test_adapter_attestations_must_be_nonempty_list(self):
    x=full_export(); x["adapter_v0_4_evidence"]["attestations"]=[]; self.assertIn("adapter_attestations_missing",c.validate_export(x)["reasons"])
  def test_prior_collision_gate_shape(self):
    x=full_export(); del x["adapter_v0_4_evidence"]["prior_collision_report"]["boundary_gate"]; self.assertIn("adapter_prior_collision_report_incomplete",c.validate_export(x)["reasons"])
  def test_unknown_top_level_field_rejects(self):
    x=full_export(); x["surprise_security_field"]=True; self.assertIn("unrecognized_top_level_field:surprise_security_field",c.validate_export(x)["reasons"])
  def test_extension_container_is_allowed(self):
    x=full_export(); x["extensions"]={"prometheus":{"lineage_report_id":"provenance-lineage:abc"}}; self.assertTrue(c.validate_export(x)["conformant"])
  def test_secret_field_names_reject(self):
    x=full_export(); x["extensions"]={"private_key":"secret"}; self.assertIn("forbidden_secret_field:private_key",c.validate_export(x)["reasons"])
  def test_input_immutability(self):
    x=full_export(); before=copy.deepcopy(x); c.validate_export(x); self.assertEqual(x,before)
  def test_handoff_checklist_deterministic(self):
    a=c.build_handoff_checklist("PROMETHEUS"); b=c.build_handoff_checklist("PROMETHEUS"); self.assertEqual(a,b); self.assertEqual(a["sibling_id"],"PROMETHEUS"); self.assertFalse(a["grants_authority"])
  def test_prometheus_declared_profile_is_not_runtime_evidence(self):
    p=c.prometheus_v0_5_declared_profile(); self.assertEqual(p["evidence_class"],"DECLARED_CONTRACT"); self.assertFalse(p["is_runtime_manifest"]); self.assertIn("subject_sha256",p["external_attestation_required_fields"])
  def test_status_never_claims_authenticated(self):
    r=c.validate_export(full_export()); self.assertFalse(r["authenticated"]); self.assertNotIn("AUTHENTICATED",r["status"])

  def test_prior_collision_requires_full_v04_shape(self):
    x=full_export(); x["adapter_v0_4_evidence"]["prior_collision_report"]={"boundary_gate":True,"non_interference_gate":True}
    r=c.validate_export(x); self.assertFalse(r["ready_for_adapter_v0_4"]); self.assertIn("adapter_prior_collision_report_incomplete",r["reasons"])

  def test_transparency_policy_requires_full_v04_shape(self):
    x=full_export(); x["adapter_v0_4_evidence"]["trust_policy"]["transparency_policy"]={"required":True}
    r=c.validate_export(x); self.assertFalse(r["ready_for_adapter_v0_4"]); self.assertIn("adapter_transparency_policy_incomplete",r["reasons"])

  def test_backend_contract_requires_full_v04_surface(self):
    x=full_export(); del x["adapter_v0_4_evidence"]["backend_contract"]["transparency"]
    r=c.validate_export(x); self.assertFalse(r["ready_for_adapter_v0_4"]); self.assertIn("adapter_backend_contract_incomplete",r["reasons"])

  def test_adapter_attestation_set_requires_signed_payload_shape(self):
    x=full_export(); x["adapter_v0_4_evidence"]["attestations"]=[{"signer_id":"root"}]
    r=c.validate_export(x); self.assertFalse(r["ready_for_adapter_v0_4"]); self.assertIn("adapter_attestation_shape_invalid",r["reasons"])

  def test_backend_artifact_hash_substitution_blocks_readiness(self):
    x=full_export(); x["adapter_v0_4_evidence"]["backend_contract"]["backend_artifact_sha256"]["inclusion"]="0"*64
    r=c.validate_export(x); self.assertFalse(r["ready_for_adapter_v0_4"]); self.assertIn("adapter_backend_artifact_digest_mismatch:inclusion",r["reasons"])

  def test_transparency_policy_digest_must_bind_contract(self):
    x=full_export(); x["adapter_v0_4_evidence"]["backend_contract"]["transparency_policy_sha256"]="0"*64
    r=c.validate_export(x); self.assertFalse(r["ready_for_adapter_v0_4"]); self.assertIn("adapter_transparency_policy_digest_mismatch",r["reasons"])

  def test_transparency_evidence_requires_v08_v07_shape(self):
    x=full_export(); del x["adapter_v0_4_evidence"]["transparency_evidence"]["transition"]["witness_observations"]
    r=c.validate_export(x); self.assertFalse(r["ready_for_adapter_v0_4"]); self.assertIn("adapter_transition_evidence_incomplete",r["reasons"])

if __name__=='__main__': unittest.main()
