"""Crash-consistent public gossip receipt journal with hash-chain replay.

v3.6 adds additive, witness-signed replay compaction. The original journal
remains append-only and is never truncated: a signed snapshot authenticates a
verified prefix while a much smaller signed anchor chain chooses the latest
accepted snapshot. Legacy ``load()`` therefore remains fully compatible and
forensic history remains intact.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

try:
    from .witnessed_transparency import GossipReceiptStore, WitnessError, _canon
except ImportError:  # direct-script compatibility
    from witnessed_transparency import GossipReceiptStore, WitnessError, _canon


def _entry_digest(body):
    return hashlib.sha256(_canon(body)).hexdigest()


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _policy_bind(statement, registry):
    epoch = getattr(registry, "policy_epoch", None)
    digest = getattr(registry, "policy_digest", None)
    if (epoch is None) != (digest is None):
        raise WitnessError("incomplete witness policy registry")
    if epoch is not None:
        statement["policy_epoch"] = int(epoch)
        statement["policy_digest"] = str(digest)
    return statement


def _required_threshold(registry, statement):
    if hasattr(registry, "threshold_for_statement"):
        return int(registry.threshold_for_statement(statement))
    try:
        return int(registry.threshold)
    except Exception as exc:
        raise WitnessError("compaction requires a witness threshold") from exc


def _sign_statement(statement, witnesses, registry, *, label="compaction"):
    receipts, seen = [], set()
    for witness in witnesses:
        wid = str(witness.witness_id)
        if wid in seen:
            continue
        sig = witness.sign(statement)
        registry.verify(wid, statement, sig)
        seen.add(wid)
        receipts.append({"witness_id": wid, "signature": sig})
    if len(receipts) < _required_threshold(registry, statement):
        raise WitnessError(f"{label} witness quorum invalid")
    return receipts


def _verify_statement(statement, signatures, registry, *, label="compaction"):
    seen = set()
    try:
        for receipt in signatures:
            wid = str(receipt["witness_id"])
            if wid in seen:
                continue
            registry.verify(wid, statement, receipt["signature"])
            seen.add(wid)
    except WitnessError:
        raise
    except Exception as exc:
        raise WitnessError(f"malformed {label} signatures") from exc
    if len(seen) < _required_threshold(registry, statement):
        raise WitnessError(f"{label} witness quorum invalid")
    return True


def _fsync_directory(path):
    try:
        fd = os.open(Path(path), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        # Some platforms/filesystems do not permit directory fsync. The caller
        # still gets atomic same-directory publication semantics, but the
        # stronger power-loss durability guarantee is platform dependent.
        pass


class DurableGossipJournal:
    def __init__(self, path, registry):
        self.path = Path(path)
        self.registry = registry
        self.store = GossipReceiptStore(registry=registry)
        self.sequence = 0
        self.last_digest = None

    def _preflight(self, checkpoint, *, historical=False):
        if not historical and hasattr(self.registry, "assert_current_policy_fresh"):
            self.registry.assert_current_policy_fresh()
        self.store._authenticate(checkpoint)
        if not historical and hasattr(self.registry, "policy_epoch"):
            if int(checkpoint.get("policy_epoch", -1)) != int(self.registry.policy_epoch):
                raise WitnessError("stale policy epoch")
            if checkpoint.get("policy_digest") != self.registry.policy_digest:
                raise WitnessError("stale policy digest")
        latest = self.store.latest(checkpoint["log_id"])
        if latest is not None:
            size, prior_size = int(checkpoint["tree_size"]), int(latest["tree_size"])
            if size < prior_size:
                raise WitnessError("gossip rollback detected")
            if size == prior_size and checkpoint["root"] != latest["root"]:
                raise WitnessError("gossip equivocation detected")
            if "policy_epoch" in checkpoint and "policy_epoch" in latest:
                if int(checkpoint["policy_epoch"]) < int(latest["policy_epoch"]):
                    raise WitnessError("gossip policy epoch rollback")
        return True

    def _append_envelope(self, envelope):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existed = self.path.exists()
        with self.path.open("a") as fh:
            fh.write(json.dumps(envelope, sort_keys=True, separators=(",", ":")) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        if not existed:
            _fsync_directory(self.path.parent)

    def append(self, checkpoint):
        cp = dict(checkpoint)
        self._preflight(cp, historical=False)
        body = {
            "schema": 1,
            "sequence": self.sequence + 1,
            "previous_digest": self.last_digest,
            "receipt": cp,
        }
        envelope = {**body, "entry_digest": _entry_digest(body)}
        try:
            self._append_envelope(envelope)
        except Exception as exc:
            raise WitnessError("journal persistence failed") from exc
        # Persistence comes first. If the process dies here, replay reconstructs state.
        self.store.observe(cp)
        self.sequence += 1
        self.last_digest = envelope["entry_digest"]
        return envelope["entry_digest"]

    @staticmethod
    def _replay_lines(obj, lines, *, sequence=0, previous=None):
        for raw in lines:
            if not raw.strip():
                continue
            try:
                env = json.loads(raw)
                body = {k: env[k] for k in ("schema", "sequence", "previous_digest", "receipt")}
            except Exception as exc:
                raise WitnessError("malformed gossip journal") from exc
            if env.get("entry_digest") != _entry_digest(body):
                raise WitnessError("gossip journal integrity failure")
            if int(env.get("sequence", -1)) != sequence + 1 or env.get("previous_digest") != previous:
                raise WitnessError("gossip journal chain failure")
            cp = dict(env["receipt"])
            obj._preflight(cp, historical=True)
            obj.store.observe(cp)
            sequence += 1
            previous = env["entry_digest"]
        obj.sequence = sequence
        obj.last_digest = previous
        return obj

    @classmethod
    def load(cls, path, registry):
        obj = cls(path, registry)
        p = Path(path)
        if not p.exists():
            return obj
        try:
            lines = p.read_text().splitlines()
        except Exception as exc:
            raise WitnessError("unable to read gossip journal") from exc
        return cls._replay_lines(obj, lines)

    @classmethod
    def recover(cls, path, registry, quarantine_dir=None):
        """Recover only an incomplete final JSON line; fail closed on authenticated corruption."""
        p = Path(path)
        try:
            data = p.read_bytes()
        except Exception as exc:
            raise WitnessError("unable to read gossip journal") from exc
        try:
            obj = cls.load(p, registry)
            obj.recovery_report = {"quarantined_bytes": 0, "quarantine_path": None}
            return obj
        except WitnessError as exc:
            strict_error = exc
        if not data or data.endswith(b"\n"):
            raise strict_error
        cut = data.rfind(b"\n") + 1
        prefix, tail = data[:cut], data[cut:]
        # Recovery is deliberately narrow: only malformed/incomplete JSON at EOF is recoverable.
        try:
            json.loads(tail.decode("utf-8"))
        except Exception:
            pass
        else:
            raise strict_error
        qdir = Path(quarantine_dir) if quarantine_dir else p.parent / "quarantine"
        qdir.mkdir(parents=True, exist_ok=True)
        qpath = qdir / (p.name + ".torn." + str(time.time_ns()))
        with qpath.open("xb") as fh:
            fh.write(tail)
            fh.flush()
            os.fsync(fh.fileno())
        tmp = p.with_name(p.name + ".recover.tmp")
        with tmp.open("wb") as fh:
            fh.write(prefix)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, p)
        _fsync_directory(p.parent)
        obj = cls.load(p, registry)
        obj.recovery_report = {"quarantined_bytes": len(tail), "quarantine_path": str(qpath)}
        return obj

    @staticmethod
    def _read_anchor_chain(anchor_path, registry):
        p = Path(anchor_path)
        if not p.exists():
            return []
        try:
            raw_lines = p.read_text().splitlines()
        except Exception as exc:
            raise WitnessError("unable to read compaction anchor journal") from exc
        out = []
        previous_digest = None
        previous_epoch = 0
        previous_sequence = 0
        previous_prefix_bytes = 0
        for raw in raw_lines:
            if not raw.strip():
                continue
            try:
                env = json.loads(raw)
                statement = dict(env["statement"])
                signatures = list(env["signatures"])
            except Exception as exc:
                raise WitnessError("malformed compaction anchor journal") from exc
            if statement.get("schema") != 1 or statement.get("kind") != "gossip-compaction-anchor":
                raise WitnessError("malformed compaction anchor statement")
            digest = _entry_digest(statement)
            if env.get("entry_digest") != digest:
                raise WitnessError("compaction anchor integrity failure")
            try:
                epoch = int(statement["snapshot_epoch"])
                journal_sequence = int(statement["journal_sequence"])
                prefix_bytes = int(statement["journal_prefix_bytes"])
            except Exception as exc:
                raise WitnessError("malformed compaction anchor statement") from exc
            if epoch != previous_epoch + 1 or statement.get("previous_anchor_digest") != previous_digest:
                raise WitnessError("compaction anchor chain failure")
            if journal_sequence <= previous_sequence or prefix_bytes < previous_prefix_bytes:
                raise WitnessError("compaction anchor rollback detected")
            _verify_statement(statement, signatures, registry, label="compaction anchor")
            out.append({"statement": statement, "signatures": signatures, "entry_digest": digest})
            previous_digest = digest
            previous_epoch = epoch
            previous_sequence = journal_sequence
            previous_prefix_bytes = prefix_bytes
        return out

    @staticmethod
    def _write_snapshot_exclusive(path, envelope):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise WitnessError("compaction snapshot already exists")
        data = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
        try:
            with target.open("xb") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            _fsync_directory(target.parent)
        except WitnessError:
            raise
        except Exception as exc:
            try:
                if target.exists():
                    target.unlink()
            except OSError:
                pass
            raise WitnessError("compaction snapshot persistence failed") from exc

    @staticmethod
    def _append_anchor_envelope(anchor_path, envelope):
        target = Path(anchor_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".append.tmp")
        try:
            prior = target.read_bytes() if target.exists() else b""
            if prior and not prior.endswith(b"\n"):
                raise WitnessError("malformed compaction anchor journal")
            try:
                statement = dict(envelope["statement"])
                expected_previous = statement.get("previous_anchor_digest")
                expected_epoch = int(statement["snapshot_epoch"])
                if prior:
                    last = json.loads(prior.rstrip(b"\n").split(b"\n")[-1])
                    current_previous = last.get("entry_digest")
                    current_epoch = int(last["statement"]["snapshot_epoch"])
                else:
                    current_previous = None
                    current_epoch = 0
            except WitnessError:
                raise
            except Exception as exc:
                raise WitnessError("malformed compaction anchor journal") from exc
            if current_previous != expected_previous or expected_epoch != current_epoch + 1:
                raise WitnessError("compaction anchor changed during commit")
            line = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
            with tmp.open("wb") as fh:
                fh.write(prior)
                fh.write(line)
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

    @staticmethod
    def _acquire_compaction_lock(anchor_path):
        anchor = Path(anchor_path)
        anchor.parent.mkdir(parents=True, exist_ok=True)
        lock = anchor.with_name(anchor.name + ".compaction.lock")
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise WitnessError("compaction already in progress") from exc
        except OSError as exc:
            raise WitnessError("unable to acquire compaction lock") from exc
        try:
            os.write(fd, (str(os.getpid()) + "\n").encode("ascii"))
            os.fsync(fd)
        finally:
            os.close(fd)
        _fsync_directory(lock.parent)
        return lock

    @staticmethod
    def _release_compaction_lock(lock):
        try:
            Path(lock).unlink()
            _fsync_directory(Path(lock).parent)
        except OSError:
            # A stale lock is fail-closed for future compactions and can be
            # removed only after an operator verifies no writer is active.
            pass

    def compact(self, snapshot_path, anchor_path, witnesses):
        """Create a new immutable signed replay snapshot and commit it to the anchor chain.

        The gossip journal is intentionally *not* truncated. This keeps legacy
        ``load()`` and forensic replay fully backward compatible while
        ``load_compacted()`` can seek directly to the signed prefix boundary.
        """
        snapshot_path = Path(snapshot_path)
        anchor_path = Path(anchor_path)
        if snapshot_path.exists():
            raise WitnessError("compaction snapshot already exists")
        lock = self._acquire_compaction_lock(anchor_path)
        try:
            trusted_time = None
            if hasattr(self.registry, "assert_current_policy_fresh"):
                trusted_time = self.registry.assert_current_policy_fresh()
            # Strict full replay is the admission gate for creating a compacted view.
            disk = type(self).load(self.path, self.registry)
            if disk.sequence != self.sequence or disk.last_digest != self.last_digest:
                raise WitnessError("journal state changed; reload before compaction")
            if disk.sequence < 1 or disk.last_digest is None:
                raise WitnessError("cannot compact empty gossip journal")
            try:
                journal_bytes = self.path.read_bytes()
            except Exception as exc:
                raise WitnessError("unable to read gossip journal") from exc
            if not journal_bytes.endswith(b"\n"):
                raise WitnessError("cannot compact non-canonical gossip journal tail")

            anchors = self._read_anchor_chain(anchor_path, self.registry)
            latest_anchor = anchors[-1] if anchors else None
            previous_anchor_digest = latest_anchor["entry_digest"] if latest_anchor else None
            previous_sequence = int(latest_anchor["statement"]["journal_sequence"]) if latest_anchor else 0
            if disk.sequence <= previous_sequence:
                raise WitnessError("compaction requires journal advancement")
            snapshot_epoch = (int(latest_anchor["statement"]["snapshot_epoch"]) + 1) if latest_anchor else 1

            latest_by_log = {}
            for cp in disk.store.export():
                latest_by_log[str(cp["log_id"])] = dict(cp)
            latest_receipts = [latest_by_log[k] for k in sorted(latest_by_log)]

            snapshot_body = {
                "schema": 1,
                "kind": "gossip-compaction-snapshot",
                "snapshot_epoch": snapshot_epoch,
                "journal_sequence": disk.sequence,
                "journal_last_digest": disk.last_digest,
                "journal_prefix_bytes": len(journal_bytes),
                "journal_prefix_sha256": _sha256_bytes(journal_bytes),
                "latest_receipts": latest_receipts,
            }
            if trusted_time is not None:
                snapshot_body["trusted_time"] = trusted_time
            statement = _policy_bind(snapshot_body, self.registry)
            signatures = _sign_statement(statement, witnesses, self.registry, label="compaction snapshot")
            snapshot_digest = _entry_digest(statement)
            snapshot_envelope = {
                "statement": statement,
                "signatures": signatures,
                "statement_digest": snapshot_digest,
            }

            anchor_body = {
                "schema": 1,
                "kind": "gossip-compaction-anchor",
                "snapshot_epoch": snapshot_epoch,
                "previous_anchor_digest": previous_anchor_digest,
                "snapshot_digest": snapshot_digest,
                "journal_sequence": disk.sequence,
                "journal_last_digest": disk.last_digest,
                "journal_prefix_bytes": len(journal_bytes),
                "journal_prefix_sha256": statement["journal_prefix_sha256"],
            }
            if trusted_time is not None:
                anchor_body["trusted_time"] = trusted_time
            anchor_statement = _policy_bind(anchor_body, self.registry)
            anchor_signatures = _sign_statement(anchor_statement, witnesses, self.registry, label="compaction anchor")
            anchor_digest = _entry_digest(anchor_statement)
            anchor_envelope = {
                "statement": anchor_statement,
                "signatures": anchor_signatures,
                "entry_digest": anchor_digest,
            }

            # Publication order is snapshot first, anchor commit second. A crash or
            # I/O failure between them leaves at most an orphan immutable snapshot;
            # the prior anchor chain remains authoritative.
            self._write_snapshot_exclusive(snapshot_path, snapshot_envelope)
            try:
                self._append_anchor_envelope(anchor_path, anchor_envelope)
            except Exception as exc:
                raise WitnessError("compaction anchor persistence failed") from exc

            return {
                "snapshot_epoch": snapshot_epoch,
                "journal_sequence": disk.sequence,
                "journal_last_digest": disk.last_digest,
                "journal_prefix_bytes": len(journal_bytes),
                "journal_prefix_sha256": statement["journal_prefix_sha256"],
                "snapshot_digest": snapshot_digest,
                "anchor_digest": anchor_digest,
                "snapshot_path": str(snapshot_path),
                "anchor_path": str(anchor_path),
            }
        finally:
            self._release_compaction_lock(lock)

    @classmethod
    def load_compacted(
        cls,
        path,
        snapshot_path,
        anchor_path,
        registry,
        *,
        minimum_snapshot_epoch=None,
        expected_anchor_digest=None,
    ):
        """Load from a signed prefix snapshot, then replay only the journal suffix.

        ``minimum_snapshot_epoch`` and ``expected_anchor_digest`` are optional
        externally pinned trust floors. They detect rollback even if an attacker
        restores both the local snapshot and local anchor journal to an older,
        previously valid state. Without an external pin, the local anchor chain
        still rejects selecting an older snapshot than its latest entry, but no
        purely local format can detect rollback of *all* local trusted state.
        """
        if hasattr(registry, "assert_current_policy_fresh"):
            registry.assert_current_policy_fresh()
        p = Path(path)
        sp = Path(snapshot_path)
        try:
            env = json.loads(sp.read_text())
            statement = dict(env["statement"])
            signatures = list(env["signatures"])
        except Exception as exc:
            raise WitnessError("malformed compaction snapshot") from exc
        if statement.get("schema") != 1 or statement.get("kind") != "gossip-compaction-snapshot":
            raise WitnessError("malformed compaction snapshot statement")
        snapshot_digest = _entry_digest(statement)
        if env.get("statement_digest") != snapshot_digest:
            raise WitnessError("compaction snapshot integrity failure")
        _verify_statement(statement, signatures, registry, label="compaction snapshot")

        anchors = cls._read_anchor_chain(anchor_path, registry)
        if not anchors:
            raise WitnessError("compaction snapshot is not anchored")
        latest_anchor = anchors[-1]
        ast = latest_anchor["statement"]
        anchor_digest = latest_anchor["entry_digest"]
        try:
            snapshot_epoch = int(statement["snapshot_epoch"])
            latest_epoch = int(ast["snapshot_epoch"])
        except Exception as exc:
            raise WitnessError("malformed compaction epoch") from exc
        if minimum_snapshot_epoch is not None and snapshot_epoch < int(minimum_snapshot_epoch):
            raise WitnessError("compaction below minimum snapshot epoch")
        if expected_anchor_digest is not None and anchor_digest != str(expected_anchor_digest):
            raise WitnessError("compaction anchor pin mismatch")
        if latest_epoch != snapshot_epoch or ast.get("snapshot_digest") != snapshot_digest:
            raise WitnessError("snapshot is not latest anchored compaction")

        for field in (
            "journal_sequence",
            "journal_last_digest",
            "journal_prefix_bytes",
            "journal_prefix_sha256",
        ):
            if ast.get(field) != statement.get(field):
                raise WitnessError("compaction snapshot/anchor mismatch")
        if ast.get("trusted_time") != statement.get("trusted_time"):
            raise WitnessError("compaction snapshot/anchor trusted-time mismatch")

        try:
            data = p.read_bytes()
            prefix_bytes = int(statement["journal_prefix_bytes"])
            prefix_hash = str(statement["journal_prefix_sha256"])
            base_sequence = int(statement["journal_sequence"])
            base_digest = statement["journal_last_digest"]
            latest_receipts = list(statement["latest_receipts"])
        except Exception as exc:
            raise WitnessError("malformed compaction snapshot state") from exc
        if prefix_bytes < 0 or len(data) < prefix_bytes:
            raise WitnessError("gossip journal prefix rollback/truncation detected")
        prefix = data[:prefix_bytes]
        if _sha256_bytes(prefix) != prefix_hash:
            raise WitnessError("gossip journal prefix integrity failure")

        obj = cls(p, registry)
        # The snapshot contains only the latest authenticated receipt per log;
        # this is sufficient to preserve future rollback/equivocation checks.
        for cp in latest_receipts:
            cp = dict(cp)
            obj._preflight(cp, historical=True)
            obj.store.observe(cp)
        obj.sequence = base_sequence
        obj.last_digest = base_digest

        suffix = data[prefix_bytes:]
        if suffix:
            try:
                lines = suffix.decode("utf-8").splitlines()
            except Exception as exc:
                raise WitnessError("malformed gossip journal suffix") from exc
            cls._replay_lines(obj, lines, sequence=base_sequence, previous=base_digest)

        obj.compaction_report = {
            "snapshot_epoch": snapshot_epoch,
            "journal_sequence": base_sequence,
            "journal_prefix_bytes": prefix_bytes,
            "journal_prefix_sha256": prefix_hash,
            "snapshot_digest": snapshot_digest,
            "anchor_digest": anchor_digest,
            "suffix_bytes": len(suffix),
        }
        return obj

    def latest(self, log_id):
        return self.store.latest(log_id)
