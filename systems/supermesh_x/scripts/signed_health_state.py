"""Authenticated, replay-resistant distributed provider-health snapshots.

Uses HMAC-SHA256 with explicit domain separation and key IDs.  Authentication
is routing integrity only; this module never grants execution authority.
"""
import copy
import hashlib
import hmac
import json

class VerificationError(ValueError):
    pass

_AUTH_FIELDS={'auth_tag'}
_REQUIRED={'provider','health','circuit','sequence','epoch'}

def _body(row):
    return {k:v for k,v in row.items() if k not in _AUTH_FIELDS}

def _canonical(row, domain):
    envelope={'domain':str(domain),'payload':_body(row)}
    return json.dumps(envelope, sort_keys=True, separators=(',',':'), ensure_ascii=False).encode()

def _validate_shape(row):
    missing=_REQUIRED-set(row)
    if missing: raise VerificationError('missing fields: '+','.join(sorted(missing)))
    if int(row['sequence']) < 0 or int(row['epoch']) < 0: raise VerificationError('negative epoch/sequence')
    if not 0.0 <= float(row['health']) <= 1.0: raise VerificationError('health out of range')

def sign_health_snapshot(row, *, key, key_id, domain='supermesh.health.v1'):
    if not isinstance(key,(bytes,bytearray)) or len(key)<16: raise ValueError('key too short')
    out=copy.deepcopy(row); _validate_shape(out)
    out['key_id']=str(key_id)
    out['auth_alg']='HMAC-SHA256'
    out['auth_tag']=hmac.new(bytes(key), _canonical(out,domain), hashlib.sha256).hexdigest()
    return out

def verify_health_snapshot(row, *, keys, minimum_epoch=0, last_sequence=-1, domain='supermesh.health.v1'):
    out=copy.deepcopy(row); _validate_shape(out)
    if out.get('auth_alg')!='HMAC-SHA256': raise VerificationError('unsupported auth algorithm')
    kid=str(out.get('key_id',''))
    key=keys.get(kid)
    if not isinstance(key,(bytes,bytearray)): raise VerificationError('unknown key id')
    supplied=str(out.get('auth_tag',''))
    expected=hmac.new(bytes(key), _canonical(out,domain), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(supplied,expected): raise VerificationError('authentication failed')
    if int(out['epoch']) < int(minimum_epoch): raise VerificationError('epoch rollback')
    if int(out['sequence']) <= int(last_sequence): raise VerificationError('replay/non-monotonic sequence')
    return out
