"""Pluggable process identity evidence for recovery serialization (V26)."""
from __future__ import annotations
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
UNKNOWN="unknown"

class IdentityAssurance(Enum):
    UNAVAILABLE="unavailable"
    WEAK="weak"
    STRONG="strong"

@dataclass(frozen=True)
class ProcessIdentity:
    boot_id:str
    process_start:str
    @property
    def available(self): return self.boot_id!=UNKNOWN and self.process_start!=UNKNOWN

class ProcessIdentityProvider:
    """Conservative interface: unavailable identity never proves mismatch."""
    assurance=IdentityAssurance.UNAVAILABLE
    def current(self,pid:int)->ProcessIdentity:
        return ProcessIdentity(UNKNOWN,UNKNOWN)

class LinuxProcProcessIdentityProvider(ProcessIdentityProvider):
    assurance=IdentityAssurance.STRONG
    def _read(self,path):
        try:return Path(path).read_text(encoding="utf-8").strip()
        except OSError:return None
    def current(self,pid:int)->ProcessIdentity:
        boot=self._read("/proc/sys/kernel/random/boot_id") or UNKNOWN
        try:
            raw=Path(f"/proc/{int(pid)}/stat").read_text(encoding="utf-8")
            tail=raw[raw.rfind(")")+2:].split(); start=tail[19]
        except (OSError,ValueError,IndexError): start=UNKNOWN
        return ProcessIdentity(boot,start)

# --- Windows kernel evidence (ctypes; imported lazily, never touched on POSIX) -------------------
_WIN_PROCESS_QUERY_LIMITED_INFORMATION=0x1000
_WIN_ERROR_INVALID_PARAMETER=87   # OpenProcess result for a PID that names no process
_WIN_STILL_ACTIVE=259
_WIN_SYSTEM_TIME_OF_DAY_INFORMATION=3
_WIN_MAX_PID=0xFFFFFFFF
_win_api=None

def _windows_api():
    global _win_api
    if _win_api is None:
        import ctypes
        from ctypes import wintypes
        from types import SimpleNamespace
        k32=ctypes.WinDLL("kernel32",use_last_error=True); nt=ctypes.WinDLL("ntdll")
        k32.OpenProcess.argtypes=(wintypes.DWORD,wintypes.BOOL,wintypes.DWORD); k32.OpenProcess.restype=wintypes.HANDLE
        k32.GetExitCodeProcess.argtypes=(wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)); k32.GetExitCodeProcess.restype=wintypes.BOOL
        k32.GetProcessTimes.argtypes=(wintypes.HANDLE,)+(ctypes.POINTER(wintypes.FILETIME),)*4; k32.GetProcessTimes.restype=wintypes.BOOL
        k32.CloseHandle.argtypes=(wintypes.HANDLE,); k32.CloseHandle.restype=wintypes.BOOL
        nt.NtQuerySystemInformation.argtypes=(wintypes.ULONG,ctypes.c_void_p,wintypes.ULONG,ctypes.POINTER(wintypes.ULONG))
        nt.NtQuerySystemInformation.restype=ctypes.c_long
        class TimeOfDay(ctypes.Structure):  # SYSTEM_TIMEOFDAY_INFORMATION (48 bytes)
            _fields_=[("BootTime",ctypes.c_longlong),("CurrentTime",ctypes.c_longlong),("TimeZoneBias",ctypes.c_longlong),
                      ("TimeZoneId",ctypes.c_ulong),("Reserved",ctypes.c_ulong),("BootTimeBias",ctypes.c_longlong),
                      ("SleepTimeBias",ctypes.c_ulonglong)]
        _win_api=SimpleNamespace(ctypes=ctypes,wintypes=wintypes,k32=k32,nt=nt,TimeOfDay=TimeOfDay)
    return _win_api

def windows_pid_definitely_dead(pid:int)->bool:
    """True only on positive kernel evidence that no running process holds ``pid``.

    OpenProcess fails with ERROR_INVALID_PARAMETER for a PID that names no process; an existing
    process object whose exit code is not STILL_ACTIVE has terminated. Access denied (a live
    protected/foreign process) and every other failure prove nothing, so they return False.
    """
    pid=int(pid)
    if not 0<pid<=_WIN_MAX_PID: return False
    api=_windows_api()
    h=api.k32.OpenProcess(_WIN_PROCESS_QUERY_LIMITED_INFORMATION,False,pid)
    if not h: return api.ctypes.get_last_error()==_WIN_ERROR_INVALID_PARAMETER
    try:
        code=api.wintypes.DWORD()
        if not api.k32.GetExitCodeProcess(h,api.ctypes.byref(code)): return False
        # STILL_ACTIVE is also a legal exit status; treating it as running errs toward "not dead".
        return code.value!=_WIN_STILL_ACTIVE
    finally: api.k32.CloseHandle(h)

def windows_process_start_identity(pid:int)->str:
    """Absolute process creation time (FILETIME, 100 ns ticks since 1601 UTC); UNKNOWN when unreadable."""
    pid=int(pid)
    if not 0<pid<=_WIN_MAX_PID: return UNKNOWN
    api=_windows_api()
    h=api.k32.OpenProcess(_WIN_PROCESS_QUERY_LIMITED_INFORMATION,False,pid)
    if not h: return UNKNOWN
    try:
        t=[api.wintypes.FILETIME() for _ in range(4)]
        if not api.k32.GetProcessTimes(h,*(api.ctypes.byref(x) for x in t)): return UNKNOWN
        created=(t[0].dwHighDateTime<<32)|t[0].dwLowDateTime
        return str(created) if created else UNKNOWN
    finally: api.k32.CloseHandle(h)

def windows_boot_identity()->str:
    """Kernel-session boot identity: BootTime - BootTimeBias from SystemTimeOfDayInformation.

    Raw BootTime moves whenever the wall clock is stepped (the kernel adds the same delta to
    BootTimeBias), so it is NOT stable within a boot; the bias-corrected value is (it equals WMI
    Win32_OperatingSystem.LastBootUpTime). Two consecutive reads must agree so a read torn by a
    concurrent clock step can never surface as a spurious boot change. UNKNOWN when unavailable.
    """
    api=_windows_api()
    def read():
        info=api.TimeOfDay(); n=api.wintypes.ULONG()
        if api.nt.NtQuerySystemInformation(_WIN_SYSTEM_TIME_OF_DAY_INFORMATION,api.ctypes.byref(info),
                                           api.ctypes.sizeof(info),api.ctypes.byref(n))!=0: return None
        if n.value<api.TimeOfDay.BootTimeBias.offset+8: return None
        boot=info.BootTime-info.BootTimeBias
        return boot if boot>0 else None
    first=read()
    for _ in range(3):
        second=read()
        if first is not None and first==second: return f"windows-boot-{first}"
        first=second
    return UNKNOWN

class WindowsProcessIdentityProvider(ProcessIdentityProvider):
    """Windows kernel evidence: bias-corrected boot time + absolute process creation time."""
    assurance=IdentityAssurance.STRONG
    def current(self,pid:int)->ProcessIdentity:
        return ProcessIdentity(windows_boot_identity(),windows_process_start_identity(pid))

def default_process_identity_provider()->ProcessIdentityProvider:
    if Path("/proc/sys/kernel/random/boot_id").exists() and Path("/proc/self/stat").exists():
        return LinuxProcProcessIdentityProvider()
    if os.name=="nt":
        return WindowsProcessIdentityProvider()
    return ProcessIdentityProvider()
