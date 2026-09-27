from __future__ import annotations
import copy, hashlib, json
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

def canonical_json(v:Any)->bytes:return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha256_json(v:Any)->str:return hashlib.sha256(canonical_json(v)).hexdigest()
def _iso(d):
 if d.tzinfo is None:d=d.replace(tzinfo=timezone.utc)
 return d.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
def _time(s):
 d=datetime.fromisoformat(s.replace('Z','+00:00')); return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)

def create_attestation(*,signer_id,subject,manifest,artifact_bytes,collision_report,issued_at,private_key,policy_version,evidence_class):
 p={'algorithm':'Ed25519','signer_id':signer_id,'subject':subject,'issued_at':_iso(issued_at),'policy_version':policy_version,'evidence_class':evidence_class,'manifest_sha256':sha256_json(manifest),'artifact_sha256':hashlib.sha256(artifact_bytes).hexdigest(),'collision_report_sha256':sha256_json(collision_report)}
 return {'payload':p,'signature_hex':private_key.sign(canonical_json(p)).hex()}

def _verify_one(a,manifest,artifact,collision,policy,now):
 p=copy.deepcopy(dict(a.get('payload',{}))); reasons=[]; sid=p.get('signer_id'); signer=policy.get('signers',{}).get(sid)
 try:
  if int(p.get('policy_version',-1)) < int(policy.get('minimum_policy_version',policy.get('policy_version',0))): reasons.append('policy_rollback')
 except (TypeError,ValueError): reasons.append('policy_version_invalid')
 if p.get('algorithm') not in policy.get('allowed_algorithms',['Ed25519']):reasons.append('algorithm_not_allowed')
 if not signer: reasons.append('unknown_signer')
 else:
  if p.get('subject') not in signer.get('allowed_subjects',[]):reasons.append('subject_not_allowed')
  try:
   issued=_time(p.get('issued_at',''))
   if 'valid_from' in signer and issued<_time(signer['valid_from']):reasons.append('signer_outside_validity')
   if 'valid_until' in signer and issued>_time(signer['valid_until']):reasons.append('signer_outside_validity')
   if signer.get('revoked'):reasons.append('signer_revoked')
   if signer.get('compromised_at') and issued>=_time(signer['compromised_at']):reasons.append('signer_compromised')
  except Exception: reasons.append('issued_at_invalid'); issued=None
  try: Ed25519PublicKey.from_public_bytes(bytes.fromhex(signer['public_key_hex'])).verify(bytes.fromhex(a.get('signature_hex','')),canonical_json(p))
  except (InvalidSignature,ValueError,KeyError,TypeError):reasons.append('signature_invalid')
 if p.get('subject')!=manifest.get('system_id'):reasons.append('manifest_subject_mismatch')
 if p.get('manifest_sha256')!=sha256_json(manifest):reasons.append('manifest_digest_mismatch')
 if p.get('artifact_sha256')!=hashlib.sha256(artifact).hexdigest():reasons.append('artifact_digest_mismatch')
 if p.get('collision_report_sha256')!=sha256_json(collision):reasons.append('collision_report_digest_mismatch')
 try:
  issued=_time(p.get('issued_at','')); n=now if now.tzinfo else now.replace(tzinfo=timezone.utc); age=(n.astimezone(timezone.utc)-issued).total_seconds(); maxage=policy.get('evidence_max_age_seconds',{}).get(p.get('evidence_class'),policy.get('max_age_seconds',3600))
  if age < -policy.get('future_tolerance_seconds',300):reasons.append('attestation_from_future')
  if age > maxage:reasons.append('evidence_stale')
 except Exception:
  if 'issued_at_invalid' not in reasons:reasons.append('issued_at_invalid')
 return {'valid':not reasons,'reasons':sorted(set(reasons)),'signer_id':sid,'roles':[] if not signer else signer.get('roles',[]),'subject':p.get('subject')}

def verify_attestation_set(attestations:Sequence[Mapping[str,Any]],manifest,artifact_bytes,collision_report,trust_policy,now):
 results=[_verify_one(a,manifest,artifact_bytes,collision_report,trust_policy,now) for a in attestations]; reasons=sorted({r for x in results for r in x['reasons']})
 subject=manifest.get('system_id'); rule=trust_policy.get('thresholds',{}).get(subject,{'role':'root','minimum':1}); role=rule.get('role','root'); minimum=int(rule.get('minimum',1))
 unique={x['signer_id'] for x in results if x['valid'] and role in x['roles']}
 if len(unique)<minimum:reasons.append('threshold_not_met')
 required={'detector','version','collision_free','findings','boundary_gate','non_interference_gate'}
 if not required.issubset(collision_report):reasons.append('collision_report_incomplete')
 if not collision_report.get('boundary_gate',False) or not collision_report.get('non_interference_gate',False):reasons.append('collision_gate_failed')
 reasons=sorted(set(reasons)); return {'trusted':not reasons,'reasons':reasons,'valid_signers':sorted(unique),'threshold_required':minimum,'threshold_role':role,'boundary_gate':bool(collision_report.get('boundary_gate',False)),'non_interference_gate':bool(collision_report.get('non_interference_gate',False))}
