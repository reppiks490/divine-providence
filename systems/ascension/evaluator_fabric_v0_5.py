from __future__ import annotations
import hashlib, json
from typing import Any, Mapping, Sequence
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

def canonical_json(v:Any)->bytes:return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha256_json(v:Any)->str:return hashlib.sha256(canonical_json(v)).hexdigest()

def _verify_sig(pubhex:str, sighex:str, payload:Mapping[str,Any])->bool:
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pubhex)).verify(bytes.fromhex(sighex),canonical_json(payload)); return True
    except (InvalidSignature,ValueError,TypeError,KeyError): return False

def verify_root_transition(old_root:Mapping[str,Any], new_root:Mapping[str,Any], signatures:Sequence[Mapping[str,Any]], trusted_version:int):
    reasons=[]
    try: oldv=int(old_root['version']); newv=int(new_root['version']); trusted=int(trusted_version)
    except (KeyError,TypeError,ValueError): return {'accepted':False,'reasons':['root_version_invalid']}
    if oldv<trusted: reasons.append('trusted_root_rollback')
    if newv<=oldv: reasons.append('root_version_not_monotonic')
    if new_root.get('previous_root_sha256')!=sha256_json(old_root): reasons.append('previous_root_digest_mismatch')
    oldkeys=old_root.get('keys',{}); newkeys=new_root.get('keys',{})
    oldmin=int(old_root.get('threshold',1)); newmin=int(new_root.get('threshold',1))
    oldvalid=set(); newvalid=set()
    for s in signatures:
        sid=s.get('signer_id'); sig=s.get('signature_hex','')
        if sid in oldkeys and _verify_sig(oldkeys[sid],sig,new_root): oldvalid.add(sid)
        if sid in newkeys and _verify_sig(newkeys[sid],sig,new_root): newvalid.add(sid)
    if len(oldvalid)<oldmin: reasons.append('old_root_threshold_not_met')
    if len(newvalid)<newmin: reasons.append('new_root_threshold_not_met')
    return {'accepted':not reasons,'reasons':sorted(set(reasons)),'old_valid_signers':sorted(oldvalid),'new_valid_signers':sorted(newvalid),'new_version':newv}

def verify_transparency_checkpoint(checkpoint:Mapping[str,Any], witness_keys:Mapping[str,str], minimum_witnesses:int, prior_checkpoint:Mapping[str,Any]|None=None):
    reasons=[]
    payload=checkpoint.get('payload',{}); sigs=checkpoint.get('signatures',[]); valid=set()
    for s in sigs:
        sid=s.get('signer_id')
        if sid in witness_keys and _verify_sig(witness_keys[sid],s.get('signature_hex',''),payload): valid.add(sid)
    if len(valid)<int(minimum_witnesses): reasons.append('witness_threshold_not_met')
    try:
        size=int(payload['tree_size'])
        if prior_checkpoint:
            p=prior_checkpoint.get('payload',{}); psize=int(p['tree_size'])
            if size<psize: reasons.append('transparency_rollback')
            if size==psize and payload.get('root_hash')!=p.get('root_hash'): reasons.append('transparency_equivocation')
            if payload.get('previous_checkpoint_sha256')!=sha256_json(p): reasons.append('checkpoint_chain_mismatch')
    except (KeyError,TypeError,ValueError): reasons.append('checkpoint_invalid')
    return {'valid':not reasons,'reasons':sorted(set(reasons)),'valid_witnesses':sorted(valid)}

def verify_delegation(delegation:Mapping[str,Any], root:Mapping[str,Any], subject:str, role:str, at_iso:str):
    reasons=[]; payload=delegation.get('payload',{}); keys=root.get('keys',{}); threshold=int(root.get('threshold',1)); valid=set()
    for s in delegation.get('signatures',[]):
        sid=s.get('signer_id')
        if sid in keys and _verify_sig(keys[sid],s.get('signature_hex',''),payload): valid.add(sid)
    if len(valid)<threshold: reasons.append('delegation_threshold_not_met')
    if payload.get('subject')!=subject or role not in payload.get('roles',[]): reasons.append('delegation_scope_mismatch')
    if not (str(payload.get('valid_from',''))<=at_iso<=str(payload.get('valid_until',''))): reasons.append('delegation_expired_or_not_yet_valid')
    return {'valid':not reasons,'reasons':sorted(set(reasons)),'valid_root_signers':sorted(valid)}
