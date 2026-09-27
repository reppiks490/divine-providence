"""Identity-bound interprocess recovery-chain append lock (V25). Evidence-side only."""
from __future__ import annotations
import errno, hashlib, json, os, secrets, time
from dataclasses import dataclass
from pathlib import Path
from process_identity import (default_process_identity_provider,windows_boot_identity,
                              windows_pid_definitely_dead,windows_process_start_identity)

LOCK_FORMAT_VERSION=25
UNKNOWN='unknown'

def _read_text(path):
    try: return Path(path).read_text(encoding='utf-8').strip()
    except OSError: return None

def _boot_identity():
    if os.name=='nt': return windows_boot_identity()
    value=_read_text('/proc/sys/kernel/random/boot_id')
    return value if value else UNKNOWN

def _process_start_identity(pid:int):
    """Linux /proc start-time ticks; Windows process creation time; UNKNOWN elsewhere/when unreadable."""
    if os.name=='nt': return windows_process_start_identity(pid)
    try:
        raw=Path(f'/proc/{int(pid)}/stat').read_text(encoding='utf-8')
        # comm may contain spaces/parentheses; fields after final ')' begin at field 3.
        tail=raw[raw.rfind(')')+2:].split()
        return tail[19]  # field 22 overall: starttime
    except (OSError,ValueError,IndexError): return UNKNOWN

def _fingerprint(version,pid,nonce,created,boot_id,process_start):
    body={'version':version,'pid':pid,'nonce':nonce,'created_unix':created,'boot_id':boot_id,'process_start':process_start}
    return hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()

@dataclass(frozen=True)
class LockOwner:
    pid:int
    nonce:str
    created_unix:float
    version:int=LOCK_FORMAT_VERSION
    boot_id:str=UNKNOWN
    process_start:str=UNKNOWN
    owner_fingerprint:str=''

    @classmethod
    def create(cls,pid:int,created:float|None=None):
        nonce=secrets.token_hex(16); created=time.time() if created is None else float(created)
        ident=default_process_identity_provider().current(pid)
        boot=ident.boot_id; start=ident.process_start
        fp=_fingerprint(LOCK_FORMAT_VERSION,pid,nonce,created,boot,start)
        return cls(pid,nonce,created,LOCK_FORMAT_VERSION,boot,start,fp)

    def valid(self):
        if self.version!=LOCK_FORMAT_VERSION or self.pid<=0 or len(self.nonce)<16 or self.created_unix<=0: return False
        if self.boot_id==UNKNOWN or self.process_start==UNKNOWN: return False
        return self.owner_fingerprint==_fingerprint(self.version,self.pid,self.nonce,self.created_unix,self.boot_id,self.process_start)

class RecoveryChainLock:
    def __init__(self,path,*,timeout_seconds:float=2.0,poll_seconds:float=.01,stale_after_seconds:float=30.0,identity_provider=None):
        self.identity_provider=identity_provider or default_process_identity_provider()
        self._provider_injected=identity_provider is not None
        self.path=Path(path); self.timeout_seconds=float(timeout_seconds); self.poll_seconds=float(poll_seconds)
        self.stale_after_seconds=float(stale_after_seconds); self._owner=None
    @property
    def owner(self): return self._owner
    def _encode(self,o): return (json.dumps(o.__dict__,sort_keys=True,separators=(',',':'))+'\n').encode()
    def _read_owner(self):
        try:
            d=json.loads(self.path.read_text(encoding='utf-8'))
            o=LockOwner(int(d['pid']),str(d['nonce']),float(d['created_unix']),int(d['version']),str(d['boot_id']),str(d['process_start']),str(d['owner_fingerprint']))
            return o if o.valid() else None
        except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError): return None
    @staticmethod
    def _pid_definitely_dead(pid):
        # On Windows os.kill(pid,0) is GenerateConsoleCtrlEvent(CTRL_C_EVENT,pid), not a probe.
        if os.name=='nt': return windows_pid_definitely_dead(pid)
        try: os.kill(pid,0); return False
        except ProcessLookupError: return True
        except PermissionError: return False
        except OSError as exc: return exc.errno==errno.ESRCH
    def _identity_mismatch(self,o):
        ident=self.identity_provider.current(o.pid)
        if not self._provider_injected:
            # Preserve V25 module-level identity hooks for backward-compatible tests/integrations.
            boot=_boot_identity(); start=_process_start_identity(o.pid)
            ident=type(ident)(boot,start)
        if not ident.available: return False
        if o.boot_id!=ident.boot_id: return True
        return ident.process_start!=o.process_start
    def _reclaim_if_stale(self):
        o=self._read_owner()
        if o is None: return False
        # Negative age (clock moved backward) is never stale.
        age=time.time()-o.created_unix
        if age < max(0.0,self.stale_after_seconds): return False
        # Definitive death OR identity mismatch (PID reuse / prior boot) is required.
        if not (self._pid_definitely_dead(o.pid) or self._identity_mismatch(o)): return False
        if self._read_owner()!=o: return False
        try: self.path.unlink(); return True
        except FileNotFoundError: return True
        except OSError: return False
    def acquire(self):
        self.path.parent.mkdir(parents=True,exist_ok=True); deadline=time.monotonic()+max(0.0,self.timeout_seconds)
        while True:
            ident=self.identity_provider.current(os.getpid())
            if not ident.available: return False
            nonce=secrets.token_hex(16); created=time.time()
            o=LockOwner(os.getpid(),nonce,created,LOCK_FORMAT_VERSION,ident.boot_id,ident.process_start,
                        _fingerprint(LOCK_FORMAT_VERSION,os.getpid(),nonce,created,ident.boot_id,ident.process_start))
            if not o.valid(): return False  # identity unavailable => fail closed
            try:
                fd=os.open(str(self.path),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
                try: os.write(fd,self._encode(o)); os.fsync(fd)
                finally: os.close(fd)
                self._owner=o; return True
            except FileExistsError:
                if self._reclaim_if_stale(): continue
                if time.monotonic()>=deadline: return False
                time.sleep(max(.001,self.poll_seconds))
    def release(self):
        o=self._owner
        if o is None:return False
        removed=False
        if self._read_owner()==o:
            try:self.path.unlink(); removed=True
            except FileNotFoundError:pass
        self._owner=None; return removed
    def __enter__(self):
        if not self.acquire():raise TimeoutError('recovery chain lock unavailable')
        return self
    def __exit__(self,*_):self.release()
