"""Explicit overlap/revocation policy for authenticated provider-health state."""
from dataclasses import dataclass
import hashlib, json
from .signed_health_state import verify_health_snapshot, VerificationError

class RotationError(VerificationError): pass

@dataclass(frozen=True)
class KeyRotationPolicy:
    active_key_id: str
    previous_key_id: str|None = None
    overlap_until_epoch: int = -1
    revoked_key_ids: frozenset[str] = frozenset()
    def __post_init__(self):
        if not self.active_key_id: raise ValueError('active key id required')
        if self.active_key_id in self.revoked_key_ids: raise ValueError('active key cannot be revoked')
        if int(self.overlap_until_epoch) < -1: raise ValueError('invalid overlap epoch')

def verify_with_rotation(row, *, keys, policy, minimum_epoch=0, last_sequence=-1, domain='supermesh.health.v1'):
    kid=str(row.get('key_id','')); epoch=int(row.get('epoch',-1))
    if kid in policy.revoked_key_ids: raise RotationError('key revoked')
    allowed = kid == policy.active_key_id or (kid == policy.previous_key_id and epoch <= policy.overlap_until_epoch)
    if not allowed: raise RotationError('key outside rotation policy')
    return verify_health_snapshot(row, keys=keys, minimum_epoch=minimum_epoch, last_sequence=last_sequence, domain=domain)

def rotation_receipt(policy, *, event, epoch):
    body={'event':str(event),'epoch':int(epoch),'active_key_id':policy.active_key_id,
          'previous_key_id':policy.previous_key_id,'overlap_until_epoch':int(policy.overlap_until_epoch),
          'revoked_key_ids':sorted(policy.revoked_key_ids)}
    raw=json.dumps(body,sort_keys=True,separators=(',',':')).encode()
    return {**body,'receipt_sha256':hashlib.sha256(raw).hexdigest()}
