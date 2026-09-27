"""Explicit trusted-time contracts for freeze-resistant policy decisions.

SuperMesh never treats the process wall clock as trusted implicitly. Callers must
provide a source whose ``sample()`` method returns an already-authenticated
``TrustedTimeSample``.  The optional durable floor detects local time rollback;
an external minimum is still required to detect rollback of *all* local state.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

try:
    from .witnessed_transparency import WitnessError, _canon
except ImportError:  # direct-script compatibility
    from witnessed_transparency import WitnessError, _canon


def _sha256(value) -> str:
    return "sha256:" + hashlib.sha256(_canon(value)).hexdigest()


def _fsync_directory(path):
    try:
        fd = os.open(Path(path), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        # Atomic replacement still applies where same-directory rename is
        # supported; stronger power-loss durability is platform dependent.
        pass


@dataclass(frozen=True)
class TrustedTimeSample:
    """Already-authenticated time assertion supplied by a trusted adapter.

    ``unix_seconds`` is the center of the assertion and
    ``uncertainty_seconds`` defines a closed interval around it.  ``source``
    names the adapter/authority. ``evidence_digest`` may bind public external
    evidence (for example a verified timestamp token) without embedding it.
    """

    unix_seconds: int
    uncertainty_seconds: int = 0
    source: str = ""
    evidence_digest: str | None = None

    def __post_init__(self):
        if isinstance(self.unix_seconds, bool) or not isinstance(self.unix_seconds, int):
            raise WitnessError("trusted time value must be an integer number of Unix seconds")
        if self.unix_seconds < 0:
            raise WitnessError("trusted time value must be non-negative")
        if isinstance(self.uncertainty_seconds, bool) or not isinstance(self.uncertainty_seconds, int):
            raise WitnessError("trusted time uncertainty must be an integer number of seconds")
        if self.uncertainty_seconds < 0:
            raise WitnessError("trusted time uncertainty must be non-negative")
        source = str(self.source).strip()
        if not source:
            raise WitnessError("trusted time source is required")
        evidence = self.evidence_digest
        if evidence is not None and not str(evidence).strip():
            raise WitnessError("trusted time evidence digest is invalid")
        object.__setattr__(self, "unix_seconds", self.unix_seconds)
        object.__setattr__(self, "uncertainty_seconds", self.uncertainty_seconds)
        object.__setattr__(self, "source", source)
        if evidence is not None:
            object.__setattr__(self, "evidence_digest", str(evidence))

    @property
    def lower_bound_unix(self) -> int:
        return max(0, self.unix_seconds - self.uncertainty_seconds)

    @property
    def upper_bound_unix(self) -> int:
        return self.unix_seconds + self.uncertainty_seconds

    def to_public_dict(self):
        out = {
            "schema": 1,
            "unix_seconds": self.unix_seconds,
            "uncertainty_seconds": self.uncertainty_seconds,
            "source": self.source,
        }
        if self.evidence_digest is not None:
            out["evidence_digest"] = self.evidence_digest
        return out

    def digest(self) -> str:
        return _sha256(self.to_public_dict())


class DurableTrustedTimeFloor:
    """Crash-consistent local monotonic floor for trusted-time lower bounds."""

    def __init__(self, path):
        self.path = Path(path)
        self.lower_bound_unix = None
        self.floor_digest = None
        if self.path.exists():
            self._load()

    def _load(self):
        try:
            envelope = json.loads(self.path.read_text())
            payload = envelope["payload"]
        except Exception as exc:
            raise WitnessError("malformed trusted time floor") from exc
        if envelope.get("sha256") != hashlib.sha256(_canon(payload)).hexdigest():
            raise WitnessError("trusted time floor integrity failure")
        try:
            if payload.get("schema") != 1 or payload.get("kind") != "trusted-time-floor":
                raise ValueError("bad schema")
            lower = int(payload["lower_bound_unix"])
            if lower < 0:
                raise ValueError("negative floor")
        except Exception as exc:
            raise WitnessError("malformed trusted time floor") from exc
        self.lower_bound_unix = lower
        self.floor_digest = _sha256(payload)


    def _acquire_update_lock(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock = self.path.with_name(self.path.name + ".update.lock")
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise WitnessError("trusted time floor update already in progress") from exc
        except OSError as exc:
            raise WitnessError("unable to acquire trusted time floor update lock") from exc
        try:
            os.write(fd, (str(os.getpid()) + "\n").encode("ascii"))
            os.fsync(fd)
        finally:
            os.close(fd)
        _fsync_directory(lock.parent)
        return lock

    @staticmethod
    def _release_update_lock(lock):
        try:
            Path(lock).unlink()
            _fsync_directory(Path(lock).parent)
        except OSError:
            # A stranded lock fails closed. An operator must verify that no
            # writer is active before removing it.
            pass

    def _persist(self, payload):
        target = self.path
        target.parent.mkdir(parents=True, exist_ok=True)
        envelope = {
            "payload": payload,
            "sha256": hashlib.sha256(_canon(payload)).hexdigest(),
        }
        data = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
        tmp = target.with_name(target.name + ".tmp")
        try:
            with tmp.open("w") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, target)
            _fsync_directory(target.parent)
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass

    def accept(self, sample: TrustedTimeSample, *, minimum_lower_bound_unix=None, max_uncertainty_seconds=None):
        if not isinstance(sample, TrustedTimeSample):
            raise WitnessError("trusted time source returned invalid sample")
        lock = self._acquire_update_lock()
        try:
            # Re-read inside the exclusive section so a stale process cannot
            # publish against an out-of-date in-memory floor.
            if self.path.exists():
                self._load()
            else:
                self.lower_bound_unix = None
                self.floor_digest = None

            if max_uncertainty_seconds is not None:
                maximum = int(max_uncertainty_seconds)
                if maximum < 0:
                    raise WitnessError("trusted time uncertainty limit is invalid")
                if sample.uncertainty_seconds > maximum:
                    raise WitnessError("trusted time uncertainty exceeds configured maximum")

            lower = sample.lower_bound_unix
            upper = sample.upper_bound_unix
            if minimum_lower_bound_unix is not None and lower < int(minimum_lower_bound_unix):
                raise WitnessError("trusted time below external minimum")
            if self.lower_bound_unix is not None and lower < self.lower_bound_unix:
                raise WitnessError("trusted time rollback detected")

            if self.lower_bound_unix is None or lower > self.lower_bound_unix:
                payload = {
                    "schema": 1,
                    "kind": "trusted-time-floor",
                    "lower_bound_unix": lower,
                    "last_upper_bound_unix": upper,
                    "sample_digest": sample.digest(),
                    "source": sample.source,
                }
                if sample.evidence_digest is not None:
                    payload["evidence_digest"] = sample.evidence_digest
                try:
                    self._persist(payload)
                except Exception as exc:
                    if isinstance(exc, WitnessError):
                        raise
                    raise WitnessError("trusted time floor persistence failed") from exc
                self.lower_bound_unix = lower
                self.floor_digest = _sha256(payload)

            return {
                "schema": 1,
                "source": sample.source,
                "sample_digest": sample.digest(),
                "lower_bound_unix": lower,
                "upper_bound_unix": upper,
                "uncertainty_seconds": sample.uncertainty_seconds,
                "floor_lower_bound_unix": self.lower_bound_unix,
                "floor_digest": self.floor_digest,
                **({"evidence_digest": sample.evidence_digest} if sample.evidence_digest is not None else {}),
            }
        finally:
            self._release_update_lock(lock)



class TrustedTimeGuard:
    """Fixed-sample policy freshness gate with optional durable rollback floor."""

    def __init__(
        self,
        source,
        *,
        floor: DurableTrustedTimeFloor | None = None,
        max_uncertainty_seconds=None,
        minimum_lower_bound_unix=None,
    ):
        self.source = source
        self.floor = floor
        self.max_uncertainty_seconds = max_uncertainty_seconds
        self.minimum_lower_bound_unix = minimum_lower_bound_unix

    def capture(self):
        try:
            sample = self.source.sample()
        except WitnessError:
            raise
        except Exception as exc:
            raise WitnessError("trusted time source unavailable") from exc
        if not isinstance(sample, TrustedTimeSample):
            raise WitnessError("trusted time source returned invalid sample")
        if self.floor is not None:
            return self.floor.accept(
                sample,
                minimum_lower_bound_unix=self.minimum_lower_bound_unix,
                max_uncertainty_seconds=self.max_uncertainty_seconds,
            )
        if self.max_uncertainty_seconds is not None and sample.uncertainty_seconds > int(self.max_uncertainty_seconds):
            raise WitnessError("trusted time uncertainty exceeds configured maximum")
        if self.minimum_lower_bound_unix is not None and sample.lower_bound_unix < int(self.minimum_lower_bound_unix):
            raise WitnessError("trusted time below external minimum")
        return {
            "schema": 1,
            "source": sample.source,
            "sample_digest": sample.digest(),
            "lower_bound_unix": sample.lower_bound_unix,
            "upper_bound_unix": sample.upper_bound_unix,
            "uncertainty_seconds": sample.uncertainty_seconds,
            **({"evidence_digest": sample.evidence_digest} if sample.evidence_digest is not None else {}),
        }

    @staticmethod
    def _check_policy_against_report(policy, report):
        expires = getattr(policy, "expires_unix", None)
        if expires is None:
            return None
        expires = int(expires)
        lower = int(report["lower_bound_unix"])
        upper = int(report["upper_bound_unix"])
        if expires <= lower:
            raise WitnessError("witness policy expired")
        if expires <= upper:
            raise WitnessError("trusted time uncertainty overlaps policy expiry boundary")
        return {
            **dict(report),
            "policy_epoch": int(policy.epoch),
            "policy_digest": str(policy.digest()),
            "policy_expires_unix": expires,
        }

    def assert_policy_fresh(self, policy, *, report=None):
        if getattr(policy, "expires_unix", None) is None:
            return None
        fixed = self.capture() if report is None else dict(report)
        return self._check_policy_against_report(policy, fixed)

    def assert_policies_fresh(self, policies):
        policies = list(policies)
        expiring = [p for p in policies if getattr(p, "expires_unix", None) is not None]
        if not expiring:
            return None
        fixed = self.capture()
        reports = [self._check_policy_against_report(p, fixed) for p in expiring]
        return {"fixed_trusted_time": fixed, "policies": reports}
