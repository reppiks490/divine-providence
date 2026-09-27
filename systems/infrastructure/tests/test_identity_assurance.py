from process_identity import ProcessIdentity,ProcessIdentityProvider,IdentityAssurance
from recovery_auth import HMACRecoveryAuthenticator,AuthenticatedRecoveryEnvelope

class Strong(ProcessIdentityProvider):
    assurance=IdentityAssurance.STRONG
    def current(self,pid): return ProcessIdentity('boot','start')
class Weak(ProcessIdentityProvider):
    assurance=IdentityAssurance.WEAK
    def current(self,pid): return ProcessIdentity('boot','unknown')

def test_provider_assurance_is_explicit():
    assert Strong().assurance is IdentityAssurance.STRONG
    assert Weak().assurance is IdentityAssurance.WEAK

def test_authenticated_envelope_roundtrip_and_tamper():
    a=HMACRecoveryAuthenticator('producer-A',b'k'*32)
    e=a.sign({'checkpoint_hash':'abc','generation':7})
    assert a.verify(e)
    bad_sig=e.signature[:-1]+('1' if e.signature[-1]!='1' else '0')
    bad=AuthenticatedRecoveryEnvelope(e.version,e.producer_id,e.algorithm,e.payload_hash,e.payload,bad_sig)
    assert not a.verify(bad)

def test_wrong_producer_key_rejected():
    e=HMACRecoveryAuthenticator('A',b'a'*32).sign({'x':1})
    assert not HMACRecoveryAuthenticator('B',b'b'*32).verify(e)

def test_authenticator_has_no_mutation_authority():
    a=HMACRecoveryAuthenticator('A',b'a'*32)
    assert {'execute','mutate','promote','rollback','acquire','release'}.isdisjoint(set(dir(a)))
