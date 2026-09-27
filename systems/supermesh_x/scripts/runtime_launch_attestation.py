"""SuperMesh-X v2.8 launch attestation and connect-pin contract."""
from __future__ import annotations
import copy, hashlib, ipaddress, json

class LaunchAttestationError(RuntimeError): pass

def _digest(v):
    return 'sha256:'+hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def _public_ip(value):
    try: ip=ipaddress.ip_address(str(value).strip('[]'))
    except ValueError: return False
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved)

def build_launch_request(run_id,worker_id,fencing_token,requested_limits,resolved_ips,input_mounts,outbox='/workspace/out'):
    limits={str(k):int(v) for k,v in requested_limits.items()}
    if not limits or any(v<=0 for v in limits.values()): raise LaunchAttestationError('positive requested limits required')
    pins=sorted(set(str(x) for x in resolved_ips))
    if not pins or any(not _public_ip(x) for x in pins): raise LaunchAttestationError('only public resolved IPs may be pinned')
    mounts=sorted(set(str(x) for x in input_mounts))
    if outbox in mounts: raise LaunchAttestationError('outbox must be distinct from immutable inputs')
    body={'schema':1,'run_id':str(run_id),'worker_id':str(worker_id),'fencing_token':int(fencing_token),'requested_limits':limits,'connect_pins':pins,'input_mounts':mounts,'outbox':str(outbox)}
    body['request_digest']=_digest(body)
    return body

def verify_mount_attestation(input_mounts,actual_mounts,outbox='/workspace/out'):
    for p in input_mounts:
        if actual_mounts.get(p)!='ro': raise LaunchAttestationError('input mount not read-only: '+str(p))
    if actual_mounts.get(outbox)!='rw': raise LaunchAttestationError('outbox must be writable')
    if outbox in set(input_mounts): raise LaunchAttestationError('outbox overlaps immutable input')
    return {'schema':1,'verified':True,'immutable_inputs':sorted(input_mounts),'outbox':outbox,'mount_digest':_digest(actual_mounts)}

def attest_launch(request,enforced_limits,actual_mounts,pid):
    enforced={str(k):int(v) for k,v in enforced_limits.items()}
    for k,want in request['requested_limits'].items():
        # Resource ceilings must be no larger than requested. For resources where
        # larger means more restrictive this adapter must normalize before attest.
        if k not in enforced or enforced[k] > int(want): raise LaunchAttestationError('resource ceiling weaker than requested: '+k)
    m=verify_mount_attestation(request['input_mounts'],actual_mounts,request['outbox'])
    if int(pid)<=0: raise LaunchAttestationError('positive pid required')
    return {'schema':1,'verified':True,'run_id':request['run_id'],'worker_id':request['worker_id'],'fencing_token':request['fencing_token'],'pid':int(pid),'enforced_limits':enforced,'mount_digest':m['mount_digest'],'request_digest':request['request_digest'],'attestation_digest':_digest({'limits':enforced,'mounts':m,'pid':int(pid)})}

def verify_connect_pin(host,resolved_ips,connected_ip):
    pins=sorted(set(str(x) for x in resolved_ips))
    connected=str(connected_ip)
    allowed=bool(pins) and connected in pins and _public_ip(connected) and all(_public_ip(x) for x in pins)
    return {'schema':1,'host':str(host),'allowed':allowed,'connected_ip':connected,'pin_digest':_digest(pins),'reason':'pinned_public_ip' if allowed else 'pin_mismatch_or_nonpublic'}

def reconcile_runtime(observed_runtime,durable_owner):
    if durable_owner is None:
        return {'schema':1,'action':'destroy_unowned_runtime' if observed_runtime else 'noop'}
    if observed_runtime is None:
        return {'schema':1,'action':'mark_lost_and_requeue','worker_id':durable_owner.get('worker_id'),'fencing_token':durable_owner.get('fencing_token')}
    same=(observed_runtime.get('worker_id')==durable_owner.get('worker_id') and int(observed_runtime.get('fencing_token',-1))==int(durable_owner.get('fencing_token',-2)))
    if not same: return {'schema':1,'action':'destroy_stale_runtime','observed_fence':observed_runtime.get('fencing_token'),'durable_fence':durable_owner.get('fencing_token')}
    return {'schema':1,'action':'adopt_if_attested' if observed_runtime.get('status')=='running' else 'reconcile_state'}
