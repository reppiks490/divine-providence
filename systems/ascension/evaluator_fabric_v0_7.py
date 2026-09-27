from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def canonical_json(v: Any) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()

def _h(x: bytes) -> bytes: return hashlib.sha256(x).digest()
def _node(a: bytes, b: bytes) -> bytes: return _h(b'\x01' + a + b)
def _empty_root() -> bytes: return _h(b'')

def _hash32(v: Any) -> bytes:
    if isinstance(v, bytes):
        b=v
    elif isinstance(v, bytearray):
        b=bytes(v)
    elif isinstance(v, str):
        b=bytes.fromhex(v)
    else:
        raise TypeError('hash must be bytes or hex string')
    if len(b) != 32:
        raise ValueError('hash must be 32 bytes')
    return b

def _is_power_of_two(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0

def verify_compact_consistency(first_size: int, second_size: int, first_root: Any, second_root: Any, consistency_path: Sequence[Any]):
    """Verify an RFC 9162-style compact Merkle consistency proof.

    RFC 9162 specifies the core algorithm for 0 < first_size < second_size.
    This reference also handles equal sizes as a strict local extension:
    roots must match and the proof must be empty.
    """
    reasons=[]
    try:
        first=int(first_size); second=int(second_size)
        fr_expected=_hash32(first_root); sr_expected=_hash32(second_root)
        path=[_hash32(x) for x in consistency_path]
    except (TypeError, ValueError, OverflowError):
        return {'valid':False,'reasons':['consistency_input_invalid']}

    if first <= 0:
        reasons.append('first_size_invalid')
    if second <= 0:
        reasons.append('second_size_invalid')
    if first > second:
        reasons.append('tree_size_rollback')
    if reasons:
        return {'valid':False,'reasons':sorted(set(reasons))}

    if first == second:
        if path: reasons.append('consistency_path_nonempty_equal_size')
        if fr_expected != sr_expected: reasons.append('same_size_root_mismatch')
        return {'valid':not reasons,'reasons':sorted(set(reasons))}

    if not path:
        return {'valid':False,'reasons':['consistency_path_empty']}

    work=list(path)
    if _is_power_of_two(first):
        work.insert(0, fr_expected)

    fn=first-1; sn=second-1
    if fn & 1:
        while fn & 1:
            fn >>= 1; sn >>= 1

    fr=work[0]; sr=work[0]
    for c in work[1:]:
        if sn == 0:
            reasons.append('consistency_path_too_long')
            break
        if (fn & 1) or fn == sn:
            fr=_node(c,fr); sr=_node(c,sr)
            if not (fn & 1):
                while fn != 0 and not (fn & 1):
                    fn >>= 1; sn >>= 1
        else:
            sr=_node(sr,c)
        fn >>= 1; sn >>= 1

    if not reasons:
        if sn != 0: reasons.append('consistency_path_too_short')
        if fr != fr_expected: reasons.append('first_root_mismatch')
        if sr != sr_expected: reasons.append('second_root_mismatch')
    return {'valid':not reasons,'reasons':sorted(set(reasons)),'first_size':first,'second_size':second,'proof_nodes':len(path)}

def _time(s: str) -> datetime:
    d=datetime.fromisoformat(str(s).replace('Z','+00:00'))
    if d.tzinfo is None: d=d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)

def _key_record(record: Any):
    if isinstance(record, str): return {'public_key_hex':record,'revoked':False}
    if isinstance(record, Mapping): return dict(record)
    raise TypeError('invalid witness key record')

def verify_signed_witness_observations(observations: Sequence[Mapping[str,Any]], witness_keys: Mapping[str,Any], minimum_witnesses: int,
        expected_log_id: str, expected_tree_size: int, expected_root_hash: Any, now_iso: str, max_age_seconds: int,
        future_tolerance_seconds: int=300):
    reasons=[]; valid=set(); results=[]
    try:
        if not isinstance(witness_keys, Mapping): raise TypeError('witness_keys')
        if observations is None or isinstance(observations, (str, bytes, bytearray)):
            raise TypeError('observations')
        observations=list(observations)
        minimum=int(minimum_witnesses); size=int(expected_tree_size); root=_hash32(expected_root_hash).hex(); now=_time(now_iso)
        max_age=float(max_age_seconds); future=float(future_tolerance_seconds)
        if minimum < 1: reasons.append('witness_threshold_invalid')
        if size < 1: reasons.append('witness_expected_tree_size_invalid')
        if max_age < 0 or future < 0: reasons.append('witness_time_policy_invalid')
    except Exception:
        return {'valid':False,'reasons':['witness_policy_invalid'],'valid_witnesses':[],'observations':[]}

    for item in observations:
        local=[]; payload=dict(item.get('payload',{})) if isinstance(item,Mapping) else {}
        wid=payload.get('witness_id')
        rec=None
        try: rec=_key_record(witness_keys.get(wid)) if wid in witness_keys else None
        except Exception: local.append('witness_key_invalid')
        if payload.get('algorithm') != 'Ed25519': local.append('witness_algorithm_not_allowed')
        if not wid or rec is None: local.append('witness_unknown')
        elif rec.get('revoked'): local.append('witness_revoked')
        if payload.get('log_id') != expected_log_id: local.append('witness_log_mismatch')
        try:
            if int(payload.get('tree_size')) != size: local.append('witness_tree_size_mismatch')
        except Exception: local.append('witness_tree_size_invalid')
        try:
            if _hash32(payload.get('root_hash')).hex() != root: local.append('witness_root_mismatch')
        except Exception: local.append('witness_root_invalid')
        try:
            observed=_time(payload.get('observed_at','')); age=(now-observed).total_seconds()
            if age > max_age: local.append('witness_observation_stale')
            if age < -future: local.append('witness_observation_from_future')
        except Exception: local.append('witness_observed_at_invalid')
        if rec is not None:
            try:
                Ed25519PublicKey.from_public_bytes(bytes.fromhex(rec['public_key_hex'])).verify(bytes.fromhex(item.get('signature_hex','')),canonical_json(payload))
            except (InvalidSignature,ValueError,TypeError,KeyError): local.append('witness_signature_invalid')
        if not local and wid not in valid:
            valid.add(wid)
        results.append({'witness_id':wid,'valid':not local,'reasons':sorted(set(local))})
        reasons.extend(local)

    if len(valid) < minimum: reasons.append('witness_threshold_not_met')
    return {'valid':not reasons,'reasons':sorted(set(reasons)),'valid_witnesses':sorted(valid),'observations':results,'threshold_required':minimum}

def verify_transparency_transition(first_size: int, second_size: int, first_root: Any, second_root: Any, consistency_path: Sequence[Any],
        observations: Sequence[Mapping[str,Any]], witness_keys: Mapping[str,Any], minimum_witnesses: int, expected_log_id: str,
        now_iso: str, max_age_seconds: int, future_tolerance_seconds: int=300):
    consistency=verify_compact_consistency(first_size,second_size,first_root,second_root,consistency_path)
    witness=verify_signed_witness_observations(observations,witness_keys,minimum_witnesses,expected_log_id,second_size,second_root,now_iso,max_age_seconds,future_tolerance_seconds)
    reasons=[]
    reasons.extend('consistency:'+x for x in consistency['reasons'])
    reasons.extend('witness:'+x for x in witness['reasons'])
    return {'valid':not reasons,'reasons':sorted(set(reasons)),'consistency':consistency,'witness':witness}
