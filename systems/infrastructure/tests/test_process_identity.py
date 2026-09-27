import sys, pytest
from process_identity import ProcessIdentity,ProcessIdentityProvider,LinuxProcProcessIdentityProvider,default_process_identity_provider,UNKNOWN
from recovery_lock import RecoveryChainLock
class Fake(ProcessIdentityProvider):
    def __init__(self,boot="boot",start="1"): self.ident=ProcessIdentity(boot,start)
    def current(self,pid): return self.ident
@pytest.mark.skipif(sys.platform=="win32",reason="LinuxProcProcessIdentityProvider reads /proc/sys/kernel/random/boot_id and /proc/<pid>/stat, which do not exist on Windows; the Windows default provider is asserted available by test_v25_recovery_lock_identity::test_owner_is_versioned_and_fingerprinted")
def test_linux_provider_has_current_identity():
    assert LinuxProcProcessIdentityProvider().current(__import__("os").getpid()).available
def test_unsupported_provider_fails_closed(tmp_path):
    lock=RecoveryChainLock(tmp_path/"l",timeout_seconds=0,identity_provider=ProcessIdentityProvider())
    assert not lock.acquire() and not (tmp_path/"l").exists()
def test_injected_provider_owns_and_releases(tmp_path):
    lock=RecoveryChainLock(tmp_path/"l",identity_provider=Fake())
    assert lock.acquire(); assert lock.owner.boot_id=="boot"; assert lock.release()
def test_provider_failure_never_proves_identity_mismatch(tmp_path):
    lock=RecoveryChainLock(tmp_path/"l",identity_provider=ProcessIdentityProvider())
    from recovery_lock import LockOwner,_fingerprint,LOCK_FORMAT_VERSION
    fp=_fingerprint(LOCK_FORMAT_VERSION,123,"a"*16,1.0,"old","7")
    o=LockOwner(123,"a"*16,1.0,LOCK_FORMAT_VERSION,"old","7",fp)
    assert not lock._identity_mismatch(o)
def test_pid_reuse_detected_by_provider(tmp_path):
    lock=RecoveryChainLock(tmp_path/"l",identity_provider=Fake("sameboot","newstart"))
    from recovery_lock import LockOwner,_fingerprint,LOCK_FORMAT_VERSION
    fp=_fingerprint(LOCK_FORMAT_VERSION,123,"b"*16,1.0,"sameboot","oldstart")
    o=LockOwner(123,"b"*16,1.0,LOCK_FORMAT_VERSION,"sameboot","oldstart",fp)
    assert lock._identity_mismatch(o)
def test_boot_change_detected_by_provider(tmp_path):
    lock=RecoveryChainLock(tmp_path/"l",identity_provider=Fake("newboot","1"))
    from recovery_lock import LockOwner,_fingerprint,LOCK_FORMAT_VERSION
    fp=_fingerprint(LOCK_FORMAT_VERSION,123,"c"*16,1.0,"oldboot","1")
    o=LockOwner(123,"c"*16,1.0,LOCK_FORMAT_VERSION,"oldboot","1",fp)
    assert lock._identity_mismatch(o)
