from __future__ import annotations
import contextlib
import errno

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Iterable
import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def priority_score(c: dict[str, Any]) -> float:
    """Transparent leverage score. Inputs are expected in [0, 1]."""
    benefit_terms = [
        clamp01(c.get("impact", 0.0)),
        clamp01(c.get("centrality", 0.0)),
        clamp01(c.get("uncertainty_reduction", 0.0)),
        clamp01(c.get("reusability", 0.0)),
        clamp01(c.get("failure_pressure", 0.0)),
        clamp01(c.get("evidence_gap", 0.0)),
    ]
    # Geometric mean discourages a candidate from ranking highly when one
    # critical benefit dimension is near zero.
    product = 1.0
    for v in benefit_terms:
        product *= max(v, 1e-6)
    benefit = product ** (1.0 / len(benefit_terms))

    cost = max(0.05, clamp01(c.get("cost", 0.5)))
    regression = clamp01(c.get("regression_risk", 0.0))
    duplicate = clamp01(c.get("duplication_risk", 0.0))
    penalty = cost * (1.0 + regression) * (1.0 + duplicate)
    return benefit / penalty


@dataclass(frozen=True)
class SnapshotEntry:
    path: str
    size: int
    mtime_ns: int
    sha256: str


class JanusTwin:
    def __init__(self, db_path: str | os.PathLike[str]):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        self.conn.close()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;

            CREATE TABLE IF NOT EXISTS facts (
                fact_id TEXT PRIMARY KEY,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                value_json TEXT NOT NULL,
                valid_from TEXT NOT NULL,
                valid_to TEXT,
                known_at TEXT NOT NULL,
                source TEXT NOT NULL,
                source_hash TEXT,
                confidence TEXT NOT NULL DEFAULT 'reported',
                authority TEXT,
                supersedes TEXT,
                inserted_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS facts_sp_time
                ON facts(subject, predicate, valid_from, known_at);

            CREATE TABLE IF NOT EXISTS components (
                name TEXT PRIMARY KEY,
                authority TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS dependencies (
                src TEXT NOT NULL,
                dst TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'depends_on',
                PRIMARY KEY(src, dst, kind)
            );

            CREATE TABLE IF NOT EXISTS invariants (
                invariant_hash TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                source TEXT,
                inserted_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS candidates (
                candidate_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                metrics_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'proposed',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS snapshots (
                snapshot_id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                root TEXT NOT NULL,
                created_at TEXT NOT NULL,
                manifest_json TEXT NOT NULL,
                manifest_hash TEXT NOT NULL,
                git_head TEXT
            );

            CREATE TABLE IF NOT EXISTS proof_bundles (
                change_id TEXT PRIMARY KEY,
                bundle_json TEXT NOT NULL,
                bundle_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS proof_lifecycle_events (
                event_id TEXT PRIMARY KEY,
                change_id TEXT NOT NULL,
                status TEXT NOT NULL,
                known_at TEXT NOT NULL,
                actor TEXT NOT NULL,
                reason TEXT NOT NULL,
                superseded_by TEXT,
                inserted_at TEXT NOT NULL,
                FOREIGN KEY(change_id) REFERENCES proof_bundles(change_id)
            );
            CREATE INDEX IF NOT EXISTS proof_lifecycle_time
                ON proof_lifecycle_events(change_id, known_at, event_id);

            CREATE TABLE IF NOT EXISTS authority_precedence (
                subject_prefix TEXT NOT NULL,
                predicate TEXT NOT NULL,
                authority TEXT NOT NULL,
                rank INTEGER NOT NULL,
                PRIMARY KEY(subject_prefix, predicate, authority)
            );

            CREATE TABLE IF NOT EXISTS evidence_precedence (
                confidence TEXT PRIMARY KEY,
                rank INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS normalization_decisions (
                decision_id TEXT PRIMARY KEY,
                proposal_json TEXT NOT NULL,
                decision TEXT NOT NULL CHECK(decision IN ('approved','rejected')),
                decided_by TEXT NOT NULL,
                proof_refs_json TEXT NOT NULL,
                known_at TEXT NOT NULL,
                revoked_at TEXT,
                revoked_by TEXT,
                revocation_reason TEXT
            );

            CREATE TABLE IF NOT EXISTS signing_keys (
                key_id TEXT PRIMARY KEY,
                authority TEXT NOT NULL,
                public_key_b64 TEXT NOT NULL,
                valid_from TEXT NOT NULL,
                valid_to TEXT,
                known_at TEXT NOT NULL,
                revoked_at TEXT,
                revocation_reason TEXT
            );
            CREATE INDEX IF NOT EXISTS signing_keys_authority_time
                ON signing_keys(authority, valid_from, known_at);

            CREATE TABLE IF NOT EXISTS authorization_policies (
                policy_id TEXT PRIMARY KEY,
                subsystem TEXT NOT NULL,
                evidence_class TEXT NOT NULL,
                authorities_json TEXT NOT NULL,
                threshold INTEGER NOT NULL,
                valid_from TEXT NOT NULL,
                valid_to TEXT,
                known_at TEXT NOT NULL,
                revoked_at TEXT,
                revoked_by TEXT,
                revocation_reason TEXT
            );
            CREATE INDEX IF NOT EXISTS authorization_policy_scope_time
                ON authorization_policies(subsystem, evidence_class, valid_from, known_at);

            CREATE TABLE IF NOT EXISTS signing_key_rotations (
                predecessor_key_id TEXT NOT NULL, successor_key_id TEXT NOT NULL,
                rotated_at TEXT NOT NULL, known_at TEXT NOT NULL,
                PRIMARY KEY(predecessor_key_id, successor_key_id)
            );
            CREATE TABLE IF NOT EXISTS authority_delegations (
                delegation_id TEXT PRIMARY KEY, principal_authority TEXT NOT NULL, delegate_authority TEXT NOT NULL,
                subsystem TEXT NOT NULL, evidence_class TEXT NOT NULL, valid_from TEXT NOT NULL, valid_to TEXT,
                known_at TEXT NOT NULL, revoked_at TEXT, revoked_by TEXT, revocation_reason TEXT
            );

            CREATE TABLE IF NOT EXISTS sync_sessions (
                session_id TEXT PRIMARY KEY,
                change_id TEXT NOT NULL,
                causal_root TEXT NOT NULL,
                trust_bundle_digest TEXT NOT NULL,
                authorization_decision_digest TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('staged','completed','failed')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                receipt_json TEXT,
                failure_reason TEXT,
                receiver_state_digest TEXT
            );
            CREATE TABLE IF NOT EXISTS sync_session_chunks (
                session_id TEXT NOT NULL, evidence_domain TEXT NOT NULL, chunk_hash TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('missing','acquired','verified')), payload_json TEXT, updated_at TEXT NOT NULL,
                PRIMARY KEY(session_id,evidence_domain,chunk_hash)
            );
            CREATE TABLE IF NOT EXISTS joint_receipts (
                receipt_digest TEXT PRIMARY KEY, session_id TEXT NOT NULL, previous_receipt_digest TEXT,
                signer_authority TEXT, signature_b64 TEXT, receipt_json TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS promotion_fence_state (
                singleton INTEGER PRIMARY KEY CHECK(singleton=1), current_epoch INTEGER NOT NULL
            );
            INSERT OR IGNORE INTO promotion_fence_state(singleton,current_epoch) VALUES (1,0);
            CREATE TABLE IF NOT EXISTS sync_promotion_guards (
                session_id TEXT PRIMARY KEY, fence_epoch INTEGER NOT NULL, expected_receipt_head TEXT, acquired_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS promotion_leases (
                session_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, fence_epoch INTEGER NOT NULL,
                acquired_at TEXT NOT NULL, expires_at TEXT NOT NULL, renewed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS receipt_fork_evidence (
                evidence_digest TEXT PRIMARY KEY, session_id TEXT NOT NULL, fence_epoch INTEGER NOT NULL,
                expected_head TEXT, observed_head TEXT, detected_at TEXT NOT NULL, evidence_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS promotion_journal (
                session_id TEXT PRIMARY KEY, fence_epoch INTEGER NOT NULL, owner_id TEXT NOT NULL,
                expected_receipt_head TEXT, receiver_state_digest TEXT NOT NULL, status TEXT NOT NULL,
                prepared_at TEXT NOT NULL, resolved_at TEXT, receipt_digest TEXT, failure_reason TEXT
            );
            CREATE TABLE IF NOT EXISTS recovery_certificates (
                certificate_digest TEXT PRIMARY KEY, session_id TEXT NOT NULL, outcome TEXT NOT NULL,
                certificate_json TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS storage_quarantine (
                evidence_digest TEXT PRIMARY KEY, session_id TEXT NOT NULL, fault_class TEXT NOT NULL,
                original_stage_path TEXT NOT NULL, quarantine_path TEXT NOT NULL, stage_sha256 TEXT,
                integrity_result TEXT, detected_at TEXT NOT NULL, evidence_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS storage_fault_audit (
                audit_digest TEXT PRIMARY KEY, fault_evidence_digest TEXT NOT NULL, previous_audit_digest TEXT,
                signer_authority TEXT NOT NULL, signature_b64 TEXT NOT NULL, audit_json TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS forensic_proof_links (
                link_digest TEXT PRIMARY KEY, audit_digest TEXT NOT NULL, session_id TEXT NOT NULL,
                recovery_certificate_digest TEXT NOT NULL, session_receipt_digest TEXT, receipt_head_digest TEXT,
                fence_epoch INTEGER, previous_link_digest TEXT, signer_authority TEXT NOT NULL, signature_b64 TEXT NOT NULL,
                link_json TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS clock_policy (
                singleton INTEGER PRIMARY KEY CHECK(singleton=1), max_clock_skew_seconds INTEGER NOT NULL
            );
            INSERT OR IGNORE INTO clock_policy(singleton,max_clock_skew_seconds) VALUES (1,2);

            CREATE TABLE IF NOT EXISTS negative_knowledge (
                fingerprint TEXT PRIMARY KEY,
                family TEXT NOT NULL,
                context_json TEXT NOT NULL,
                rejection_reason TEXT NOT NULL,
                retry_condition TEXT,
                evidence_json TEXT NOT NULL,
                known_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS truth_revalidation_receipt_chain (
                sequence INTEGER PRIMARY KEY,
                entry_digest TEXT NOT NULL UNIQUE,
                previous_entry_digest TEXT,
                truth_receipt_digest TEXT NOT NULL,
                entry_json TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def add_fact(self, fact: dict[str, Any]) -> str:
        canonical = {
            "subject": fact["subject"],
            "predicate": fact["predicate"],
            "value": fact.get("value"),
            "valid_from": fact["valid_from"],
            "valid_to": fact.get("valid_to"),
            "known_at": fact["known_at"],
            "source": fact["source"],
            "source_hash": fact.get("source_hash"),
            "confidence": fact.get("confidence", "reported"),
            "authority": fact.get("authority"),
            "supersedes": fact.get("supersedes"),
        }
        fact_id = sha256_bytes(stable_json(canonical).encode())
        self.conn.execute(
            """INSERT OR IGNORE INTO facts
            (fact_id,subject,predicate,value_json,valid_from,valid_to,known_at,source,source_hash,confidence,authority,supersedes,inserted_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                fact_id,
                canonical["subject"],
                canonical["predicate"],
                stable_json(canonical["value"]),
                canonical["valid_from"],
                canonical["valid_to"],
                canonical["known_at"],
                canonical["source"],
                canonical["source_hash"],
                canonical["confidence"],
                canonical["authority"],
                canonical["supersedes"],
                utcnow(),
            ),
        )
        self.conn.commit()
        return fact_id

    def add_component(self, name: str, authority: str, metadata: dict[str, Any] | None = None) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO components(name,authority,metadata_json) VALUES (?,?,?)",
            (name, authority, stable_json(metadata or {})),
        )
        self.conn.commit()

    def add_dependency(self, src: str, dst: str, kind: str = "depends_on") -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO dependencies(src,dst,kind) VALUES (?,?,?)",
            (src, dst, kind),
        )
        self.conn.commit()

    def add_invariant(self, text: str, source: str | None = None) -> str:
        h = sha256_bytes(text.strip().encode())
        self.conn.execute(
            "INSERT OR IGNORE INTO invariants(invariant_hash,text,source,inserted_at) VALUES (?,?,?,?)",
            (h, text.strip(), source, utcnow()),
        )
        self.conn.commit()
        return h

    def add_candidate(self, candidate: dict[str, Any]) -> None:
        cid = candidate["id"]
        title = candidate["title"]
        metrics = {k: v for k, v in candidate.items() if k not in {"id", "title", "status"}}
        self.conn.execute(
            "INSERT OR REPLACE INTO candidates(candidate_id,title,metrics_json,status,created_at) VALUES (?,?,?,?,?)",
            (cid, title, stable_json(metrics), candidate.get("status", "proposed"), utcnow()),
        )
        self.conn.commit()

    def seed_manifest(self, path: str | os.PathLike[str]) -> None:
        data = json.loads(Path(path).read_text())
        for c in data.get("components", []):
            self.add_component(c["name"], c["authority"], {k: v for k, v in c.items() if k not in {"name", "authority", "depends_on"}})
            for dep in c.get("depends_on", []):
                self.add_dependency(c["name"], dep)
        for policy in data.get("evidence_precedence", []):
            self.set_evidence_precedence(policy["confidence"], policy["rank"])
        for fact in data.get("facts", []):
            self.add_fact(fact)
        for inv in data.get("invariants", []):
            self.add_invariant(inv, source=str(path))
        for cand in data.get("candidates", []):
            self.add_candidate(cand)

    def facts_as_known_at(self, known_at: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM facts WHERE known_at <= ? ORDER BY subject,predicate,valid_from,known_at,fact_id",
            (known_at,),
        ).fetchall()
        return [self._fact_row(r) for r in rows]

    def facts_as_of(self, valid_at: str, known_at: str) -> list[dict[str, Any]]:
        """Reconstruct authoritative state at project time *valid_at* using only
        information learned by *known_at*.

        This is the core bitemporal query: a fact must already be valid in project
        time, must not have expired, and must have been known to the project by the
        requested knowledge boundary. Among eligible facts, the latest valid/known
        fact wins unless it was explicitly superseded by another eligible fact.
        """
        # Fetch by start/knowledge boundary first. Approved normalization overlays
        # may supply an effective end for otherwise open-ended source facts, so
        # validity filtering must happen after overlay resolution.
        rows = self.conn.execute(
            """SELECT * FROM facts
               WHERE valid_from <= ? AND known_at <= ?
               ORDER BY subject,predicate,valid_from DESC,known_at DESC,fact_id DESC""",
            (valid_at, known_at),
        ).fetchall()
        overlay_ends = {
            o["close_fact_id"]: o["effective_valid_to"]
            for o in self.verified_normalization_overlays(known_at)
        }
        filtered = []
        for r in rows:
            source_end = r["valid_to"]
            overlay_end = overlay_ends.get(r["fact_id"])
            effective_end = min(x for x in (source_end, overlay_end) if x is not None) if (source_end or overlay_end) else None
            if effective_end is None or effective_end > valid_at:
                filtered.append(r)
        rows = filtered
        eligible_ids = {r["fact_id"] for r in rows}
        superseded = {
            r["supersedes"] for r in rows
            if r["supersedes"] and r["supersedes"] in eligible_ids
        }
        seen: set[tuple[str, str]] = set()
        out = []
        for r in rows:
            if r["fact_id"] in superseded:
                continue
            key = (r["subject"], r["predicate"])
            if key in seen:
                continue
            seen.add(key)
            out.append(self._fact_row(r))
        return sorted(out, key=lambda x: (x["subject"], x["predicate"]))

    def current_facts(self, valid_at: str | None = None) -> list[dict[str, Any]]:
        """Return current project state, respecting explicit validity intervals.

        ``valid_at`` makes tests/replays deterministic. When omitted, wall-clock UTC
        is used and all facts learned so far are eligible by knowledge time.
        """
        boundary = valid_at or utcnow()
        return self.facts_as_of(boundary, "9999-12-31T23:59:59.999999Z")

    def set_authority_precedence(self, subject_prefix: str, predicate: str, authority: str, rank: int) -> None:
        """Register explicit conflict-resolution precedence. Higher rank wins.

        JANUS never invents authority ordering: without an explicit policy, a
        temporal conflict is quarantined rather than silently resolved.
        """
        self.conn.execute(
            "INSERT OR REPLACE INTO authority_precedence(subject_prefix,predicate,authority,rank) VALUES (?,?,?,?)",
            (subject_prefix, predicate, authority, int(rank)),
        )
        self.conn.commit()

    def set_evidence_precedence(self, confidence: str, rank: int) -> None:
        """Register explicit evidence-strength precedence. Higher rank wins.

        Confidence labels have no built-in ordering: JANUS will not assume that a
        label such as ``verified`` outranks ``reported`` unless policy says so.
        """
        self.conn.execute(
            "INSERT OR REPLACE INTO evidence_precedence(confidence,rank) VALUES (?,?)",
            (confidence, int(rank)),
        )
        self.conn.commit()

    def _evidence_rank(self, confidence: str | None) -> int | None:
        if not confidence:
            return None
        row = self.conn.execute(
            "SELECT rank FROM evidence_precedence WHERE confidence=?", (confidence,)
        ).fetchone()
        return row[0] if row else None

    def _authority_rank(self, subject: str, predicate: str, authority: str | None) -> int | None:
        if not authority:
            return None
        rows = self.conn.execute(
            "SELECT subject_prefix,rank FROM authority_precedence WHERE predicate=? AND authority=?",
            (predicate, authority),
        ).fetchall()
        matches = [(len(r["subject_prefix"]), r["rank"]) for r in rows if subject == r["subject_prefix"] or subject.startswith(r["subject_prefix"] + ".")]
        return max(matches)[1] if matches else None

    @staticmethod
    def _intervals_overlap(a: sqlite3.Row, b: sqlite3.Row) -> bool:
        # ISO-8601 UTC timestamps sort lexicographically. None is open-ended.
        a_end = a["valid_to"] or "9999-12-31T23:59:59.999999Z"
        b_end = b["valid_to"] or "9999-12-31T23:59:59.999999Z"
        return a["valid_from"] < b_end and b["valid_from"] < a_end

    def _blast_radius(self, subject: str) -> list[str]:
        root = subject.split(".", 1)[0]
        reverse: dict[str, set[str]] = {}
        for r in self.conn.execute("SELECT src,dst FROM dependencies"):
            reverse.setdefault(r["dst"], set()).add(r["src"])
        seen: set[str] = set()
        frontier = list(reverse.get(root, set()))
        while frontier:
            node = frontier.pop()
            if node in seen:
                continue
            seen.add(node)
            frontier.extend(reverse.get(node, set()) - seen)
        return sorted(seen)

    def _adjudicate_facts(self, facts: Iterable[sqlite3.Row]) -> dict[str, Any]:
        """Single policy kernel for authority/evidence conflict adjudication.

        Authority always precedes evidence. Missing explicit policy fails closed
        to quarantine; JANUS never infers subsystem authority from labels.
        """
        rows = list(facts)
        ranked = [(self._authority_rank(r["subject"], r["predicate"], r["authority"]), r) for r in rows]
        known_ranks = [rank for rank, _ in ranked if rank is not None]
        if len(known_ranks) != len(ranked):
            return {"status": "quarantined", "reason": "authority_policy_missing"}
        top = max(known_ranks)
        winners = [r for rank, r in ranked if rank == top]
        if len(winners) == 1:
            w = winners[0]
            return {"status": "resolved", "reason": "explicit_authority_precedence", "winner_fact_id": w["fact_id"], "winner_authority": w["authority"], "winner_rank": top}
        evidence_ranked = [(self._evidence_rank(r["confidence"]), r) for r in winners]
        evidence_ranks = [rank for rank, _ in evidence_ranked if rank is not None]
        if len(evidence_ranks) != len(evidence_ranked):
            return {"status": "quarantined", "reason": "authority_tie"}
        evidence_top = max(evidence_ranks)
        evidence_winners = [r for rank, r in evidence_ranked if rank == evidence_top]
        if len(evidence_winners) != 1:
            return {"status": "quarantined", "reason": "authority_and_evidence_tie"}
        w = evidence_winners[0]
        return {"status": "resolved", "reason": "explicit_evidence_precedence", "winner_fact_id": w["fact_id"], "winner_authority": w["authority"], "winner_rank": top, "winner_evidence_rank": evidence_top}

    def temporal_conflicts(self) -> list[dict[str, Any]]:
        """Detect differing unsuperseded facts whose validity intervals overlap.

        Resolution is deliberately conservative. A winner is emitted only when
        explicit authority precedence exists and exactly one fact has the unique
        highest rank. Otherwise the conflict is quarantined for proof/review.
        """
        rows = self.conn.execute("SELECT * FROM facts ORDER BY subject,predicate,valid_from,known_at,fact_id").fetchall()
        superseded = {r["supersedes"] for r in rows if r["supersedes"]}
        active = [r for r in rows if r["fact_id"] not in superseded]
        out: list[dict[str, Any]] = []
        for i, a in enumerate(active):
            for b in active[i + 1:]:
                if (a["subject"], a["predicate"]) != (b["subject"], b["predicate"]):
                    continue
                if a["value_json"] == b["value_json"] or not self._intervals_overlap(a, b):
                    continue
                resolution = self._adjudicate_facts((a, b))
                out.append({
                    "kind": "overlap_conflict",
                    "subject": a["subject"],
                    "predicate": a["predicate"],
                    "overlap_from": max(a["valid_from"], b["valid_from"]),
                    "overlap_to": min(a["valid_to"] or "9999-12-31T23:59:59.999999Z", b["valid_to"] or "9999-12-31T23:59:59.999999Z"),
                    "facts": [self._fact_row(a), self._fact_row(b)],
                    "resolution": resolution,
                    "proof_required": resolution["status"] != "resolved",
                    "blast_radius": self._blast_radius(a["subject"]),
                })
        return out

    def temporal_conflicts_as_of(self, valid_at: str, known_at: str) -> list[dict[str, Any]]:
        """Replay unresolved/resolved conflicts at a bitemporal coordinate.

        Unlike :meth:`temporal_conflicts`, this is a point-in-time surface: only
        facts known by ``known_at`` and valid at ``valid_at`` participate, after
        applying only normalization overlays whose proofs are valid at ``known_at``.
        """
        overlays = self.verified_normalization_overlays(known_at)
        overlay_ends = {o["close_fact_id"]: o["effective_valid_to"] for o in overlays}
        rows = self.conn.execute(
            "SELECT * FROM facts WHERE valid_from<=? AND known_at<=? ORDER BY subject,predicate,valid_from,known_at,fact_id",
            (valid_at, known_at),
        ).fetchall()
        eligible = []
        for r in rows:
            source_end = r["valid_to"]
            overlay_end = overlay_ends.get(r["fact_id"])
            ends = [x for x in (source_end, overlay_end) if x is not None]
            effective_end = min(ends) if ends else None
            if effective_end is None or valid_at < effective_end:
                eligible.append(r)
        eligible_ids = {r["fact_id"] for r in eligible}
        superseded = {r["supersedes"] for r in eligible if r["supersedes"] in eligible_ids}
        active = [r for r in eligible if r["fact_id"] not in superseded]
        out: list[dict[str, Any]] = []
        for i, a in enumerate(active):
            for b in active[i + 1:]:
                if (a["subject"], a["predicate"]) != (b["subject"], b["predicate"]):
                    continue
                if a["value_json"] == b["value_json"]:
                    continue
                # At a point-in-time both rows are already interval-eligible, so
                # differing values form a replay conflict regardless of their raw
                # interval boundaries. Reuse the same explicit policy hierarchy.
                resolution = self._adjudicate_facts((a, b))
                related = [o for o in overlays if o["close_fact_id"] in {a["fact_id"], b["fact_id"]} or o["successor_fact_id"] in {a["fact_id"], b["fact_id"]}]
                out.append({
                    "kind": "bitemporal_replay_conflict",
                    "subject": a["subject"], "predicate": a["predicate"],
                    "replay": {"valid_at": valid_at, "known_at": known_at},
                    "facts": [self._fact_row(a), self._fact_row(b)],
                    "resolution": resolution,
                    "proof_required": resolution["status"] != "resolved",
                    "blast_radius": self._blast_radius(a["subject"]),
                    "normalization_lineage": related,
                })
        return out

    def temporal_normalization_proposals(self) -> list[dict[str, Any]]:
        """Suggest safe-looking interval closures without mutating historical facts.

        A proposal requires same subject/predicate, same source lineage, same
        authority, an open-ended older fact, and a later differing value. This is
        evidence for review, never an automatic rewrite of project history.
        """
        rows = self.conn.execute(
            "SELECT * FROM facts ORDER BY subject,predicate,valid_from,known_at,fact_id"
        ).fetchall()
        out: list[dict[str, Any]] = []
        for i, old in enumerate(rows):
            if old["valid_to"] is not None:
                continue
            for new in rows[i + 1:]:
                if (old["subject"], old["predicate"]) != (new["subject"], new["predicate"]):
                    continue
                if new["valid_from"] <= old["valid_from"] or new["value_json"] == old["value_json"]:
                    continue
                if old["source"] != new["source"] or old["authority"] != new["authority"]:
                    continue
                out.append({
                    "kind": "interval_closure_proposal",
                    "subject": old["subject"],
                    "predicate": old["predicate"],
                    "close_fact_id": old["fact_id"],
                    "successor_fact_id": new["fact_id"],
                    "proposed_valid_to": new["valid_from"],
                    "basis": "same_source_and_authority_later_differing_value",
                    "mutation_applied": False,
                    "proof_required": True,
                })
                break
        return out

    def record_normalization_decision(self, proposal: dict[str, Any], decision: str, decided_by: str, proof_refs: list[str], known_at: str) -> dict[str, Any]:
        """Append an auditable approval/rejection without mutating source facts."""
        if decision not in {"approved", "rejected"}:
            raise ValueError("decision must be approved or rejected")
        if not proof_refs:
            raise ValueError("normalization decisions require at least one proof reference")
        canonical = {
            "proposal": proposal, "decision": decision, "decided_by": decided_by,
            "proof_refs": sorted(set(proof_refs)), "known_at": known_at,
        }
        decision_id = sha256_bytes(stable_json(canonical).encode())
        self.conn.execute(
            "INSERT OR IGNORE INTO normalization_decisions(decision_id,proposal_json,decision,decided_by,proof_refs_json,known_at) VALUES (?,?,?,?,?,?)",
            (decision_id, stable_json(proposal), decision, decided_by, stable_json(canonical["proof_refs"]), known_at),
        )
        self.conn.commit()
        return {"decision_id": decision_id, **canonical}

    def revoke_normalization_decision(self, decision_id: str, revoked_by: str, reason: str, revoked_at: str) -> None:
        row = self.conn.execute("SELECT decision_id FROM normalization_decisions WHERE decision_id=?", (decision_id,)).fetchone()
        if not row:
            raise KeyError(decision_id)
        self.conn.execute(
            "UPDATE normalization_decisions SET revoked_at=?,revoked_by=?,revocation_reason=? WHERE decision_id=? AND revoked_at IS NULL",
            (revoked_at, revoked_by, reason, decision_id),
        )
        self.conn.commit()

    def record_proof_lifecycle_event(self, change_id: str, status: str, known_at: str, actor: str, reason: str, superseded_by: str | None = None) -> dict[str, Any]:
        """Append a knowledge-time proof status transition without mutating its bundle."""
        allowed = {"proved", "integrated", "revoked", "superseded"}
        if status not in allowed:
            raise ValueError(f"unsupported proof lifecycle status: {status}")
        if not self.conn.execute("SELECT 1 FROM proof_bundles WHERE change_id=?", (change_id,)).fetchone():
            raise KeyError(change_id)
        if status == "superseded":
            if not superseded_by:
                raise ValueError("superseded lifecycle events require superseded_by")
            # Missing replacement targets are preserved as audit evidence and surfaced by
            # proof_provenance_graph(); this keeps Run 007 handoffs backward compatible.
            # Reject only cycles whose referenced nodes are already known.
            edges = {r["change_id"]: r["superseded_by"] for r in self.conn.execute(
                "SELECT change_id,superseded_by FROM proof_lifecycle_events WHERE status='superseded' AND superseded_by IS NOT NULL ORDER BY known_at,event_id"
            ).fetchall()}
            cur = superseded_by
            seen = {change_id}
            while cur in edges:
                if cur in seen:
                    raise ValueError("proof supersession cycle detected")
                seen.add(cur); cur = edges[cur]
            if cur == change_id:
                raise ValueError("proof supersession cycle detected")
        same_boundary = self.conn.execute(
            "SELECT status,superseded_by FROM proof_lifecycle_events WHERE change_id=? AND known_at=?",
            (change_id, known_at),
        ).fetchall()
        if any((r["status"], r["superseded_by"]) != (status, superseded_by) for r in same_boundary):
            raise ValueError("conflicting proof lifecycle event at identical knowledge boundary")
        canonical = {
            "change_id": change_id, "status": status, "known_at": known_at,
            "actor": actor, "reason": reason, "superseded_by": superseded_by,
        }
        event_id = sha256_bytes(stable_json(canonical).encode())
        self.conn.execute(
            "INSERT OR IGNORE INTO proof_lifecycle_events(event_id,change_id,status,known_at,actor,reason,superseded_by,inserted_at) VALUES (?,?,?,?,?,?,?,?)",
            (event_id, change_id, status, known_at, actor, reason, superseded_by, utcnow()),
        )
        self.conn.commit()
        return {"event_id": event_id, **canonical}

    def proof_lifecycle_events(self, change_id: str | None = None) -> list[dict[str, Any]]:
        if change_id is None:
            rows = self.conn.execute("SELECT * FROM proof_lifecycle_events ORDER BY known_at,event_id").fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM proof_lifecycle_events WHERE change_id=? ORDER BY known_at,event_id", (change_id,)).fetchall()
        return [dict(r) for r in rows]

    def _proof_effective_status(self, change_id: str, known_at: str | None = None) -> tuple[str | None, dict[str, Any] | None]:
        row = self.conn.execute("SELECT status FROM proof_bundles WHERE change_id=?", (change_id,)).fetchone()
        if not row:
            return None, None
        if known_at is None:
            event = self.conn.execute(
                "SELECT * FROM proof_lifecycle_events WHERE change_id=? ORDER BY known_at DESC,event_id DESC LIMIT 1",
                (change_id,),
            ).fetchone()
        else:
            event = self.conn.execute(
                "SELECT * FROM proof_lifecycle_events WHERE change_id=? AND known_at<=? ORDER BY known_at DESC,event_id DESC LIMIT 1",
                (change_id, known_at),
            ).fetchone()
        return (event["status"] if event else row["status"], dict(event) if event else None)

    def _verify_proof_ref(self, proof_ref: str, known_at: str | None = None) -> dict[str, Any]:
        """Verify a bound proof and its lifecycle at an optional knowledge boundary."""
        parts = proof_ref.split(":", 2)
        if len(parts) != 3 or parts[0] != "proof":
            return {"proof_ref": proof_ref, "verified": False, "reason": "unbound_proof_reference"}
        change_id, expected_hash = parts[1], parts[2]
        row = self.conn.execute(
            "SELECT bundle_hash,status FROM proof_bundles WHERE change_id=?", (change_id,)
        ).fetchone()
        if not row:
            return {"proof_ref": proof_ref, "verified": False, "reason": "proof_bundle_missing"}
        if row["bundle_hash"] != expected_hash:
            return {"proof_ref": proof_ref, "verified": False, "reason": "proof_hash_mismatch"}
        effective_status, lifecycle_event = self._proof_effective_status(change_id, known_at)
        if effective_status not in {"proved", "integrated"}:
            return {
                "proof_ref": proof_ref, "verified": False,
                "reason": f"proof_status_{effective_status or 'missing'}",
                "change_id": change_id, "effective_status": effective_status,
                "lifecycle_event": lifecycle_event,
            }
        return {
            "proof_ref": proof_ref, "verified": True, "reason": "hash_and_status_verified",
            "change_id": change_id, "effective_status": effective_status,
            "lifecycle_event": lifecycle_event,
        }

    def verified_normalization_overlays(self, known_at: str = "9999-12-31T23:59:59.999999Z") -> list[dict[str, Any]]:
        """Return only overlays backed by integrity-checked proof bundles."""
        out = []
        for overlay in self.normalization_overlays(known_at):
            checks = [self._verify_proof_ref(ref, known_at) for ref in overlay["proof_refs"]]
            if checks and all(c["verified"] for c in checks):
                out.append({**overlay, "proof_integrity": "verified", "proof_checks": checks})
        return out

    def normalization_overlays(self, known_at: str = "9999-12-31T23:59:59.999999Z") -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM normalization_decisions WHERE decision='approved' AND known_at<=? AND (revoked_at IS NULL OR revoked_at>?) ORDER BY known_at,decision_id",
            (known_at, known_at),
        ).fetchall()
        out = []
        for r in rows:
            p = json.loads(r["proposal_json"])
            out.append({
                "decision_id": r["decision_id"], "close_fact_id": p["close_fact_id"],
                "successor_fact_id": p["successor_fact_id"], "effective_valid_to": p["proposed_valid_to"],
                "decided_by": r["decided_by"], "proof_refs": json.loads(r["proof_refs_json"]),
                "known_at": r["known_at"], "immutable_source_facts": True,
            })
        return out

    def contradictions(self) -> list[dict[str, Any]]:
        """Find simultaneous unsuperseded differing values at the same valid_from boundary.

        Historical evolution at different valid_from timestamps is not a contradiction.
        """
        rows = self.conn.execute("SELECT * FROM facts ORDER BY subject,predicate,valid_from,known_at").fetchall()
        groups: dict[tuple[str, str, str], list[sqlite3.Row]] = {}
        superseded = {r["supersedes"] for r in rows if r["supersedes"]}
        for r in rows:
            if r["fact_id"] in superseded:
                continue
            groups.setdefault((r["subject"], r["predicate"], r["valid_from"]), []).append(r)
        out = []
        for (subject, predicate, valid_from), rs in groups.items():
            vals = {r["value_json"] for r in rs}
            if len(vals) > 1:
                out.append(
                    {
                        "subject": subject,
                        "predicate": predicate,
                        "valid_from": valid_from,
                        "facts": [self._fact_row(r) for r in rs],
                    }
                )
        return out

    def prioritized_candidates(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM candidates WHERE status IN ('proposed','active')").fetchall()
        out = []
        for r in rows:
            metrics = json.loads(r["metrics_json"])
            out.append(
                {
                    "id": r["candidate_id"],
                    "title": r["title"],
                    "status": r["status"],
                    "metrics": metrics,
                    "score": priority_score(metrics),
                }
            )
        return sorted(out, key=lambda x: (-x["score"], x["id"]))

    def _git_head(self, root: Path) -> str | None:
        try:
            p = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            )
            return p.stdout.strip() or None
        except Exception:
            return None

    def build_manifest(self, root: str | os.PathLike[str]) -> dict[str, Any]:
        rootp = Path(root).resolve()
        entries: list[dict[str, Any]] = []
        skip_parts = {".git", ".janus", "__pycache__", ".pytest_cache", ".mypy_cache"}
        for p in sorted(rootp.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(rootp)
            if any(part in skip_parts for part in rel.parts):
                continue
            stat = p.stat()
            e = SnapshotEntry(
                path=rel.as_posix(),
                size=stat.st_size,
                mtime_ns=stat.st_mtime_ns,
                sha256=sha256_file(p),
            )
            entries.append(asdict(e))
        content_view = [{"path": e["path"], "size": e["size"], "sha256": e["sha256"]} for e in entries]
        return {
            "root": str(rootp),
            "entries": entries,
            "content_hash": sha256_bytes(stable_json(content_view).encode()),
            "git_head": self._git_head(rootp),
        }

    def snapshot(self, root: str | os.PathLike[str], label: str) -> dict[str, Any]:
        manifest = self.build_manifest(root)
        payload = {
            "label": label,
            "root": manifest["root"],
            "content_hash": manifest["content_hash"],
            "git_head": manifest["git_head"],
        }
        sid = sha256_bytes(stable_json(payload).encode())
        self.conn.execute(
            "INSERT OR REPLACE INTO snapshots(snapshot_id,label,root,created_at,manifest_json,manifest_hash,git_head) VALUES (?,?,?,?,?,?,?)",
            (sid, label, manifest["root"], utcnow(), stable_json(manifest), manifest["content_hash"], manifest["git_head"]),
        )
        self.conn.commit()
        return {"snapshot_id": sid, **manifest}

    def latest_snapshot(self) -> dict[str, Any] | None:
        r = self.conn.execute("SELECT * FROM snapshots ORDER BY created_at DESC, snapshot_id DESC LIMIT 1").fetchone()
        if not r:
            return None
        m = json.loads(r["manifest_json"])
        return {"snapshot_id": r["snapshot_id"], "label": r["label"], "created_at": r["created_at"], **m}

    def reconcile_root(self, root: str | os.PathLike[str]) -> dict[str, Any]:
        previous = self.latest_snapshot()
        current = self.build_manifest(root)
        if not previous:
            return {"status": "no_baseline", "current": current}
        old = {e["path"]: e for e in previous["entries"]}
        new = {e["path"]: e for e in current["entries"]}
        added = sorted(set(new) - set(old))
        removed = sorted(set(old) - set(new))
        changed = sorted(p for p in set(old) & set(new) if old[p]["sha256"] != new[p]["sha256"])
        unchanged = sorted(p for p in set(old) & set(new) if old[p]["sha256"] == new[p]["sha256"])
        return {
            "status": "drift" if added or removed or changed else "clean",
            "baseline_snapshot_id": previous["snapshot_id"],
            "baseline_hash": previous["content_hash"],
            "current_hash": current["content_hash"],
            "added": added,
            "removed": removed,
            "changed": changed,
            "unchanged_count": len(unchanged),
            "git_head": current["git_head"],
        }

    def add_proof_bundle(self, bundle: dict[str, Any]) -> str:
        raw = stable_json(bundle)
        h = sha256_bytes(raw.encode())
        self.conn.execute(
            "INSERT OR REPLACE INTO proof_bundles(change_id,bundle_json,bundle_hash,status,created_at) VALUES (?,?,?,?,?)",
            (bundle["change_id"], raw, h, bundle.get("status", "draft"), utcnow()),
        )
        self.conn.commit()
        return h

    def proof_provenance_graph(self, known_at: str = "9999-12-31T23:59:59.999999Z") -> dict[str, Any]:
        """Return the knowledge-time proof supersession DAG and validated replacement chains."""
        nodes = [r["change_id"] for r in self.conn.execute("SELECT change_id FROM proof_bundles ORDER BY change_id").fetchall()]
        latest = {}
        for cid in nodes:
            row = self.conn.execute(
                "SELECT * FROM proof_lifecycle_events WHERE change_id=? AND known_at<=? ORDER BY known_at DESC,event_id DESC LIMIT 1",
                (cid, known_at),
            ).fetchone()
            if row: latest[cid] = dict(row)
        edges = {cid:e["superseded_by"] for cid,e in latest.items() if e["status"] == "superseded" and e.get("superseded_by")}
        incoming = {dst for dst in edges.values()}
        roots = sorted(set(edges) - incoming)
        chains=[]; errors=[]
        for root in roots:
            path=[]; seen=set(); cur=root
            while True:
                if cur in seen:
                    errors.append({"type":"cycle","path":path+[cur]}); break
                seen.add(cur); path.append(cur)
                nxt=edges.get(cur)
                if not nxt: break
                if nxt not in nodes:
                    errors.append({"type":"missing_target","source":cur,"target":nxt}); path.append(nxt); break
                cur=nxt
            chains.append({"root":root,"path":path,"terminal":path[-1]})
        # Components with no outgoing/incoming supersession remain singleton chains.
        covered={x for c in chains for x in c["path"]}
        for cid in sorted(set(nodes)-covered): chains.append({"root":cid,"path":[cid],"terminal":cid})
        return {"known_at":known_at,"nodes":nodes,"edges":[{"from":a,"to":b} for a,b in sorted(edges.items())],"chains":chains,"errors":errors,"valid":not errors}

    def proof_impact_graph(self, change_id: str, valid_at: str, before_known_at: str, after_known_at: str) -> dict[str, Any]:
        """Explain causal project-truth impact of one proof across a knowledge window."""
        if after_known_at < before_known_at:
            raise ValueError("after_known_at must be >= before_known_at")
        if not self.conn.execute("SELECT 1 FROM proof_bundles WHERE change_id=?", (change_id,)).fetchone():
            raise KeyError(change_id)
        token = f"proof:{change_id}:"
        decisions = []
        affected_fact_ids: set[str] = set()
        affected_subjects: set[str] = set()
        for r in self.conn.execute("SELECT * FROM normalization_decisions ORDER BY known_at,decision_id"):
            refs = json.loads(r["proof_refs_json"])
            if not any(ref.startswith(token) for ref in refs):
                continue
            p = json.loads(r["proposal_json"])
            decisions.append(r["decision_id"])
            affected_fact_ids.update((p["close_fact_id"], p["successor_fact_id"]))
        if affected_fact_ids:
            qmarks = ",".join("?" for _ in affected_fact_ids)
            for r in self.conn.execute(f"SELECT subject FROM facts WHERE fact_id IN ({qmarks})", tuple(sorted(affected_fact_ids))):
                affected_subjects.add(r["subject"])
        before = self.temporal_conflicts_as_of(valid_at, before_known_at)
        after = self.temporal_conflicts_as_of(valid_at, after_known_at)
        def key(c: dict[str, Any]) -> tuple[str, str, tuple[str, ...]]:
            return (c["subject"], c["predicate"], tuple(sorted(f["fact_id"] for f in c["facts"])))
        bm, am = {key(c):c for c in before}, {key(c):c for c in after}
        delta=[]
        for k in sorted(set(bm)|set(am)):
            if k not in bm: change="conflict_reappeared"
            elif k not in am: change="conflict_resolved"
            elif bm[k]["resolution"] != am[k]["resolution"]: change="resolution_changed"
            else: continue
            delta.append({"change":change,"subject":k[0],"predicate":k[1],"fact_ids":list(k[2]),"before_resolution":bm.get(k,{}).get("resolution"),"after_resolution":am.get(k,{}).get("resolution")})
        blast=set()
        for subject in affected_subjects: blast.update(self._blast_radius(subject))
        return {
            "change_id":change_id,"valid_at":valid_at,
            "knowledge_window":{"before":before_known_at,"after":after_known_at},
            "proof_status_before":self._proof_effective_status(change_id,before_known_at)[0],
            "proof_status_after":self._proof_effective_status(change_id,after_known_at)[0],
            "normalization_decision_ids":sorted(decisions),"affected_fact_ids":sorted(affected_fact_ids),
            "affected_subjects":sorted(affected_subjects),"blast_radius":sorted(blast),
            "before":{"conflict_count":len(before),"conflicts":before},
            "after":{"conflict_count":len(after),"conflicts":after},"conflict_delta":delta,
        }

    def automatic_causal_horizon(self, change_id: str) -> dict[str, Any]:
        """Discover the full replay horizon for a proof or connected proof chain.

        This is a read-only causal analysis. It discovers proof-chain membership,
        every normalization decision that cites a chain member, the validity
        intervals those decisions can reinterpret, every relevant knowledge-time
        transition, and the conflict deltas visible at automatically selected
        replay boundaries. No source fact, proof, or decision is mutated.
        """
        if not self.conn.execute("SELECT 1 FROM proof_bundles WHERE change_id=?", (change_id,)).fetchone():
            raise KeyError(change_id)

        graph = self.proof_provenance_graph()
        # Treat supersession as an undirected lineage relation for impact discovery:
        # a receiver asking about any member should see decisions attached anywhere
        # on the connected replacement chain.
        adjacency: dict[str, set[str]] = {n: set() for n in graph["nodes"]}
        # Provenance is historical, not merely the latest effective status. A later
        # revocation must not erase the fact that two proof objects were linked by
        # an earlier supersession event.
        for edge in self.conn.execute(
            "SELECT change_id,superseded_by FROM proof_lifecycle_events WHERE status='superseded' AND superseded_by IS NOT NULL ORDER BY known_at,event_id"
        ):
            adjacency.setdefault(edge["change_id"], set()).add(edge["superseded_by"])
            adjacency.setdefault(edge["superseded_by"], set()).add(edge["change_id"])
        chain: set[str] = set()
        stack = [change_id]
        while stack:
            cur = stack.pop()
            if cur in chain:
                continue
            chain.add(cur)
            stack.extend(sorted(adjacency.get(cur, set()) - chain))

        decisions: list[dict[str, Any]] = []
        affected_fact_ids: set[str] = set()
        affected_subject_predicates: set[tuple[str, str]] = set()
        intervals: list[dict[str, Any]] = []
        transitions: list[dict[str, Any]] = []
        for r in self.conn.execute("SELECT * FROM normalization_decisions ORDER BY known_at,decision_id"):
            refs = json.loads(r["proof_refs_json"])
            cited = sorted({ref.split(":", 2)[1] for ref in refs if ref.startswith("proof:") and len(ref.split(":", 2)) == 3} & chain)
            if not cited:
                continue
            proposal = json.loads(r["proposal_json"])
            decisions.append({"decision_id": r["decision_id"], "cited_proofs": cited, "decision": r["decision"], "known_at": r["known_at"]})
            affected_fact_ids.update((proposal["close_fact_id"], proposal["successor_fact_id"]))
            old = self.conn.execute("SELECT * FROM facts WHERE fact_id=?", (proposal["close_fact_id"],)).fetchone()
            if old:
                affected_subject_predicates.add((old["subject"], old["predicate"]))
                intervals.append({
                    "decision_id": r["decision_id"], "subject": old["subject"], "predicate": old["predicate"],
                    "start": proposal["proposed_valid_to"], "end": old["valid_to"],
                    "close_fact_id": proposal["close_fact_id"], "successor_fact_id": proposal["successor_fact_id"],
                })
            transitions.append({"known_at": r["known_at"], "kind": "normalization_decision", "id": r["decision_id"], "event_status": r["decision"]})
            if r["revoked_at"]:
                transitions.append({"known_at": r["revoked_at"], "kind": "normalization_revocation", "id": r["decision_id"], "event_status": "revoked"})

        for cid in sorted(chain):
            for e in self.proof_lifecycle_events(cid):
                transitions.append({"known_at": e["known_at"], "kind": "proof_lifecycle", "id": e["event_id"], "change_id": cid, "event_status": e["status"]})

        # Replay at every boundary at which an affected subject/predicate can change
        # inside a potentially reinterpreted interval, not merely at the first point.
        replay_points: set[str] = set()
        for iv in intervals:
            replay_points.add(iv["start"])
            params: list[Any] = [iv["subject"], iv["predicate"], iv["start"]]
            sql = "SELECT valid_from,valid_to FROM facts WHERE subject=? AND predicate=? AND valid_from>=?"
            if iv["end"] is not None:
                sql += " AND valid_from<?"
                params.append(iv["end"])
            for f in self.conn.execute(sql, tuple(params)):
                replay_points.add(f["valid_from"])
                if f["valid_to"] and (iv["end"] is None or f["valid_to"] < iv["end"]):
                    replay_points.add(f["valid_to"])

        def before_timestamp(ts: str) -> str:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            from datetime import timedelta
            return (dt - timedelta(microseconds=1)).isoformat().replace("+00:00", "Z")

        unique_transitions = []
        seen_t = set()
        for t in sorted(transitions, key=lambda x: (x["known_at"], x["kind"], x["id"])):
            key = (t["known_at"], t["kind"], t["id"], t["event_status"])
            if key in seen_t:
                continue
            seen_t.add(key)
            unique_transitions.append({**t, "before_known_at": before_timestamp(t["known_at"]), "after_known_at": t["known_at"]})

        def conflict_key(c: dict[str, Any]) -> tuple[str, str, tuple[str, ...]]:
            return (c["subject"], c["predicate"], tuple(sorted(f["fact_id"] for f in c["facts"])))

        deltas: list[dict[str, Any]] = []
        for t in unique_transitions:
            for valid_at in sorted(replay_points):
                before = [c for c in self.temporal_conflicts_as_of(valid_at, t["before_known_at"]) if (c["subject"], c["predicate"]) in affected_subject_predicates]
                after = [c for c in self.temporal_conflicts_as_of(valid_at, t["after_known_at"]) if (c["subject"], c["predicate"]) in affected_subject_predicates]
                bm, am = {conflict_key(c): c for c in before}, {conflict_key(c): c for c in after}
                for k in sorted(set(bm) | set(am)):
                    if k not in bm:
                        change = "conflict_reappeared"
                    elif k not in am:
                        change = "conflict_resolved"
                    elif bm[k]["resolution"] != am[k]["resolution"]:
                        change = "resolution_changed"
                    else:
                        continue
                    deltas.append({
                        "transition": {k2: t[k2] for k2 in ("known_at", "kind", "id", "event_status") if k2 in t},
                        "valid_at": valid_at, "change": change, "subject": k[0], "predicate": k[1],
                        "fact_ids": list(k[2]), "before_resolution": bm.get(k, {}).get("resolution"),
                        "after_resolution": am.get(k, {}).get("resolution"),
                    })

        blast: set[str] = set()
        for subject, _ in affected_subject_predicates:
            blast.update(self._blast_radius(subject))
        unique_delta_keys = {(d["valid_at"], d["change"], d["subject"], d["predicate"], tuple(d["fact_ids"])) for d in deltas}
        score = min(100, 25 * len(unique_delta_keys) + 10 * len(affected_subject_predicates) + 5 * len(blast) + 5 * len(decisions))
        band = "critical" if score >= 75 else "high" if score >= 50 else "moderate" if score >= 25 else "low" if score else "none"
        causal_core = {
            "change_id": change_id, "proof_chain": sorted(chain),
            "normalization_decision_ids": sorted(d["decision_id"] for d in decisions),
            "affected_fact_ids": sorted(affected_fact_ids),
            "affected_subjects": sorted({s for s, _ in affected_subject_predicates}),
            "affected_validity_intervals": sorted(intervals, key=lambda x: (x["start"], x["decision_id"])),
            "replay_valid_at": sorted(replay_points), "knowledge_transitions": unique_transitions,
            "conflict_deltas": deltas, "blast_radius": sorted(blast),
            "exposure": {
                "score": score, "band": band,
                "factors": {"changed_conflict_boundaries": len(unique_delta_keys), "affected_subject_predicates": len(affected_subject_predicates), "downstream_components": len(blast), "normalization_decisions": len(decisions)},
                "formula": "min(100,25*changed_conflict_boundaries+10*affected_subject_predicates+5*downstream_components+5*normalization_decisions)",
            },
        }
        certificate_payload = {
            "change_id": change_id, "proof_chain": causal_core["proof_chain"],
            "decision_ids": causal_core["normalization_decision_ids"], "intervals": causal_core["affected_validity_intervals"],
            "transitions": causal_core["knowledge_transitions"], "deltas": causal_core["conflict_deltas"],
            "blast_radius": causal_core["blast_radius"], "exposure": causal_core["exposure"],
        }
        causal_core["certificate"] = {
            "kind": "janus-causal-horizon-certificate-v1",
            "digest": sha256_bytes(stable_json(certificate_payload).encode()),
            "deterministic": True, "mutation_applied": False,
        }
        return causal_core

    def generalized_truth_delta(self, change_id: str) -> dict[str, Any]:
        """Explain all reconstructed truth-surface changes caused by a proof lineage.

        Unlike conflict-only causal replay, this compares the complete set of
        interval-eligible observations for affected subject/predicates across each
        discovered knowledge transition. It therefore captures added/removed facts
        even when no adjudicated conflict exists. The method is read-only.
        """
        horizon = self.automatic_causal_horizon(change_id)
        affected = set()
        for iv in horizon["affected_validity_intervals"]:
            affected.add((iv["subject"], iv["predicate"]))

        def surface(valid_at: str, known_at: str) -> dict[tuple[str, str, str], dict[str, Any]]:
            overlays = self.verified_normalization_overlays(known_at)
            overlay_ends = {o["close_fact_id"]: o["effective_valid_to"] for o in overlays}
            rows = self.conn.execute(
                "SELECT * FROM facts WHERE valid_from<=? AND known_at<=? ORDER BY subject,predicate,valid_from,known_at,fact_id",
                (valid_at, known_at),
            ).fetchall()
            eligible = []
            for r in rows:
                if (r["subject"], r["predicate"]) not in affected:
                    continue
                ends = [x for x in (r["valid_to"], overlay_ends.get(r["fact_id"])) if x is not None]
                effective_end = min(ends) if ends else None
                if effective_end is None or valid_at < effective_end:
                    eligible.append(r)
            ids = {r["fact_id"] for r in eligible}
            superseded = {r["supersedes"] for r in eligible if r["supersedes"] in ids}
            return {(r["subject"], r["predicate"], r["fact_id"]): self._fact_row(r) for r in eligible if r["fact_id"] not in superseded}

        deltas = []
        for transition in horizon["knowledge_transitions"]:
            for valid_at in horizon["replay_valid_at"]:
                before = surface(valid_at, transition["before_known_at"])
                after = surface(valid_at, transition["after_known_at"])
                for key in sorted(set(before) | set(after)):
                    b, a = before.get(key), after.get(key)
                    if b is None:
                        change = "added"
                    elif a is None:
                        change = "removed"
                    elif b["value"] != a["value"]:
                        change = "changed"
                    else:
                        continue
                    deltas.append({
                        "transition": {k: transition[k] for k in ("known_at", "kind", "id", "event_status") if k in transition},
                        "valid_at": valid_at, "change": change,
                        "subject": key[0], "predicate": key[1], "fact_id": key[2],
                        "before_value": None if b is None else b["value"],
                        "after_value": None if a is None else a["value"],
                    })

        # Minimal certificate contains only causal identifiers and observed deltas;
        # descriptive/redundant horizon fields are deliberately excluded.
        payload = {
            "change_id": change_id,
            "proof_chain": horizon["proof_chain"],
            "normalization_decision_ids": horizon["normalization_decision_ids"],
            "truth_deltas": deltas,
            "conflict_deltas": horizon["conflict_deltas"],
            "blast_radius": horizon["blast_radius"],
        }
        certificate = {
            "kind": "janus-minimal-causal-proof-certificate-v1",
            "digest": sha256_bytes(stable_json(payload).encode()),
            "truth_delta_count": len(deltas),
            "conflict_delta_count": len(horizon["conflict_deltas"]),
            "deterministic": True,
            "mutation_applied": False,
        }
        return {**payload, "certificate": certificate}

    def build_causal_evidence_bundle(self, change_id: str) -> dict[str, Any]:
        """Build the minimal content-addressed evidence closure for a causal certificate."""
        report = self.generalized_truth_delta(change_id)
        chain = set(report["proof_chain"])
        decision_ids = set(report["normalization_decision_ids"])
        fact_ids = {d["fact_id"] for d in report["truth_deltas"] if d.get("fact_id")}
        for did in decision_ids:
            row = self.conn.execute("SELECT proposal_json FROM normalization_decisions WHERE decision_id=?", (did,)).fetchone()
            if row:
                p = json.loads(row["proposal_json"]); fact_ids.update([p["close_fact_id"], p["successor_fact_id"]])
        objects = []
        for cid in sorted(chain):
            r=self.conn.execute("SELECT change_id,bundle_json,bundle_hash,status FROM proof_bundles WHERE change_id=?",(cid,)).fetchone()
            if r: objects.append({"kind":"proof_bundle","change_id":r["change_id"],"bundle":json.loads(r["bundle_json"]),"bundle_hash":r["bundle_hash"],"status":r["status"]})
            for e in self.conn.execute("SELECT event_id,change_id,status,known_at,actor,reason,superseded_by FROM proof_lifecycle_events WHERE change_id=? ORDER BY known_at,event_id",(cid,)):
                objects.append({"kind":"proof_lifecycle_event",**dict(e)})
        for did in sorted(decision_ids):
            r=self.conn.execute("SELECT * FROM normalization_decisions WHERE decision_id=?",(did,)).fetchone()
            if r: objects.append({"kind":"normalization_decision",**dict(r)})
        subjects=set()
        for fid in sorted(fact_ids):
            r=self.conn.execute("SELECT fact_id,subject,predicate,value_json,valid_from,valid_to,known_at,source,source_hash,authority,confidence,supersedes FROM facts WHERE fact_id=?",(fid,)).fetchone()
            if r: objects.append({"kind":"fact",**dict(r)}); subjects.add(r["subject"].split('.')[0])
        # Conflict replay may depend on competing facts that did not themselves change.
        # Include every fact participating in the certificate's conflict deltas.
        conflict_fact_ids={fid for d in report["conflict_deltas"] for fid in d.get("fact_ids",[])}
        for fid in sorted(conflict_fact_ids - fact_ids):
            r=self.conn.execute("SELECT fact_id,subject,predicate,value_json,valid_from,valid_to,known_at,source,source_hash,authority,confidence,supersedes FROM facts WHERE fact_id=?",(fid,)).fetchone()
            if r: objects.append({"kind":"fact",**dict(r)}); subjects.add(r["subject"].split('.')[0])
        # Dependencies are part of the certificate because they justify blast radius.
        needed=set(subjects)|set(report["blast_radius"])
        # Include the complete dependency subgraph among the causal root and its blast radius.
        # This is required for a receiver to independently reproduce transitive exposure.
        for r in self.conn.execute("SELECT src,dst,kind FROM dependencies ORDER BY src,dst,kind"):
            if r["src"] in needed and r["dst"] in needed: objects.append({**dict(r),"kind":"dependency"})
        for name in sorted(needed):
            r=self.conn.execute("SELECT name,authority,metadata_json FROM components WHERE name=?",(name,)).fetchone()
            if r: objects.append({**dict(r),"kind":"component"})
        for r in self.conn.execute("SELECT subject_prefix,predicate,authority,rank FROM authority_precedence ORDER BY subject_prefix,predicate,authority"):
            objects.append({"kind":"authority_precedence",**dict(r)})
        for r in self.conn.execute("SELECT confidence,rank FROM evidence_precedence ORDER BY confidence"):
            objects.append({"kind":"evidence_precedence",**dict(r)})
        chunks={}
        for obj in objects:
            digest=sha256_bytes(stable_json(obj).encode()); chunks[digest]={"sha256":digest,"payload":obj}
        leaves=sorted(chunks)
        root=sha256_bytes(stable_json(leaves).encode())
        return {"format":"janus-causal-evidence-bundle-v1","change_id":change_id,"certificate":report["certificate"],"manifest":{"chunk_hashes":leaves,"root_digest":root},"chunks":chunks}

    def build_merkle_evidence_manifest(self, bundle: dict[str, Any]) -> dict[str, Any]:
        """Build deterministic binary Merkle inclusion proofs over bundle chunk digests."""
        verification = self.verify_causal_evidence_bundle(bundle)
        if not verification["valid"]:
            raise ValueError("cannot merklize invalid causal evidence bundle")
        leaves = sorted(bundle["chunks"])
        if not leaves:
            raise ValueError("cannot merklize empty evidence bundle")
        proofs = {h: [] for h in leaves}
        # Each node tracks the original leaves it commits to so sibling steps can
        # be appended to every affected leaf's inclusion path.
        level = [(h, [h]) for h in leaves]
        while len(level) > 1:
            nxt = []
            for i in range(0, len(level), 2):
                left_hash, left_members = level[i]
                if i + 1 < len(level):
                    right_hash, right_members = level[i + 1]
                else:
                    right_hash, right_members = left_hash, []
                for h in left_members:
                    proofs[h].append({"side": "right", "hash": right_hash})
                for h in right_members:
                    proofs[h].append({"side": "left", "hash": left_hash})
                parent = sha256_bytes(stable_json([left_hash, right_hash]).encode())
                nxt.append((parent, left_members + right_members))
            level = nxt
        return {
            "format": "janus-merkle-evidence-manifest-v1",
            "hash_algorithm": "sha256",
            "bundle_format": bundle["format"],
            "certificate_kind": bundle["certificate"]["kind"],
            "leaves": leaves,
            "root_digest": level[0][0],
            "proofs": proofs,
        }

    def verify_merkle_inclusion(self, leaf_hash: str, proof: list[dict[str, str]], root_digest: str) -> bool:
        if not isinstance(leaf_hash, str) or len(leaf_hash) != 64:
            return False
        current = leaf_hash
        for step in proof:
            sibling = step.get("hash"); side = step.get("side")
            if not isinstance(sibling, str) or len(sibling) != 64 or side not in {"left", "right"}:
                return False
            pair = [sibling, current] if side == "left" else [current, sibling]
            current = sha256_bytes(stable_json(pair).encode())
        return current == root_digest

    def verification_capabilities(self) -> dict[str, Any]:
        return {
            "protocol": "janus-verification-contract-v1",
            "bundle_formats": ["janus-causal-evidence-bundle-v1"],
            "merkle_formats": ["janus-merkle-evidence-manifest-v1"],
            "certificate_kinds": ["janus-minimal-causal-proof-certificate-v1"],
            "hash_algorithms": ["sha256"],
        }

    def negotiate_verification_contract(self, receiver: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
        reasons = []
        if receiver.get("protocol") != "janus-verification-contract-v1": reasons.append("unsupported_protocol")
        if manifest.get("bundle_format") not in receiver.get("bundle_formats", []): reasons.append("unsupported_bundle_format")
        if manifest.get("format") not in receiver.get("merkle_formats", []): reasons.append("unsupported_merkle_format")
        if manifest.get("certificate_kind") not in receiver.get("certificate_kinds", []): reasons.append("unsupported_certificate_kind")
        if manifest.get("hash_algorithm") not in receiver.get("hash_algorithms", []): reasons.append("unsupported_hash_algorithm")
        return {"compatible": not reasons, "reasons": reasons, "contract": "janus-verification-contract-v1"}

    def missing_evidence_chunks(self, manifest: dict[str, Any], available_hashes: set[str] | list[str]) -> list[str]:
        available = set(available_hashes)
        return [h for h in manifest.get("leaves", []) if h not in available]

    def generate_signing_keypair(self) -> tuple[str, str]:
        """Generate an Ed25519 keypair encoded as base64 raw key bytes."""
        private = Ed25519PrivateKey.generate()
        private_raw = private.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
        public_raw = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        return base64.b64encode(private_raw).decode(), base64.b64encode(public_raw).decode()

    def sign_merkle_root(self, manifest: dict[str, Any], authority: str, private_key_b64: str) -> dict[str, Any]:
        """Sign a domain-separated Merkle-root commitment; this authenticates origin, not semantic authority."""
        if manifest.get("format") != "janus-merkle-evidence-manifest-v1":
            raise ValueError("unsupported merkle manifest")
        statement = {"domain":"JANUS_MERKLE_ROOT_V1","root_digest":manifest["root_digest"],"manifest_format":manifest["format"],"hash_algorithm":manifest["hash_algorithm"],"authority":authority}
        private = Ed25519PrivateKey.from_private_bytes(base64.b64decode(private_key_b64))
        signature = private.sign(stable_json(statement).encode())
        return {"format":"janus-signed-proof-root-v1","algorithm":"Ed25519","authority":authority,"statement":statement,"signature":base64.b64encode(signature).decode()}

    def verify_signed_merkle_root(self, envelope: dict[str, Any], manifest: dict[str, Any], trust_store: dict[str, str]) -> dict[str, Any]:
        errors=[]
        if envelope.get("format") != "janus-signed-proof-root-v1" or envelope.get("algorithm") != "Ed25519": errors.append("unsupported_signature_envelope")
        authority=envelope.get("authority")
        if authority not in trust_store: errors.append("untrusted_authority")
        statement=envelope.get("statement",{})
        expected={"domain":"JANUS_MERKLE_ROOT_V1","root_digest":manifest.get("root_digest"),"manifest_format":manifest.get("format"),"hash_algorithm":manifest.get("hash_algorithm"),"authority":authority}
        if statement != expected: errors.append("signed_statement_mismatch")
        if not errors:
            try:
                public=Ed25519PublicKey.from_public_bytes(base64.b64decode(trust_store[authority]))
                public.verify(base64.b64decode(envelope.get("signature","")), stable_json(statement).encode())
            except (ValueError, InvalidSignature, TypeError): errors.append("invalid_signature")
        return {"valid":not errors,"errors":errors,"authority":authority,"root_digest":manifest.get("root_digest")}

    def record_signing_key(self, key_id: str, authority: str, public_key_b64: str, valid_from: str, known_at: str, valid_to: str | None = None) -> str:
        """Append a bitemporal trust assertion for one signing key."""
        Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
        self.conn.execute("INSERT INTO signing_keys(key_id,authority,public_key_b64,valid_from,valid_to,known_at) VALUES (?,?,?,?,?,?)", (key_id,authority,public_key_b64,valid_from,valid_to,known_at))
        self.conn.commit(); return key_id

    def revoke_signing_key(self, key_id: str, revoked_at: str, reason: str) -> None:
        row=self.conn.execute("SELECT revoked_at FROM signing_keys WHERE key_id=?",(key_id,)).fetchone()
        if row is None: raise KeyError(key_id)
        if row["revoked_at"] is not None: raise ValueError("key already revoked")
        self.conn.execute("UPDATE signing_keys SET revoked_at=?,revocation_reason=? WHERE key_id=?",(revoked_at,reason,key_id)); self.conn.commit()

    def record_authorization_policy(self, subsystem: str, evidence_class: str, authorities: list[str], threshold: int, valid_from: str, known_at: str, valid_to: str | None = None) -> str:
        auths=sorted(set(authorities))
        if threshold < 1 or threshold > len(auths): raise ValueError("invalid threshold")
        core={"subsystem":subsystem,"evidence_class":evidence_class,"authorities":auths,"threshold":threshold,"valid_from":valid_from,"valid_to":valid_to,"known_at":known_at}
        pid=sha256_bytes(stable_json(core).encode())
        self.conn.execute("INSERT OR IGNORE INTO authorization_policies(policy_id,subsystem,evidence_class,authorities_json,threshold,valid_from,valid_to,known_at) VALUES (?,?,?,?,?,?,?,?)",(pid,subsystem,evidence_class,stable_json(auths),threshold,valid_from,valid_to,known_at)); self.conn.commit(); return pid

    def revoke_authorization_policy(self, policy_id: str, revoked_at: str, revoked_by: str, reason: str) -> None:
        row=self.conn.execute("SELECT revoked_at FROM authorization_policies WHERE policy_id=?",(policy_id,)).fetchone()
        if row is None: raise KeyError(policy_id)
        if row["revoked_at"] is not None: raise ValueError("policy already revoked")
        self.conn.execute("UPDATE authorization_policies SET revoked_at=?,revoked_by=?,revocation_reason=? WHERE policy_id=?",(revoked_at,revoked_by,reason,policy_id)); self.conn.commit()

    def record_key_rotation(self, predecessor_key_id: str, successor_key_id: str, rotated_at: str, known_at: str) -> None:
        old=self.conn.execute("SELECT authority FROM signing_keys WHERE key_id=?",(predecessor_key_id,)).fetchone(); new=self.conn.execute("SELECT authority FROM signing_keys WHERE key_id=?",(successor_key_id,)).fetchone()
        if old is None or new is None: raise KeyError("unknown rotation key")
        if old["authority"] != new["authority"]: raise ValueError("cross_authority_rotation_forbidden")
        if predecessor_key_id == successor_key_id: raise ValueError("self_rotation_forbidden")
        # Reject any edge that would make successor reach predecessor. Rotation is a DAG.
        frontier=[successor_key_id]; seen=set()
        while frontier:
            cur=frontier.pop()
            if cur == predecessor_key_id: raise ValueError("rotation_cycle_forbidden")
            if cur in seen: continue
            seen.add(cur)
            rows=self.conn.execute("SELECT successor_key_id FROM signing_key_rotations WHERE predecessor_key_id=?",(cur,)).fetchall()
            frontier.extend(r["successor_key_id"] for r in rows)
        self.conn.execute("INSERT INTO signing_key_rotations(predecessor_key_id,successor_key_id,rotated_at,known_at) VALUES (?,?,?,?)",(predecessor_key_id,successor_key_id,rotated_at,known_at)); self.conn.commit()

    def record_authority_delegation(self, principal_authority: str, delegate_authority: str, subsystem: str, evidence_class: str, valid_from: str, known_at: str, valid_to: str | None = None) -> str:
        if principal_authority == delegate_authority: raise ValueError("self_delegation_forbidden")
        core={"principal_authority":principal_authority,"delegate_authority":delegate_authority,"subsystem":subsystem,"evidence_class":evidence_class,"valid_from":valid_from,"valid_to":valid_to,"known_at":known_at}
        did=sha256_bytes(stable_json(core).encode())
        self.conn.execute("INSERT INTO authority_delegations(delegation_id,principal_authority,delegate_authority,subsystem,evidence_class,valid_from,valid_to,known_at) VALUES (?,?,?,?,?,?,?,?)",(did,principal_authority,delegate_authority,subsystem,evidence_class,valid_from,valid_to,known_at)); self.conn.commit(); return did

    def revoke_authority_delegation(self, delegation_id: str, revoked_at: str, revoked_by: str, reason: str) -> None:
        row=self.conn.execute("SELECT revoked_at FROM authority_delegations WHERE delegation_id=?",(delegation_id,)).fetchone()
        if row is None: raise KeyError(delegation_id)
        if row["revoked_at"] is not None: raise ValueError("delegation already revoked")
        self.conn.execute("UPDATE authority_delegations SET revoked_at=?,revoked_by=?,revocation_reason=? WHERE delegation_id=?",(revoked_at,revoked_by,reason,delegation_id)); self.conn.commit()

    def _rotation_predecessor_chain(self, key_id: str, valid_at: str, known_at: str) -> list[dict[str, str]]:
        chain=[]; cur=key_id; seen=set()
        while cur not in seen:
            seen.add(cur)
            row=self.conn.execute("SELECT predecessor_key_id,successor_key_id FROM signing_key_rotations WHERE successor_key_id=? AND rotated_at<=? AND known_at<=? ORDER BY rotated_at DESC,predecessor_key_id LIMIT 1",(cur,valid_at,known_at)).fetchone()
            if row is None: break
            edge={"predecessor_key_id":row["predecessor_key_id"],"successor_key_id":row["successor_key_id"]}
            chain.append(edge); cur=row["predecessor_key_id"]
        chain.reverse(); return chain

    def verify_authorized_merkle_root_at(self, envelopes: list[dict[str, Any]], manifest: dict[str, Any], subsystem: str, evidence_class: str, valid_at: str, known_at: str) -> dict[str, Any]:
        """Verify signatures, temporal key trust, scoped direct/non-transitive delegation, and quorum."""
        policies=self.conn.execute("SELECT * FROM authorization_policies WHERE subsystem=? AND evidence_class=? AND valid_from<=? AND (valid_to IS NULL OR valid_to>?) AND known_at<=? AND (revoked_at IS NULL OR revoked_at>?) ORDER BY known_at DESC,policy_id",(subsystem,evidence_class,valid_at,valid_at,known_at,known_at)).fetchall()
        if not policies: return {"authorized":False,"errors":["no_applicable_authorization_policy"],"valid_signers":[]}
        policy=policies[0]; allowed=set(json.loads(policy["authorities_json"])); valid_signers=set(); satisfied=set(); errors=[]; delegation_lineage=[]; rotation_lineage=[]
        delegations=self.conn.execute("SELECT * FROM authority_delegations WHERE subsystem=? AND evidence_class=? AND valid_from<=? AND (valid_to IS NULL OR valid_to>?) AND known_at<=? AND (revoked_at IS NULL OR revoked_at>?)",(subsystem,evidence_class,valid_at,valid_at,known_at,known_at)).fetchall()
        direct_delegate={d["delegate_authority"]:d for d in delegations if d["principal_authority"] in allowed}
        for env in envelopes:
            signer=env.get("authority"); principal=signer if signer in allowed else (direct_delegate.get(signer)["principal_authority"] if signer in direct_delegate else None)
            if principal is None: errors.append(f"unauthorized_authority:{signer}"); continue
            keys=self.conn.execute("SELECT * FROM signing_keys WHERE authority=? AND valid_from<=? AND (valid_to IS NULL OR valid_to>?) AND known_at<=? AND (revoked_at IS NULL OR revoked_at>?) ORDER BY known_at DESC,key_id",(signer,valid_at,valid_at,known_at,known_at)).fetchall()
            matched=None
            for key in keys:
                if self.verify_signed_merkle_root(env,manifest,{signer:key["public_key_b64"]})["valid"]: matched=key; break
            if matched is None: errors.append(f"no_valid_key_at_boundary:{signer}"); continue
            valid_signers.add(signer); satisfied.add(principal)
            if signer != principal:
                d=direct_delegate[signer]; delegation_lineage.append({"principal_authority":principal,"delegate_authority":signer,"delegation_id":d["delegation_id"]})
            rotation_lineage.extend(self._rotation_predecessor_chain(matched["key_id"],valid_at,known_at))
        threshold=int(policy["threshold"]); quorum=len(satisfied)>=threshold
        if not quorum: errors.append("quorum_not_met")
        result={"authorized":quorum,"errors":errors,"policy_id":policy["policy_id"],"threshold":threshold,"valid_signers":sorted(valid_signers),"satisfied_principals":sorted(satisfied),"delegation_lineage":sorted(delegation_lineage,key=lambda x:(x["principal_authority"],x["delegate_authority"])),"key_rotation_lineage":sorted(rotation_lineage,key=lambda x:(x["predecessor_key_id"],x["successor_key_id"])),"valid_at":valid_at,"known_at":known_at,"subsystem":subsystem,"evidence_class":evidence_class}
        decision_core={k:result[k] for k in ("authorized","policy_id","threshold","valid_signers","satisfied_principals","delegation_lineage","key_rotation_lineage","valid_at","known_at","subsystem","evidence_class")}
        result["authorization_decision_digest"]=sha256_bytes(stable_json(decision_core).encode()); return result

    def build_trust_lineage_bundle(self, envelopes: list[dict[str, Any]], manifest: dict[str, Any], subsystem: str, evidence_class: str, valid_at: str, known_at: str) -> dict[str, Any]:
        """Export the minimal content-addressed trust state needed to replay one authorization decision."""
        decision=self.verify_authorized_merkle_root_at(envelopes,manifest,subsystem,evidence_class,valid_at,known_at)
        if not decision.get("authorized"): raise ValueError("cannot_export_unauthorized_decision")
        objects=[]
        policy=self.conn.execute("SELECT * FROM authorization_policies WHERE policy_id=?",(decision["policy_id"],)).fetchone()
        objects.append({"kind":"authorization_policy",**dict(policy)})
        signer_authorities=set(decision["valid_signers"])
        key_ids=set()
        for authority in sorted(signer_authorities):
            for key in self.conn.execute("SELECT * FROM signing_keys WHERE authority=? AND valid_from<=? AND (valid_to IS NULL OR valid_to>?) AND known_at<=? AND (revoked_at IS NULL OR revoked_at>?) ORDER BY key_id",(authority,valid_at,valid_at,known_at,known_at)):
                objects.append({"kind":"signing_key",**dict(key)}); key_ids.add(key["key_id"])
        for edge in decision["key_rotation_lineage"]:
            r=self.conn.execute("SELECT * FROM signing_key_rotations WHERE predecessor_key_id=? AND successor_key_id=?",(edge["predecessor_key_id"],edge["successor_key_id"])).fetchone()
            if r:
                objects.append({"kind":"signing_key_rotation",**dict(r)}); key_ids.update([r["predecessor_key_id"],r["successor_key_id"]])
        for kid in sorted(key_ids):
            if not any(o.get("kind")=="signing_key" and o.get("key_id")==kid for o in objects):
                r=self.conn.execute("SELECT * FROM signing_keys WHERE key_id=?",(kid,)).fetchone()
                if r: objects.append({"kind":"signing_key",**dict(r)})
        for d in decision["delegation_lineage"]:
            r=self.conn.execute("SELECT * FROM authority_delegations WHERE delegation_id=?",(d["delegation_id"],)).fetchone()
            if r: objects.append({"kind":"authority_delegation",**dict(r)})
        chunks={}
        for obj in objects:
            h=sha256_bytes(stable_json(obj).encode()); chunks[h]={"sha256":h,"payload":obj}
        core={"format":"janus-trust-lineage-bundle-v1","subsystem":subsystem,"evidence_class":evidence_class,"valid_at":valid_at,"known_at":known_at,"authorization_decision_digest":decision["authorization_decision_digest"],"chunk_hashes":sorted(chunks)}
        return {**core,"bundle_digest":sha256_bytes(stable_json(core).encode()),"chunks":chunks}

    def verify_trust_lineage_bundle(self, bundle: dict[str, Any]) -> dict[str, Any]:
        errors=[]
        if bundle.get("format")!="janus-trust-lineage-bundle-v1": errors.append("unsupported_trust_bundle")
        chunks=bundle.get("chunks",{})
        for h,c in chunks.items():
            actual=sha256_bytes(stable_json(c.get("payload")).encode())
            if h!=c.get("sha256") or h!=actual: errors.append(f"chunk_hash_mismatch:{h}")
        if sorted(chunks)!=bundle.get("chunk_hashes",[]): errors.append("chunk_manifest_mismatch")
        core={k:bundle.get(k) for k in ("format","subsystem","evidence_class","valid_at","known_at","authorization_decision_digest","chunk_hashes")}
        if sha256_bytes(stable_json(core).encode())!=bundle.get("bundle_digest"): errors.append("bundle_digest_mismatch")
        return {"valid":not errors,"errors":errors}

    def build_trust_lineage_merkle_manifest(self, bundle: dict[str, Any]) -> dict[str, Any]:
        if not self.verify_trust_lineage_bundle(bundle)["valid"]: raise ValueError("invalid_trust_lineage_bundle")
        leaves=sorted(bundle["chunks"]); proofs={h:[] for h in leaves}; level=[(h,[h]) for h in leaves]
        if not level: raise ValueError("empty_trust_lineage_bundle")
        while len(level)>1:
            nxt=[]
            for i in range(0,len(level),2):
                lh,lm=level[i]; rh,rm=level[i+1] if i+1<len(level) else (lh,[])
                for h in lm: proofs[h].append({"side":"right","hash":rh})
                for h in rm: proofs[h].append({"side":"left","hash":lh})
                nxt.append((sha256_bytes(stable_json([lh,rh]).encode()),lm+rm))
            level=nxt
        return {"format":"janus-trust-lineage-merkle-v1","hash_algorithm":"sha256","bundle_format":bundle["format"],"leaves":leaves,"root_digest":level[0][0],"proofs":proofs}

    def missing_trust_lineage_chunks(self, manifest: dict[str, Any], available_hashes: set[str] | list[str]) -> list[str]:
        available=set(available_hashes); return [h for h in manifest.get("leaves",[]) if h not in available]

    def import_and_replay_trust_lineage(self, bundle: dict[str, Any], envelopes: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
        """Verify before mutation, import only trust objects in the closure, then reproduce the sender decision."""
        check=self.verify_trust_lineage_bundle(bundle)
        if not check["valid"]: raise ValueError("invalid_trust_lineage_bundle:"+",".join(check["errors"]))
        for h in bundle["chunk_hashes"]:
            o=bundle["chunks"][h]["payload"]; kind=o["kind"]
            if kind=="signing_key":
                self.conn.execute("INSERT OR IGNORE INTO signing_keys(key_id,authority,public_key_b64,valid_from,valid_to,known_at,revoked_at,revocation_reason) VALUES (?,?,?,?,?,?,?,?)",tuple(o.get(k) for k in ("key_id","authority","public_key_b64","valid_from","valid_to","known_at","revoked_at","revocation_reason")))
            elif kind=="authorization_policy":
                self.conn.execute("INSERT OR IGNORE INTO authorization_policies(policy_id,subsystem,evidence_class,authorities_json,threshold,valid_from,valid_to,known_at,revoked_at,revoked_by,revocation_reason) VALUES (?,?,?,?,?,?,?,?,?,?,?)",tuple(o.get(k) for k in ("policy_id","subsystem","evidence_class","authorities_json","threshold","valid_from","valid_to","known_at","revoked_at","revoked_by","revocation_reason")))
            elif kind=="authority_delegation":
                self.conn.execute("INSERT OR IGNORE INTO authority_delegations(delegation_id,principal_authority,delegate_authority,subsystem,evidence_class,valid_from,valid_to,known_at,revoked_at,revoked_by,revocation_reason) VALUES (?,?,?,?,?,?,?,?,?,?,?)",tuple(o.get(k) for k in ("delegation_id","principal_authority","delegate_authority","subsystem","evidence_class","valid_from","valid_to","known_at","revoked_at","revoked_by","revocation_reason")))
            elif kind=="signing_key_rotation":
                self.conn.execute("INSERT OR IGNORE INTO signing_key_rotations(predecessor_key_id,successor_key_id,rotated_at,known_at) VALUES (?,?,?,?)",tuple(o.get(k) for k in ("predecessor_key_id","successor_key_id","rotated_at","known_at")))
            else: raise ValueError("unsupported_trust_object:"+str(kind))
        self.conn.commit()
        replay=self.verify_authorized_merkle_root_at(envelopes,manifest,bundle["subsystem"],bundle["evidence_class"],bundle["valid_at"],bundle["known_at"])
        if replay.get("authorization_decision_digest")!=bundle["authorization_decision_digest"]: raise ValueError("authorization_decision_reproduction_failed")
        return replay

    def begin_sync_session(self, causal_bundle: dict[str, Any], causal_manifest: dict[str, Any], trust_bundle: dict[str, Any]) -> str:
        """Create or resume a deterministic control-plane checkpoint without changing project truth."""
        core={"change_id":causal_bundle["change_id"],"causal_root":causal_manifest["root_digest"],"trust_bundle_digest":trust_bundle["bundle_digest"],"authorization_decision_digest":trust_bundle["authorization_decision_digest"]}
        sid=sha256_bytes(stable_json(core).encode())
        now=utcnow()
        self.conn.execute("INSERT OR IGNORE INTO sync_sessions(session_id,change_id,causal_root,trust_bundle_digest,authorization_decision_digest,status,created_at,updated_at,receiver_state_digest) VALUES (?,?,?,?,?,'staged',?,?,?)",(sid,core["change_id"],core["causal_root"],core["trust_bundle_digest"],core["authorization_decision_digest"],now,now,self.state_digest()))
        self.conn.commit(); return sid

    def checkpoint_sync_chunks(self, session_id: str, evidence_domain: str, required_hashes: list[str], acquired_chunks: dict[str, Any]) -> dict[str, Any]:
        """Durably record per-session chunk inventory so verified transfer work survives restart."""
        if evidence_domain not in {"causal","trust"}: raise ValueError("unsupported_evidence_domain")
        now=utcnow(); acquired=set(acquired_chunks)
        for h in required_hashes:
            payload=acquired_chunks.get(h)
            status="acquired" if h in acquired else "missing"
            if payload is not None:
                raw=payload.get("payload") if isinstance(payload,dict) and "payload" in payload else payload
                if sha256_bytes(stable_json(raw).encode())==h: status="verified"
            self.conn.execute("INSERT INTO sync_session_chunks(session_id,evidence_domain,chunk_hash,status,payload_json,updated_at) VALUES (?,?,?,?,?,?) ON CONFLICT(session_id,evidence_domain,chunk_hash) DO UPDATE SET status=excluded.status,payload_json=COALESCE(excluded.payload_json,sync_session_chunks.payload_json),updated_at=excluded.updated_at",(session_id,evidence_domain,h,status,stable_json(payload) if payload is not None else None,now))
        self.conn.commit(); return self.sync_chunk_inventory(session_id,evidence_domain)

    def sync_chunk_inventory(self, session_id: str, evidence_domain: str) -> dict[str, Any]:
        rows=[dict(r) for r in self.conn.execute("SELECT chunk_hash,status,payload_json FROM sync_session_chunks WHERE session_id=? AND evidence_domain=? ORDER BY chunk_hash",(session_id,evidence_domain))]
        return {"session_id":session_id,"evidence_domain":evidence_domain,"required":len(rows),"verified":[r["chunk_hash"] for r in rows if r["status"]=="verified"],"missing":[r["chunk_hash"] for r in rows if r["status"]!="verified"]}

    def _receipt_head(self) -> str | None:
        row=self.conn.execute("SELECT receipt_digest FROM joint_receipts ORDER BY created_at DESC, receipt_digest DESC LIMIT 1").fetchone()
        return row[0] if row else None

    def acquire_promotion_fence(self, session_id: str) -> dict[str, Any]:
        """Acquire a monotonic single-writer fencing epoch; idempotent for an existing session."""
        existing=self.conn.execute("SELECT * FROM sync_promotion_guards WHERE session_id=?",(session_id,)).fetchone()
        if existing: return dict(existing)
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            existing=self.conn.execute("SELECT * FROM sync_promotion_guards WHERE session_id=?",(session_id,)).fetchone()
            if existing:
                self.conn.commit(); return dict(existing)
            epoch=self.conn.execute("SELECT current_epoch FROM promotion_fence_state WHERE singleton=1").fetchone()[0]+1
            self.conn.execute("UPDATE promotion_fence_state SET current_epoch=? WHERE singleton=1",(epoch,))
            head=self._receipt_head(); now=utcnow()
            self.conn.execute("INSERT INTO sync_promotion_guards(session_id,fence_epoch,expected_receipt_head,acquired_at) VALUES (?,?,?,?)",(session_id,epoch,head,now))
            self.conn.commit(); return {"session_id":session_id,"fence_epoch":epoch,"expected_receipt_head":head,"acquired_at":now}
        except Exception:
            self.conn.rollback(); raise

    def _iso_after(self, seconds: int) -> str:
        return (datetime.now(timezone.utc)+timedelta(seconds=seconds)).isoformat().replace("+00:00","Z")

    def acquire_promotion_lease(self, session_id: str, owner_id: str, ttl_seconds: int = 30) -> dict[str, Any]:
        """Bind the current fencing epoch to a temporal owner lease; takeover always gets a newer epoch."""
        if ttl_seconds <= 0: raise ValueError("invalid_lease_ttl")
        now=utcnow(); existing=self.conn.execute("SELECT * FROM promotion_leases WHERE session_id=?",(session_id,)).fetchone()
        if existing and dict(existing)["owner_id"]==owner_id and dict(existing)["expires_at"]>now:
            return dict(existing)
        guard=self.acquire_promotion_fence(session_id)
        # A different/expired owner must receive a fresh epoch, even for the same deterministic session.
        if existing:
            self.conn.execute("DELETE FROM sync_promotion_guards WHERE session_id=?",(session_id,)); self.conn.commit(); guard=self.acquire_promotion_fence(session_id)
        expires=self._iso_after(ttl_seconds)
        self.conn.execute("INSERT OR REPLACE INTO promotion_leases(session_id,owner_id,fence_epoch,acquired_at,expires_at,renewed_at) VALUES (?,?,?,?,?,?)",(session_id,owner_id,guard["fence_epoch"],now,expires,now)); self.conn.commit()
        return dict(self.conn.execute("SELECT * FROM promotion_leases WHERE session_id=?",(session_id,)).fetchone())

    def renew_promotion_lease(self, session_id: str, owner_id: str, ttl_seconds: int = 30) -> dict[str, Any]:
        row=self.conn.execute("SELECT * FROM promotion_leases WHERE session_id=?",(session_id,)).fetchone(); now=utcnow()
        if not row or dict(row)["owner_id"]!=owner_id: raise ValueError("lease_owner_mismatch")
        lease=dict(row)
        if lease["expires_at"] <= now: raise ValueError("promotion_lease_expired")
        current=self.conn.execute("SELECT current_epoch FROM promotion_fence_state WHERE singleton=1").fetchone()[0]
        if lease["fence_epoch"] != current: raise ValueError("stale_fencing_epoch")
        expires=self._iso_after(ttl_seconds); self.conn.execute("UPDATE promotion_leases SET expires_at=?,renewed_at=? WHERE session_id=?",(expires,now,session_id)); self.conn.commit()
        return dict(self.conn.execute("SELECT * FROM promotion_leases WHERE session_id=?",(session_id,)).fetchone())

    def assert_promotion_lease(self, session_id: str, owner_id: str) -> dict[str, Any]:
        row=self.conn.execute("SELECT * FROM promotion_leases WHERE session_id=?",(session_id,)).fetchone(); now=utcnow()
        if not row: raise ValueError("promotion_lease_missing")
        lease=dict(row)
        if lease["owner_id"]!=owner_id: raise ValueError("lease_owner_mismatch")
        if self._lease_expired_with_skew(lease["expires_at"], now): raise ValueError("promotion_lease_expired")
        current=self.conn.execute("SELECT current_epoch FROM promotion_fence_state WHERE singleton=1").fetchone()[0]
        if lease["fence_epoch"] != current: raise ValueError("stale_fencing_epoch")
        return lease

    def _record_receipt_fork(self, session_id: str, guard: dict[str, Any], observed: str | None) -> dict[str, Any]:
        core={"format":"janus-receipt-fork-evidence-v1","session_id":session_id,"fence_epoch":guard["fence_epoch"],"expected_head":guard.get("expected_receipt_head"),"observed_head":observed,"detected_at":utcnow()}
        digest=sha256_bytes(stable_json(core).encode()); evidence={**core,"evidence_digest":digest}
        self.conn.execute("INSERT OR IGNORE INTO receipt_fork_evidence(evidence_digest,session_id,fence_epoch,expected_head,observed_head,detected_at,evidence_json) VALUES (?,?,?,?,?,?,?)",(digest,session_id,guard["fence_epoch"],core["expected_head"],observed,core["detected_at"],stable_json(evidence))); self.conn.commit(); return evidence

    def receipt_fork_evidence(self, session_id: str) -> list[dict[str, Any]]:
        return [json.loads(r[0]) for r in self.conn.execute("SELECT evidence_json FROM receipt_fork_evidence WHERE session_id=? ORDER BY detected_at,evidence_digest",(session_id,))]

    def assert_promotion_guard(self, session_id: str) -> dict[str, Any]:
        guard=self.conn.execute("SELECT * FROM sync_promotion_guards WHERE session_id=?",(session_id,)).fetchone()
        if not guard: raise ValueError("promotion_fence_missing")
        g=dict(guard); current=self.conn.execute("SELECT current_epoch FROM promotion_fence_state WHERE singleton=1").fetchone()[0]
        if g["fence_epoch"] != current: raise ValueError("stale_fencing_epoch")
        observed=self._receipt_head()
        if g.get("expected_receipt_head") != observed:
            self._record_receipt_fork(session_id,g,observed); raise ValueError("receipt_head_changed")
        return g

    def set_clock_skew_policy(self, max_clock_skew_seconds: int) -> dict[str, Any]:
        if max_clock_skew_seconds < 0: raise ValueError("invalid_clock_skew")
        self.conn.execute("UPDATE clock_policy SET max_clock_skew_seconds=? WHERE singleton=1",(max_clock_skew_seconds,)); self.conn.commit()
        return {"max_clock_skew_seconds":max_clock_skew_seconds}

    def _lease_expired_with_skew(self, expires_at: str, now_iso: str | None = None) -> bool:
        skew=self.conn.execute("SELECT max_clock_skew_seconds FROM clock_policy WHERE singleton=1").fetchone()[0]
        now=datetime.fromisoformat((now_iso or utcnow()).replace("Z","+00:00"))
        exp=datetime.fromisoformat(expires_at.replace("Z","+00:00"))
        return now > exp + timedelta(seconds=skew)

    def prepare_promotion_intent(self, session_id: str, owner_id: str) -> dict[str, Any]:
        lease=self.assert_promotion_lease(session_id,owner_id); guard=self.assert_promotion_guard(session_id); session=self.sync_session(session_id)
        now=utcnow()
        self.conn.execute("INSERT INTO promotion_journal(session_id,fence_epoch,owner_id,expected_receipt_head,receiver_state_digest,status,prepared_at) VALUES (?,?,?,?,?,'prepared',?) ON CONFLICT(session_id) DO UPDATE SET fence_epoch=excluded.fence_epoch,owner_id=excluded.owner_id,expected_receipt_head=excluded.expected_receipt_head,receiver_state_digest=excluded.receiver_state_digest,status='prepared',prepared_at=excluded.prepared_at,resolved_at=NULL,receipt_digest=NULL,failure_reason=NULL",(session_id,lease['fence_epoch'],owner_id,guard.get('expected_receipt_head'),session['receiver_state_digest'],now)); self.conn.commit()
        return dict(self.conn.execute("SELECT * FROM promotion_journal WHERE session_id=?",(session_id,)).fetchone())

    def _resolve_promotion_intent(self, session_id: str, outcome: str, receipt_digest: str | None = None, failure_reason: str | None = None) -> dict[str, Any]:
        if outcome not in ('committed','aborted'): raise ValueError('invalid_promotion_outcome')
        now=utcnow()
        existing=self.conn.execute("SELECT 1 FROM promotion_journal WHERE session_id=?",(session_id,)).fetchone()
        if not existing:
            guard=self.conn.execute("SELECT * FROM sync_promotion_guards WHERE session_id=?",(session_id,)).fetchone(); session=self.sync_session(session_id)
            if not guard: raise ValueError('promotion_journal_guard_missing')
            g=dict(guard); lease=self.conn.execute("SELECT owner_id FROM promotion_leases WHERE session_id=?",(session_id,)).fetchone()
            self.conn.execute("INSERT INTO promotion_journal(session_id,fence_epoch,owner_id,expected_receipt_head,receiver_state_digest,status,prepared_at) VALUES (?,?,?,?,?,'prepared',?)",(session_id,g['fence_epoch'],lease[0] if lease else 'recovered',g.get('expected_receipt_head'),session['receiver_state_digest'],now))
        self.conn.execute("UPDATE promotion_journal SET status=?,resolved_at=?,receipt_digest=?,failure_reason=? WHERE session_id=?",(outcome,now,receipt_digest,failure_reason,session_id)); self.conn.commit()
        core={"format":"janus-promotion-recovery-certificate-v1","session_id":session_id,"outcome":outcome,"receipt_digest":receipt_digest,"failure_reason":failure_reason,"resolved_at":now}
        digest=sha256_bytes(stable_json(core).encode()); cert={**core,"certificate_digest":digest}
        self.conn.execute("INSERT OR IGNORE INTO recovery_certificates(certificate_digest,session_id,outcome,certificate_json,created_at) VALUES (?,?,?,?,?)",(digest,session_id,outcome,stable_json(cert),now)); self.conn.commit(); return cert

    def recover_promotion(self, session_id: str) -> dict[str, Any]:
        row=self.conn.execute("SELECT * FROM promotion_journal WHERE session_id=?",(session_id,)).fetchone()
        if not row: raise KeyError(session_id)
        j=dict(row)
        if j['status'] in ('committed','aborted'):
            cert=self.conn.execute("SELECT certificate_json FROM recovery_certificates WHERE session_id=? ORDER BY created_at DESC LIMIT 1",(session_id,)).fetchone()
            return json.loads(cert[0]) if cert else self._resolve_promotion_intent(session_id,j['status'],j.get('receipt_digest'),j.get('failure_reason'))
        receipt=self.conn.execute("SELECT receipt_digest FROM joint_receipts WHERE session_id=? ORDER BY created_at DESC LIMIT 1",(session_id,)).fetchone()
        if receipt: return self._resolve_promotion_intent(session_id,'committed',receipt[0],None)
        return self._resolve_promotion_intent(session_id,'aborted',None,'recovered_uncommitted_promotion')

    def promotion_journal(self, session_id: str) -> dict[str, Any]:
        row=self.conn.execute("SELECT * FROM promotion_journal WHERE session_id=?",(session_id,)).fetchone()
        if not row: raise KeyError(session_id)
        return dict(row)

    def recover_pending_promotions(self) -> list[dict[str, Any]]:
        """Resolve every durable prepared intent exactly once after restart."""
        rows=self.conn.execute("SELECT session_id FROM promotion_journal WHERE status='prepared' ORDER BY prepared_at,session_id").fetchall()
        return [self.recover_promotion(r[0]) for r in rows]

    def sign_joint_receipt(self, receipt: dict[str, Any], authority: str, private_key_b64: str) -> dict[str, Any]:
        statement={"domain":"JANUS_JOINT_RECEIPT_V1","receipt_digest":receipt["receipt_digest"],"previous_receipt_digest":receipt.get("previous_receipt_digest"),"authority":authority}
        sig=Ed25519PrivateKey.from_private_bytes(base64.b64decode(private_key_b64)).sign(stable_json(statement).encode())
        return {**receipt,"signer_authority":authority,"signature":{"algorithm":"Ed25519","statement":statement,"signature_b64":base64.b64encode(sig).decode()}}

    def verify_joint_receipt_signature(self, receipt: dict[str, Any], trust_store: dict[str,str]) -> bool:
        sig=receipt.get("signature",{}); authority=receipt.get("signer_authority")
        if authority not in trust_store or sig.get("algorithm")!="Ed25519": return False
        expected={"domain":"JANUS_JOINT_RECEIPT_V1","receipt_digest":receipt.get("receipt_digest"),"previous_receipt_digest":receipt.get("previous_receipt_digest"),"authority":authority}
        if sig.get("statement")!=expected: return False
        try:
            Ed25519PublicKey.from_public_bytes(base64.b64decode(trust_store[authority])).verify(base64.b64decode(sig.get("signature_b64","")),stable_json(expected).encode()); return True
        except (ValueError,InvalidSignature,TypeError): return False

    def sync_session(self, session_id: str) -> dict[str, Any]:
        row=self.conn.execute("SELECT * FROM sync_sessions WHERE session_id=?",(session_id,)).fetchone()
        if not row: raise KeyError(session_id)
        out=dict(row)
        if out.get("receipt_json"): out["receipt"]=json.loads(out["receipt_json"])
        return out

    def _quarantine_stage(self, session_id: str, stage_path: Path, fault_class: str, integrity_result: str) -> dict[str, Any]:
        detected=utcnow(); qpath=stage_path.with_name(stage_path.name+f".quarantine.{session_id[:12]}")
        digest=None
        if stage_path.exists():
            data=stage_path.read_bytes(); digest=sha256_bytes(data); qpath.write_bytes(data)
        core={"format":"janus-storage-quarantine-v1","session_id":session_id,"fault_class":fault_class,"original_stage_path":str(stage_path),"quarantine_path":str(qpath),"stage_sha256":digest,"integrity_result":integrity_result,"detected_at":detected}
        evidence={**core,"evidence_digest":sha256_bytes(stable_json(core).encode())}
        self.conn.execute("INSERT OR REPLACE INTO storage_quarantine(evidence_digest,session_id,fault_class,original_stage_path,quarantine_path,stage_sha256,integrity_result,detected_at,evidence_json) VALUES (?,?,?,?,?,?,?,?,?)",(evidence["evidence_digest"],session_id,fault_class,str(stage_path),str(qpath),digest,integrity_result,detected,stable_json(evidence))); self.conn.commit()
        return evidence

    def storage_quarantine(self, session_id: str | None = None) -> list[dict[str, Any]]:
        rows=self.conn.execute("SELECT evidence_json FROM storage_quarantine"+(" WHERE session_id=?" if session_id else "")+" ORDER BY detected_at,evidence_digest",((session_id,) if session_id else ())).fetchall()
        return [json.loads(r[0]) for r in rows]

    @staticmethod
    def _wal_checksum(data: bytes, byte_order: str, s0: int = 0, s1: int = 0) -> tuple[int, int]:
        if len(data) % 8:
            raise ValueError("wal_checksum_input_not_8_byte_aligned")
        for i in range(0, len(data), 8):
            x0=int.from_bytes(data[i:i+4],byte_order)
            x1=int.from_bytes(data[i+4:i+8],byte_order)
            s0=(s0+x0+s1)&0xffffffff
            s1=(s1+x1+s0)&0xffffffff
        return s0,s1

    @staticmethod
    def _classify_wal_bytes(wal: Path, data: bytes) -> dict[str, Any]:
        base={"path":str(wal),"exists":True,"sha256":sha256_bytes(data),"size_bytes":len(data),"frame_count":0,"valid_frame_count":0,"first_invalid_frame":None,"checksum_mismatch_frame":None,"salt_mismatch_frame":None,"header_checksum_valid":False,"last_commit_frame":0,"last_commit_checksum":None,"frame_page_numbers":[],"salt_hex":None}
        if len(data)<32:
            return {**base,"classification":"wal_corrupt_header","reason":"header_too_short"}
        magic=int.from_bytes(data[0:4],"big")
        if magic not in (0x377F0682,0x377F0683):
            return {**base,"classification":"wal_corrupt_header","reason":"invalid_magic","magic":f"0x{magic:08x}"}
        byte_order="big" if magic==0x377F0683 else "little"
        version=int.from_bytes(data[4:8],"big")
        raw_page_size=int.from_bytes(data[8:12],"big")
        page_size=65536 if raw_page_size==1 else raw_page_size
        if page_size<512 or page_size>65536 or (page_size & (page_size-1))!=0:
            return {**base,"classification":"wal_corrupt_header","reason":"invalid_page_size","magic":f"0x{magic:08x}","version":version,"page_size":page_size,"checksum_byte_order":byte_order}
        salt1=int.from_bytes(data[16:20],"big"); salt2=int.from_bytes(data[20:24],"big")
        computed_header=JanusTwin._wal_checksum(data[:24],byte_order)
        stored_header=(int.from_bytes(data[24:28],"big"),int.from_bytes(data[28:32],"big"))
        header_ok=computed_header==stored_header
        frame_size=24+page_size
        trailing=(len(data)-32)%frame_size
        frame_count=(len(data)-32)//frame_size
        base.update({"magic":f"0x{magic:08x}","version":version,"page_size":page_size,"checksum_byte_order":byte_order,"salt1":salt1,"salt2":salt2,"salt_hex":data[16:24].hex(),"header_checksum_valid":header_ok,"header_checksum_stored":list(stored_header),"header_checksum_computed":list(computed_header),"frame_size":frame_size,"frame_count":frame_count,"trailing_bytes":trailing})
        if not header_ok:
            return {**base,"classification":"wal_corrupt_header_checksum","reason":"header_checksum_mismatch"}
        if trailing:
            return {**base,"classification":"wal_corrupt_frame_layout","reason":"trailing_or_truncated_frame"}
        s0,s1=computed_header
        commit_frames=0; last_commit_frame=0; last_commit_checksum=None; frame_page_numbers=[]
        for idx in range(frame_count):
            off=32+idx*frame_size; frame=data[off:off+frame_size]; frame_no=idx+1
            page_no=int.from_bytes(frame[0:4],"big"); frame_page_numbers.append(page_no)
            fs1=int.from_bytes(frame[8:12],"big"); fs2=int.from_bytes(frame[12:16],"big")
            if (fs1,fs2)!=(salt1,salt2):
                return {**base,"frame_page_numbers":frame_page_numbers[:-1],"last_commit_frame":last_commit_frame,"last_commit_checksum":last_commit_checksum,"classification":"wal_corrupt_frame_salt","reason":"frame_salt_mismatch","first_invalid_frame":frame_no,"salt_mismatch_frame":frame_no,"valid_frame_count":idx,"commit_frame_count":commit_frames}
            s0,s1=JanusTwin._wal_checksum(frame[:8]+frame[24:],byte_order,s0,s1)
            stored=(int.from_bytes(frame[16:20],"big"),int.from_bytes(frame[20:24],"big"))
            if stored!=(s0,s1):
                return {**base,"frame_page_numbers":frame_page_numbers[:-1],"last_commit_frame":last_commit_frame,"last_commit_checksum":last_commit_checksum,"classification":"wal_corrupt_frame_checksum","reason":"frame_checksum_mismatch","first_invalid_frame":frame_no,"checksum_mismatch_frame":frame_no,"valid_frame_count":idx,"commit_frame_count":commit_frames,"expected_frame_checksum":[s0,s1],"stored_frame_checksum":list(stored)}
            if int.from_bytes(frame[4:8],"big")!=0:
                commit_frames+=1; last_commit_frame=frame_no; last_commit_checksum=[s0,s1]
        return {**base,"classification":"wal_valid","reason":None,"valid_frame_count":frame_count,"commit_frame_count":commit_frames,"last_commit_frame":last_commit_frame,"last_commit_checksum":last_commit_checksum,"frame_page_numbers":frame_page_numbers}

    @staticmethod
    def _classify_shm_bytes(shm: Path, data: bytes, wal_report: dict[str, Any], wal_bytes: bytes | None = None) -> dict[str, Any]:
        import sys
        native=sys.byteorder
        base={"path":str(shm),"exists":True,"sha256":sha256_bytes(data),"size_bytes":len(data),"classification":"shm_corrupt_header","header_copies_identical":False,"header_checksum_valid":False,"frame_map_valid":False,"first_frame_map_mismatch":None}
        if len(data)<136:
            return {**base,"reason":"header_too_short"}
        if len(data)%32768:
            return {**base,"classification":"shm_corrupt_layout","reason":"size_not_32768_multiple"}
        h1=data[:48]; h2=data[48:96]; copies=h1==h2
        version=int.from_bytes(h1[0:4],native); padding=int.from_bytes(h1[4:8],native); is_init=h1[12]; big_ck=h1[13]
        raw_page=int.from_bytes(h1[14:16],native); page_size=65536 if raw_page==1 else raw_page
        mx_frame=int.from_bytes(h1[16:20],native); n_page=int.from_bytes(h1[20:24],native)
        frame_ck=[int.from_bytes(h1[24:28],native),int.from_bytes(h1[28:32],native)]
        salt_hex=h1[32:40].hex(); stored_ck=(int.from_bytes(h1[40:44],native),int.from_bytes(h1[44:48],native))
        computed_ck=JanusTwin._wal_checksum(h1[:40],native); header_ok=stored_ck==computed_ck
        n_backfill=int.from_bytes(data[96:100],native)
        read_marks=[int.from_bytes(data[o:o+4],native) for o in range(100,120,4)]
        n_backfill_attempted=int.from_bytes(data[128:132],native)
        base.update({"header_copies_identical":copies,"header_checksum_valid":header_ok,"version":version,"padding":padding,"is_init":is_init,"big_end_checksum":bool(big_ck),"page_size":page_size,"mx_frame":mx_frame,"n_page":n_page,"frame_checksum":frame_ck,"salt_hex":salt_hex,"header_checksum_stored":list(stored_ck),"header_checksum_computed":list(computed_ck),"n_backfill":n_backfill,"n_backfill_attempted":n_backfill_attempted,"read_marks":read_marks})
        if not copies: return {**base,"classification":"shm_header_copies_diverge","reason":"header_copies_differ"}
        if version!=3007000 or padding!=0 or is_init!=1: return {**base,"classification":"shm_corrupt_header","reason":"invalid_header_fields"}
        if not header_ok: return {**base,"classification":"shm_corrupt_header_checksum","reason":"header_checksum_mismatch"}
        if n_backfill>mx_frame or n_backfill_attempted>mx_frame: return {**base,"classification":"shm_invalid_backfill_horizon","reason":"backfill_exceeds_mx_frame"}
        if wal_report.get("classification")!="wal_valid": return {**base,"classification":"shm_wal_unverifiable","reason":"wal_not_valid"}
        if page_size!=wal_report.get("page_size"): return {**base,"classification":"shm_wal_page_size_mismatch","reason":"page_size_mismatch"}
        if bool(big_ck)!=(wal_report.get("checksum_byte_order")=="big"): return {**base,"classification":"shm_wal_checksum_order_mismatch","reason":"checksum_order_mismatch"}
        if salt_hex!=wal_report.get("salt_hex"): return {**base,"classification":"shm_wal_salt_mismatch","reason":"salt_mismatch"}
        if mx_frame!=wal_report.get("last_commit_frame"): return {**base,"classification":"shm_wal_horizon_mismatch","reason":"mx_frame_not_last_commit_frame"}
        if mx_frame and frame_ck!=wal_report.get("last_commit_checksum"): return {**base,"classification":"shm_wal_frame_checksum_mismatch","reason":"last_commit_checksum_mismatch"}
        pages=wal_report.get("frame_page_numbers",[])
        for frame_no in range(1,mx_frame+1):
            idx=frame_no-1
            if frame_no<=4062:
                off=136+idx*4
            else:
                rem=frame_no-4063; block=1+(rem//4096); within=rem%4096; off=block*32768+within*4
            if off+4>len(data):
                return {**base,"classification":"shm_corrupt_layout","reason":"frame_map_out_of_bounds","first_frame_map_mismatch":frame_no}
            shm_page=int.from_bytes(data[off:off+4],native)
            wal_page=pages[idx] if idx<len(pages) else None
            if wal_page is None or shm_page!=wal_page:
                return {**base,"classification":"shm_wal_frame_map_mismatch","reason":"frame_page_number_mismatch","first_frame_map_mismatch":frame_no,"shm_page_number":shm_page,"wal_page_number":wal_page}
        return {**base,"classification":"shm_consistent","reason":None,"frame_map_valid":True}

    @staticmethod
    def run_host_storage_fault_probe(directory: str | Path, max_file_bytes: int = 1024, attempted_bytes: int = 4096) -> dict[str, Any]:
        root=Path(directory); root.mkdir(parents=True,exist_ok=True); target=root/"rlimit_fsize.probe"
        code=(
            "import errno,json,os,resource,signal,sys\n"
            "path=sys.argv[1]; limit=int(sys.argv[2]); attempted=int(sys.argv[3])\n"
            "resource.setrlimit(resource.RLIMIT_FSIZE,(limit,limit)); signal.signal(signal.SIGXFSZ,signal.SIG_IGN)\n"
            "try:\n"
            " f=open(path,'wb'); f.write(b'X'*attempted); f.flush(); os.fsync(f.fileno()); f.close(); out={'classification':'unexpected_write_success','errno':None,'errno_name':None}\n"
            "except OSError as exc:\n"
            " out={'classification':'kernel_file_size_limit' if exc.errno==errno.EFBIG else 'kernel_storage_error','errno':exc.errno,'errno_name':errno.errorcode.get(exc.errno)}\n"
            "out['resulting_size_bytes']=os.path.getsize(path) if os.path.exists(path) else 0\n"
            "print(json.dumps(out,sort_keys=True))"
        )
        proc=subprocess.run([os.sys.executable,"-c",code,str(target),str(int(max_file_bytes)),str(int(attempted_bytes))],capture_output=True,text=True)
        lines=[x for x in proc.stdout.splitlines() if x.strip()]
        result=json.loads(lines[-1]) if lines else {"classification":"probe_failed","errno":None,"errno_name":None,"resulting_size_bytes":target.stat().st_size if target.exists() else 0}
        core={"format":"janus-host-storage-fault-probe-v1","mechanism":"RLIMIT_FSIZE","max_file_bytes":int(max_file_bytes),"attempted_bytes":int(attempted_bytes),"target_path":str(target),"returncode":proc.returncode,"stderr":proc.stderr.strip(),**result}
        return {**core,"probe_digest":sha256_bytes(stable_json(core).encode())}

    @staticmethod
    def classify_storage_artifacts(db_path: str | Path) -> dict[str, Any]:
        db=Path(db_path); report={"format":"janus-storage-artifact-classification-v2"}
        wal=Path(str(db)+"-wal"); shm=Path(str(db)+"-shm")
        wal_data=wal.read_bytes() if wal.exists() else None
        shm_data=shm.read_bytes() if shm.exists() else None
        if wal_data is None:
            report["wal"]={"path":str(wal),"exists":False,"classification":"absent","sha256":None,"frame_count":0,"valid_frame_count":0,"first_invalid_frame":None,"checksum_mismatch_frame":None,"salt_mismatch_frame":None,"header_checksum_valid":False,"last_commit_frame":0,"last_commit_checksum":None,"frame_page_numbers":[],"salt_hex":None}
        else:
            # Preserve forensic bytes before opening SQLite: SQLite may consume/remove WAL/SHM artifacts.
            report["wal"]=JanusTwin._classify_wal_bytes(wal,wal_data)
        if shm_data is not None:
            report["shm"]=JanusTwin._classify_shm_bytes(shm,shm_data,report["wal"],wal_data)
        else:
            report["shm"]={"path":str(shm),"exists":False,"sha256":None,"classification":"absent","reason":None,"header_copies_identical":False,"header_checksum_valid":False,"frame_map_valid":False,"first_frame_map_mismatch":None}
        try:
            with contextlib.closing(sqlite3.connect(db)) as con: integrity=str(con.execute("PRAGMA integrity_check").fetchone()[0])
        except sqlite3.DatabaseError as exc:
            integrity="database_error:"+str(exc)
        report["main_db"]={"path":str(db),"exists":db.exists(),"sha256":sha256_file(db) if db.exists() else None,"integrity":integrity}
        core=dict(report); report["classification_digest"]=sha256_bytes(stable_json(core).encode()); return report

    @staticmethod
    def classify_storage_artifacts_non_mutating(db_path: str | Path) -> dict[str, Any]:
        """Classify a DB/WAL/SHM snapshot without allowing SQLite recovery to mutate the evidence bytes."""
        db=Path(db_path); wal=Path(str(db)+"-wal"); shm=Path(str(db)+"-shm")
        main_data=db.read_bytes() if db.exists() else None
        wal_data=wal.read_bytes() if wal.exists() else None
        shm_data=shm.read_bytes() if shm.exists() else None
        report={"format":"janus-storage-artifact-classification-v2"}
        if wal_data is None:
            report["wal"]={"path":str(wal),"exists":False,"classification":"absent","sha256":None,"frame_count":0,"valid_frame_count":0,"first_invalid_frame":None,"checksum_mismatch_frame":None,"salt_mismatch_frame":None,"header_checksum_valid":False,"last_commit_frame":0,"last_commit_checksum":None,"frame_page_numbers":[],"salt_hex":None}
        else:
            report["wal"]=JanusTwin._classify_wal_bytes(wal,wal_data)
        if shm_data is not None:
            report["shm"]=JanusTwin._classify_shm_bytes(shm,shm_data,report["wal"],wal_data)
        else:
            report["shm"]={"path":str(shm),"exists":False,"sha256":None,"classification":"absent","reason":None,"header_copies_identical":False,"header_checksum_valid":False,"frame_map_valid":False,"first_frame_map_mismatch":None}
        integrity="missing"
        if main_data is not None:
            with tempfile.TemporaryDirectory() as td:
                work=Path(td)/"snapshot.db"; work.write_bytes(main_data)
                if wal_data is not None: Path(str(work)+"-wal").write_bytes(wal_data)
                if shm_data is not None: Path(str(work)+"-shm").write_bytes(shm_data)
                try:
                    with contextlib.closing(sqlite3.connect(work)) as con: integrity=str(con.execute("PRAGMA integrity_check").fetchone()[0])
                except sqlite3.DatabaseError as exc:
                    integrity="database_error:"+str(exc)
        report["main_db"]={"path":str(db),"exists":main_data is not None,"sha256":sha256_bytes(main_data) if main_data is not None else None,"integrity":integrity}
        core=dict(report); report["classification_digest"]=sha256_bytes(stable_json(core).encode())
        return report

    def sign_storage_fault_evidence(self, evidence_digest: str, authority: str, private_key_b64: str) -> dict[str, Any]:
        row=self.conn.execute("SELECT 1 FROM storage_quarantine WHERE evidence_digest=?",(evidence_digest,)).fetchone()
        if not row: raise KeyError(evidence_digest)
        prev=self.conn.execute("SELECT audit_digest FROM storage_fault_audit ORDER BY created_at DESC,audit_digest DESC LIMIT 1").fetchone(); previous=prev[0] if prev else None
        created=utcnow(); core={"format":"janus-signed-storage-fault-audit-v1","fault_evidence_digest":evidence_digest,"previous_audit_digest":previous,"signer_authority":authority,"created_at":created}
        digest=sha256_bytes(stable_json(core).encode()); statement={"domain":"JANUS_STORAGE_FAULT_AUDIT_V1","audit_digest":digest,"fault_evidence_digest":evidence_digest,"previous_audit_digest":previous,"authority":authority}
        key=Ed25519PrivateKey.from_private_bytes(base64.b64decode(private_key_b64)); sig=base64.b64encode(key.sign(stable_json(statement).encode())).decode()
        audit={**core,"audit_digest":digest,"signature":{"algorithm":"Ed25519","statement":statement,"signature_b64":sig}}
        self.conn.execute("INSERT INTO storage_fault_audit(audit_digest,fault_evidence_digest,previous_audit_digest,signer_authority,signature_b64,audit_json,created_at) VALUES (?,?,?,?,?,?,?)",(digest,evidence_digest,previous,authority,sig,stable_json(audit),created)); self.conn.commit(); return audit

    def verify_storage_fault_audit(self, audit: dict[str, Any], trust_store: dict[str,str]) -> bool:
        authority=audit.get("signer_authority"); sig=audit.get("signature") or {}
        core={k:audit.get(k) for k in ("format","fault_evidence_digest","previous_audit_digest","signer_authority","created_at")}
        digest=sha256_bytes(stable_json(core).encode())
        if digest!=audit.get("audit_digest") or authority not in trust_store or sig.get("algorithm")!="Ed25519": return False
        expected={"domain":"JANUS_STORAGE_FAULT_AUDIT_V1","audit_digest":digest,"fault_evidence_digest":audit.get("fault_evidence_digest"),"previous_audit_digest":audit.get("previous_audit_digest"),"authority":authority}
        if sig.get("statement")!=expected: return False
        try:
            Ed25519PublicKey.from_public_bytes(base64.b64decode(trust_store[authority])).verify(base64.b64decode(sig.get("signature_b64","")),stable_json(expected).encode()); return True
        except (ValueError,InvalidSignature,TypeError): return False

    def sign_forensic_proof_link(self, audit_digest: str, session_id: str, authority: str, private_key_b64: str) -> dict[str, Any]:
        audit_row=self.conn.execute("SELECT audit_json FROM storage_fault_audit WHERE audit_digest=?",(audit_digest,)).fetchone()
        if not audit_row: raise KeyError(audit_digest)
        audit=json.loads(audit_row[0])
        cert_row=self.conn.execute("SELECT certificate_digest,certificate_json FROM recovery_certificates WHERE session_id=? ORDER BY created_at DESC,certificate_digest DESC LIMIT 1",(session_id,)).fetchone()
        if not cert_row: raise ValueError("recovery_certificate_required")
        journal=self.conn.execute("SELECT fence_epoch FROM promotion_journal WHERE session_id=?",(session_id,)).fetchone()
        session_receipt=self.conn.execute("SELECT receipt_digest FROM joint_receipts WHERE session_id=? ORDER BY created_at DESC,receipt_digest DESC LIMIT 1",(session_id,)).fetchone()
        receipt_head=self._receipt_head()
        prev=self.conn.execute("SELECT link_digest FROM forensic_proof_links ORDER BY created_at DESC,link_digest DESC LIMIT 1").fetchone(); previous=prev[0] if prev else None
        created=utcnow()
        core={"format":"janus-forensic-proof-link-v1","audit_digest":audit_digest,"fault_evidence_digest":audit["fault_evidence_digest"],"session_id":session_id,"recovery_certificate_digest":cert_row[0],"session_receipt_digest":session_receipt[0] if session_receipt else None,"receipt_head_digest":receipt_head,"fence_epoch":journal[0] if journal else None,"previous_link_digest":previous,"signer_authority":authority,"created_at":created}
        digest=sha256_bytes(stable_json(core).encode())
        statement={"domain":"JANUS_FORENSIC_PROOF_LINK_V1","link_digest":digest,"audit_digest":audit_digest,"recovery_certificate_digest":cert_row[0],"session_receipt_digest":core["session_receipt_digest"],"receipt_head_digest":receipt_head,"authority":authority}
        sig=base64.b64encode(Ed25519PrivateKey.from_private_bytes(base64.b64decode(private_key_b64)).sign(stable_json(statement).encode())).decode()
        link={**core,"link_digest":digest,"signature":{"algorithm":"Ed25519","statement":statement,"signature_b64":sig}}
        self.conn.execute("INSERT INTO forensic_proof_links(link_digest,audit_digest,session_id,recovery_certificate_digest,session_receipt_digest,receipt_head_digest,fence_epoch,previous_link_digest,signer_authority,signature_b64,link_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",(digest,audit_digest,session_id,cert_row[0],core["session_receipt_digest"],receipt_head,core["fence_epoch"],previous,authority,sig,stable_json(link),created)); self.conn.commit(); return link

    def verify_forensic_proof_link(self, link: dict[str, Any], trust_store: dict[str,str]) -> bool:
        authority=link.get("signer_authority"); sig=link.get("signature") or {}
        core={k:link.get(k) for k in ("format","audit_digest","fault_evidence_digest","session_id","recovery_certificate_digest","session_receipt_digest","receipt_head_digest","fence_epoch","previous_link_digest","signer_authority","created_at")}
        digest=sha256_bytes(stable_json(core).encode())
        if digest!=link.get("link_digest") or authority not in trust_store or sig.get("algorithm")!="Ed25519": return False
        expected={"domain":"JANUS_FORENSIC_PROOF_LINK_V1","link_digest":digest,"audit_digest":link.get("audit_digest"),"recovery_certificate_digest":link.get("recovery_certificate_digest"),"session_receipt_digest":link.get("session_receipt_digest"),"receipt_head_digest":link.get("receipt_head_digest"),"authority":authority}
        if sig.get("statement")!=expected: return False
        try:
            Ed25519PublicKey.from_public_bytes(base64.b64decode(trust_store[authority])).verify(base64.b64decode(sig.get("signature_b64","")),stable_json(expected).encode()); return True
        except (ValueError,InvalidSignature,TypeError): return False

    def build_forensic_proof_dag(self, root_link_digest: str) -> dict[str, Any]:
        nodes: dict[str,dict[str,Any]]={}; edges: set[tuple[str,str,str]]=set()
        def add(kind: str, digest: str, payload: dict[str,Any]):
            nodes[f"{kind}:{digest}"]={"id":f"{kind}:{digest}","kind":kind,"digest":digest,"payload":payload}
        link_queue=[root_link_digest]; audit_queue=[]; receipt_queue=[]
        seen_links=set(); seen_audits=set(); seen_receipts=set()
        while link_queue:
            d=link_queue.pop(0)
            if d in seen_links: continue
            seen_links.add(d); row=self.conn.execute("SELECT link_json FROM forensic_proof_links WHERE link_digest=?",(d,)).fetchone()
            if not row: raise KeyError(d)
            link=json.loads(row[0]); add("forensic_link",d,link)
            audit_queue.append(link["audit_digest"]); edges.add((f"forensic_link:{d}",f"storage_audit:{link['audit_digest']}","binds_audit"))
            rc=link["recovery_certificate_digest"]; rr=self.conn.execute("SELECT certificate_json FROM recovery_certificates WHERE certificate_digest=?",(rc,)).fetchone()
            if not rr: raise KeyError(rc)
            add("recovery_certificate",rc,json.loads(rr[0])); edges.add((f"forensic_link:{d}",f"recovery_certificate:{rc}","binds_recovery"))
            for rel,key in (("binds_session_receipt","session_receipt_digest"),("binds_receipt_head","receipt_head_digest")):
                rd=link.get(key)
                if rd: receipt_queue.append(rd); edges.add((f"forensic_link:{d}",f"receipt:{rd}",rel))
            prev=link.get("previous_link_digest")
            if prev: link_queue.append(prev); edges.add((f"forensic_link:{d}",f"forensic_link:{prev}","previous_link"))
        while audit_queue:
            d=audit_queue.pop(0)
            if d in seen_audits: continue
            seen_audits.add(d); row=self.conn.execute("SELECT audit_json FROM storage_fault_audit WHERE audit_digest=?",(d,)).fetchone()
            if not row: raise KeyError(d)
            audit=json.loads(row[0]); add("storage_audit",d,audit)
            qd=audit["fault_evidence_digest"]; qr=self.conn.execute("SELECT evidence_json FROM storage_quarantine WHERE evidence_digest=?",(qd,)).fetchone()
            if not qr: raise KeyError(qd)
            add("quarantine",qd,json.loads(qr[0])); edges.add((f"storage_audit:{d}",f"quarantine:{qd}","attests_quarantine"))
            prev=audit.get("previous_audit_digest")
            if prev: audit_queue.append(prev); edges.add((f"storage_audit:{d}",f"storage_audit:{prev}","previous_audit"))
        while receipt_queue:
            d=receipt_queue.pop(0)
            if d in seen_receipts: continue
            seen_receipts.add(d); row=self.conn.execute("SELECT receipt_json FROM joint_receipts WHERE receipt_digest=?",(d,)).fetchone()
            if not row: raise KeyError(d)
            receipt=json.loads(row[0]); add("receipt",d,receipt)
            prev=receipt.get("previous_receipt_digest")
            if prev: receipt_queue.append(prev); edges.add((f"receipt:{d}",f"receipt:{prev}","previous_receipt"))
        node_list=sorted(nodes.values(),key=lambda n:n["id"]); edge_list=[{"from":a,"to":b,"relation":r} for a,b,r in sorted(edges)]
        core={"format":"janus-forensic-proof-dag-v1","root_link_digest":root_link_digest,"nodes":node_list,"edges":edge_list}
        return {**core,"dag_digest":sha256_bytes(stable_json(core).encode())}

    def verify_forensic_proof_dag(self, dag: dict[str, Any], trust_store: dict[str,str]) -> dict[str, Any]:
        errors=[]
        if dag.get("format")!="janus-forensic-proof-dag-v1": errors.append("unsupported_format")
        core={k:dag.get(k) for k in ("format","root_link_digest","nodes","edges")}; computed=sha256_bytes(stable_json(core).encode())
        if computed!=dag.get("dag_digest"): errors.append("dag_digest_mismatch")
        nodes={n.get("id"):n for n in dag.get("nodes",[]) if isinstance(n,dict) and n.get("id")}
        if len(nodes)!=len(dag.get("nodes",[])): errors.append("duplicate_or_invalid_node_id")
        for node in nodes.values():
            kind=node.get("kind"); payload=node.get("payload") or {}; digest=node.get("digest")
            if node.get("id")!=f"{kind}:{digest}": errors.append("node_id_digest_mismatch")
            if kind=="quarantine":
                qcore={k:payload.get(k) for k in ("format","session_id","fault_class","original_stage_path","quarantine_path","stage_sha256","integrity_result","detected_at")}
                if sha256_bytes(stable_json(qcore).encode())!=digest or payload.get("evidence_digest")!=digest: errors.append("quarantine_digest_mismatch")
            elif kind=="recovery_certificate":
                rcore={k:payload.get(k) for k in ("format","session_id","outcome","receipt_digest","failure_reason","resolved_at")}
                if sha256_bytes(stable_json(rcore).encode())!=digest or payload.get("certificate_digest")!=digest: errors.append("recovery_certificate_digest_mismatch")
            elif kind=="storage_audit":
                if payload.get("audit_digest")!=digest or not self.verify_storage_fault_audit(payload,trust_store): errors.append("storage_audit_invalid")
            elif kind=="forensic_link":
                if payload.get("link_digest")!=digest or not self.verify_forensic_proof_link(payload,trust_store): errors.append("forensic_link_invalid")
            elif kind=="receipt":
                rcore={k:v for k,v in payload.items() if k not in ("receipt_digest","signer_authority","signature")}
                if sha256_bytes(stable_json(rcore).encode())!=digest or payload.get("receipt_digest")!=digest: errors.append("receipt_digest_mismatch")
                if payload.get("signature") and not self.verify_joint_receipt_signature(payload,trust_store): errors.append("receipt_signature_invalid")
            else: errors.append("unknown_node_kind:"+str(kind))
        adjacency={k:[] for k in nodes}; edge_keys=set()
        for e in dag.get("edges",[]):
            a=e.get("from"); b=e.get("to"); rel=e.get("relation"); edge_keys.add((a,b,rel))
            if a not in nodes or b not in nodes: errors.append("edge_target_missing")
            elif b not in adjacency[a]: adjacency[a].append(b)
        def require(src: str, dst: str | None, rel: str):
            if not dst: return
            if dst not in nodes or (src,dst,rel) not in edge_keys: errors.append("referenced_node_missing")
        for node_id,node in nodes.items():
            payload=node.get("payload") or {}; kind=node.get("kind")
            if kind=="forensic_link":
                require(node_id,"storage_audit:"+str(payload.get("audit_digest")),"binds_audit")
                require(node_id,"recovery_certificate:"+str(payload.get("recovery_certificate_digest")),"binds_recovery")
                if payload.get("session_receipt_digest"): require(node_id,"receipt:"+payload["session_receipt_digest"],"binds_session_receipt")
                if payload.get("receipt_head_digest"): require(node_id,"receipt:"+payload["receipt_head_digest"],"binds_receipt_head")
                if payload.get("previous_link_digest"): require(node_id,"forensic_link:"+payload["previous_link_digest"],"previous_link")
            elif kind=="storage_audit":
                require(node_id,"quarantine:"+str(payload.get("fault_evidence_digest")),"attests_quarantine")
                if payload.get("previous_audit_digest"): require(node_id,"storage_audit:"+payload["previous_audit_digest"],"previous_audit")
            elif kind=="receipt" and payload.get("previous_receipt_digest"):
                require(node_id,"receipt:"+payload["previous_receipt_digest"],"previous_receipt")
        visiting=set(); visited=set()
        def cyc(n):
            if n in visiting: return True
            if n in visited: return False
            visiting.add(n)
            for m in adjacency.get(n,[]):
                if cyc(m): return True
            visiting.remove(n); visited.add(n); return False
        if any(cyc(n) for n in list(nodes) if n not in visited): errors.append("dag_cycle_detected")
        root=f"forensic_link:{dag.get('root_link_digest')}"
        if root not in nodes: errors.append("root_link_missing")
        return {"valid":not errors,"errors":sorted(set(errors)),"dag_digest":computed,"node_count":len(nodes),"edge_count":len(dag.get("edges",[]))}

    @staticmethod
    def _portable_storage_summary(report: dict[str, Any]) -> dict[str, Any]:
        """Strip host-specific paths while retaining the bytes/horizons needed for portable verification."""
        wal=report.get("wal") or {}; shm=report.get("shm") or {}; main=report.get("main_db") or {}
        return {
            "format":"janus-portable-storage-state-v1",
            "main_db":{"exists":bool(main.get("exists")),"sha256":main.get("sha256"),"integrity":main.get("integrity")},
            "wal":{k:wal.get(k) for k in ("exists","sha256","classification","frame_count","valid_frame_count","last_commit_frame","last_commit_checksum","salt_hex","page_size")},
            "shm":{k:shm.get(k) for k in ("exists","sha256","classification","mx_frame","frame_checksum","salt_hex","n_backfill","n_backfill_attempted","frame_map_valid")},
        }

    def build_storage_state_certificate(self, session_id: str, authority: str, private_key_b64: str, root_link_digest: str | None = None) -> dict[str, Any]:
        """Build a non-self-mutating signed certificate over storage and proof state.

        The certificate is intentionally returned rather than persisted into this database so
        its own write cannot change the database hash that it attests.
        """
        journal=self.conn.execute("SELECT fence_epoch FROM promotion_journal WHERE session_id=?",(session_id,)).fetchone()
        if not journal: raise ValueError("promotion_journal_required")
        recovery=self.conn.execute("SELECT certificate_digest FROM recovery_certificates WHERE session_id=? ORDER BY created_at DESC,certificate_digest DESC LIMIT 1",(session_id,)).fetchone()
        if not recovery: raise ValueError("recovery_certificate_required")
        storage_report=self.classify_storage_artifacts_non_mutating(self.db_path)
        storage_state=self._portable_storage_summary(storage_report)
        storage_state_digest=sha256_bytes(stable_json(storage_state).encode())
        quarantine=[r[0] for r in self.conn.execute("SELECT evidence_digest FROM storage_quarantine WHERE session_id=? ORDER BY evidence_digest",(session_id,))]
        receipt_head=self._receipt_head()
        forensic_dag_digest=None; forensic_root_link_digest=None
        if root_link_digest:
            link_row=self.conn.execute("SELECT link_json FROM forensic_proof_links WHERE link_digest=?",(root_link_digest,)).fetchone()
            if not link_row: raise KeyError(root_link_digest)
            link=json.loads(link_row[0])
            if link.get("session_id")!=session_id: raise ValueError("forensic_link_session_mismatch")
            if link.get("recovery_certificate_digest")!=recovery[0]: raise ValueError("forensic_link_recovery_mismatch")
            if link.get("receipt_head_digest")!=receipt_head: raise ValueError("forensic_link_receipt_head_mismatch")
            if link.get("fault_evidence_digest") not in quarantine: raise ValueError("forensic_link_quarantine_mismatch")
            forensic_root_link_digest=root_link_digest
            forensic_dag_digest=self.build_forensic_proof_dag(root_link_digest)["dag_digest"]
        created=utcnow()
        core={
            "format":"janus-storage-state-certificate-v1",
            "session_id":session_id,
            "project_state_digest":self.state_digest(),
            "storage_state":storage_state,
            "storage_state_digest":storage_state_digest,
            "fence_epoch":journal[0],
            "receipt_head_digest":receipt_head,
            "recovery_certificate_digest":recovery[0],
            "forensic_root_link_digest":forensic_root_link_digest,
            "forensic_dag_digest":forensic_dag_digest,
            "quarantine_evidence_digests":quarantine,
            "signer_authority":authority,
            "created_at":created,
        }
        digest=sha256_bytes(stable_json(core).encode())
        statement={
            "domain":"JANUS_STORAGE_STATE_CERTIFICATE_V1",
            "certificate_digest":digest,
            "session_id":session_id,
            "project_state_digest":core["project_state_digest"],
            "storage_state_digest":storage_state_digest,
            "receipt_head_digest":core["receipt_head_digest"],
            "recovery_certificate_digest":core["recovery_certificate_digest"],
            "forensic_root_link_digest":forensic_root_link_digest,
            "forensic_dag_digest":forensic_dag_digest,
            "authority":authority,
        }
        sig=base64.b64encode(Ed25519PrivateKey.from_private_bytes(base64.b64decode(private_key_b64)).sign(stable_json(statement).encode())).decode()
        return {**core,"certificate_digest":digest,"signature":{"algorithm":"Ed25519","statement":statement,"signature_b64":sig}}

    def verify_storage_state_certificate(self, certificate: dict[str, Any], trust_store: dict[str,str], forensic_dag: dict[str, Any] | None = None, db_path: str | Path | None = None) -> dict[str, Any]:
        errors=[]
        if certificate.get("format")!="janus-storage-state-certificate-v1": errors.append("unsupported_format")
        core={k:certificate.get(k) for k in ("format","session_id","project_state_digest","storage_state","storage_state_digest","fence_epoch","receipt_head_digest","recovery_certificate_digest","forensic_root_link_digest","forensic_dag_digest","quarantine_evidence_digests","signer_authority","created_at")}
        digest=sha256_bytes(stable_json(core).encode())
        if digest!=certificate.get("certificate_digest"): errors.append("certificate_digest_mismatch")
        storage_state=certificate.get("storage_state") or {}
        if sha256_bytes(stable_json(storage_state).encode())!=certificate.get("storage_state_digest"): errors.append("storage_state_digest_mismatch")
        authority=certificate.get("signer_authority"); sig=certificate.get("signature") or {}
        expected={
            "domain":"JANUS_STORAGE_STATE_CERTIFICATE_V1","certificate_digest":digest,"session_id":certificate.get("session_id"),
            "project_state_digest":certificate.get("project_state_digest"),"storage_state_digest":certificate.get("storage_state_digest"),
            "receipt_head_digest":certificate.get("receipt_head_digest"),"recovery_certificate_digest":certificate.get("recovery_certificate_digest"),
            "forensic_root_link_digest":certificate.get("forensic_root_link_digest"),"forensic_dag_digest":certificate.get("forensic_dag_digest"),"authority":authority,
        }
        if authority not in trust_store or sig.get("algorithm")!="Ed25519" or sig.get("statement")!=expected:
            errors.append("signature_invalid")
        else:
            try:
                Ed25519PublicKey.from_public_bytes(base64.b64decode(trust_store[authority])).verify(base64.b64decode(sig.get("signature_b64","")),stable_json(expected).encode())
            except (ValueError,InvalidSignature,TypeError): errors.append("signature_invalid")
        sid=certificate.get("session_id")
        if self.state_digest()!=certificate.get("project_state_digest"): errors.append("project_state_digest_mismatch")
        journal=self.conn.execute("SELECT fence_epoch FROM promotion_journal WHERE session_id=?",(sid,)).fetchone()
        if not journal or journal[0]!=certificate.get("fence_epoch"): errors.append("fence_epoch_mismatch")
        recovery=self.conn.execute("SELECT certificate_digest FROM recovery_certificates WHERE session_id=? ORDER BY created_at DESC,certificate_digest DESC LIMIT 1",(sid,)).fetchone()
        if not recovery or recovery[0]!=certificate.get("recovery_certificate_digest"): errors.append("recovery_certificate_mismatch")
        if self._receipt_head()!=certificate.get("receipt_head_digest"): errors.append("receipt_head_mismatch")
        local_q=[r[0] for r in self.conn.execute("SELECT evidence_digest FROM storage_quarantine WHERE session_id=? ORDER BY evidence_digest",(sid,))]
        if local_q!=certificate.get("quarantine_evidence_digests"): errors.append("quarantine_closure_mismatch")
        if certificate.get("forensic_dag_digest"):
            if forensic_dag is None: errors.append("forensic_dag_required")
            else:
                dag_verification=self.verify_forensic_proof_dag(forensic_dag,trust_store)
                if not dag_verification.get("valid"): errors.append("forensic_dag_invalid")
                if forensic_dag.get("dag_digest")!=certificate.get("forensic_dag_digest"): errors.append("forensic_dag_digest_mismatch")
                if forensic_dag.get("root_link_digest")!=certificate.get("forensic_root_link_digest"): errors.append("forensic_root_link_mismatch")
                root_id="forensic_link:"+str(certificate.get("forensic_root_link_digest"))
                root_node=next((n for n in forensic_dag.get("nodes",[]) if n.get("id")==root_id),None)
                root_payload=(root_node or {}).get("payload") or {}
                if root_payload.get("session_id")!=sid: errors.append("forensic_session_mismatch")
                if root_payload.get("recovery_certificate_digest")!=certificate.get("recovery_certificate_digest"): errors.append("forensic_recovery_mismatch")
                if root_payload.get("receipt_head_digest")!=certificate.get("receipt_head_digest"): errors.append("forensic_receipt_head_mismatch")
                if root_payload.get("fault_evidence_digest") not in (certificate.get("quarantine_evidence_digests") or []): errors.append("forensic_quarantine_mismatch")
        observed=self.classify_storage_artifacts_non_mutating(db_path or self.db_path)
        observed_state=self._portable_storage_summary(observed)
        observed_digest=sha256_bytes(stable_json(observed_state).encode())
        if observed_digest!=certificate.get("storage_state_digest"): errors.append("observed_storage_state_mismatch")
        return {"valid":not errors,"errors":sorted(set(errors)),"certificate_digest":digest,"observed_storage_state_digest":observed_digest}

    @staticmethod
    def run_host_permission_fault_probe(directory: str | Path) -> dict[str, Any]:
        """Exercise a kernel-enforced write-denial path on an isolated scratch file."""
        import errno, tempfile
        requested=Path(directory); requested.mkdir(parents=True,exist_ok=True)
        # Root can bypass mode bits, so use a world-traversable /tmp scratch root and drop
        # privileges in the child. Non-root callers can use the requested scratch directory.
        if hasattr(os,"geteuid") and os.geteuid()==0:
            scratch=Path(tempfile.mkdtemp(prefix="janus-permission-probe-",dir="/tmp"))
        else:
            scratch=requested
        try:
            scratch.chmod(0o755)
        except OSError:
            pass
        target=scratch/"readonly.probe"; target.write_bytes(b"JANUS\n"); target.chmod(0o444)
        code=(
            "import errno,json,os,sys\n"
            "p=sys.argv[1]\n"
            "if hasattr(os,'geteuid') and os.geteuid()==0:\n"
            " try: os.setgid(65534); os.setuid(65534)\n"
            " except OSError: pass\n"
            "try:\n"
            " f=open(p,'wb'); f.write(b'X'); f.flush(); os.fsync(f.fileno()); f.close(); out={'classification':'unexpected_write_success','errno':None,'errno_name':None,'write_succeeded':True}\n"
            "except OSError as exc:\n"
            " denied=exc.errno in (errno.EACCES,errno.EPERM,errno.EROFS); out={'classification':'kernel_write_denied' if denied else 'kernel_storage_error','errno':exc.errno,'errno_name':errno.errorcode.get(exc.errno),'write_succeeded':False}\n"
            "print(json.dumps(out,sort_keys=True))"
        )
        proc=subprocess.run([os.sys.executable,"-c",code,str(target)],capture_output=True,text=True)
        lines=[x for x in proc.stdout.splitlines() if x.strip()]
        result=json.loads(lines[-1]) if lines else {"classification":"probe_failed","errno":None,"errno_name":None,"write_succeeded":False}
        core={"format":"janus-host-permission-fault-probe-v1","mechanism":"filesystem_mode_bits","requested_directory":str(requested),"target_path":str(target),"returncode":proc.returncode,"stderr":proc.stderr.strip(),**result}
        return {**core,"probe_digest":sha256_bytes(stable_json(core).encode())}

    @staticmethod
    def live_reconciliation_gate(repo_path: str | Path, expected_hashes: dict[str,str] | None = None) -> dict[str, Any]:
        """Fail closed unless a clean Git checkout matches every supplied expected artifact hash."""
        repo=Path(repo_path); expected_hashes=expected_hashes or {}
        def run(*args: str):
            return subprocess.run(["git","-C",str(repo),*args],capture_output=True,text=True)
        if not repo.exists():
            core={"format":"janus-live-reconciliation-gate-v1","repo_path":str(repo),"status":"git_repository_unavailable","ready_to_commit":False,"commit_sha":None,"branch":None,"dirty":None,"files":{}}
            return {**core,"gate_digest":sha256_bytes(stable_json(core).encode())}
        probe=run("rev-parse","--is-inside-work-tree")
        if probe.returncode!=0 or probe.stdout.strip()!="true":
            core={"format":"janus-live-reconciliation-gate-v1","repo_path":str(repo),"status":"git_repository_unavailable","ready_to_commit":False,"commit_sha":None,"branch":None,"dirty":None,"files":{}}
            return {**core,"gate_digest":sha256_bytes(stable_json(core).encode())}
        commit=run("rev-parse","HEAD"); branch=run("rev-parse","--abbrev-ref","HEAD"); porcelain=run("status","--porcelain")
        dirty=bool(porcelain.stdout.strip())
        if commit.returncode!=0:
            core={"format":"janus-live-reconciliation-gate-v1","repo_path":str(repo),"status":"git_head_unavailable","ready_to_commit":False,"commit_sha":None,"branch":branch.stdout.strip() if branch.returncode==0 else None,"dirty":dirty,"files":{}}
            return {**core,"gate_digest":sha256_bytes(stable_json(core).encode())}
        if not expected_hashes:
            status="worktree_dirty" if dirty else "expected_hashes_required"
            core={"format":"janus-live-reconciliation-gate-v1","repo_path":str(repo),"status":status,"ready_to_commit":False,"commit_sha":commit.stdout.strip(),"branch":branch.stdout.strip() if branch.returncode==0 else None,"dirty":dirty,"files":{}}
            return {**core,"gate_digest":sha256_bytes(stable_json(core).encode())}
        files={}; mismatch=False; missing=False; invalid_path=False
        root=repo.resolve()
        for rel,expected in sorted(expected_hashes.items()):
            candidate=(repo/rel).resolve()
            try: candidate.relative_to(root)
            except ValueError:
                invalid_path=True; files[rel]={"exists":False,"expected_sha256":expected,"actual_sha256":None,"match":False,"error":"path_outside_repo"}; continue
            exists=candidate.is_file(); actual=sha256_file(candidate) if exists else None; match=exists and actual==expected
            files[rel]={"exists":exists,"expected_sha256":expected,"actual_sha256":actual,"match":match}
            if not exists: missing=True
            elif not match: mismatch=True
        if dirty: status="worktree_dirty"
        elif invalid_path: status="expected_artifact_path_invalid"
        elif missing: status="expected_artifact_missing"
        elif mismatch: status="expected_artifact_hash_mismatch"
        else: status="reconciled"
        core={"format":"janus-live-reconciliation-gate-v1","repo_path":str(repo),"status":status,"ready_to_commit":status=="reconciled","commit_sha":commit.stdout.strip() if commit.returncode==0 else None,"branch":branch.stdout.strip() if branch.returncode==0 else None,"dirty":dirty,"files":files}
        return {**core,"gate_digest":sha256_bytes(stable_json(core).encode())}

    def atomic_joint_sync(self, causal_bundle: dict[str, Any], causal_manifest: dict[str, Any], local_causal_chunks: dict[str, Any], fetched_causal_chunks: dict[str, Any], trust_bundle: dict[str, Any], envelopes: list[dict[str, Any]], receipt_signer: tuple[str,str] | None = None, crash_at: str | None = None, hard_crash_at: str | None = None, storage_fault_at: str | None = None, hard_wait_at: str | None = None) -> dict[str, Any]:
        """Replay portable trust + causal evidence on an isolated DB and promote only a fully reproduced state."""
        sid=self.begin_sync_session(causal_bundle,causal_manifest,trust_bundle)
        session=self.sync_session(sid)
        guard=self.acquire_promotion_fence(sid)
        lease=self.acquire_promotion_lease(sid,"atomic:"+sid,30)
        # Persist transfer inventory before replay; repeated calls are idempotent and reuse verified chunks.
        combined={**local_causal_chunks,**fetched_causal_chunks}
        self.checkpoint_sync_chunks(sid,"causal",list(causal_manifest.get("leaves",[])),combined)
        trust_manifest=self.build_trust_lineage_merkle_manifest(trust_bundle)
        self.checkpoint_sync_chunks(sid,"trust",list(trust_manifest.get("leaves",[])),trust_bundle.get("chunks",{}))
        stage_path=self.db_path.with_name(self.db_path.name+f".{sid[:12]}.stage")
        for suffix in ("", "-wal", "-shm"):
            try: Path(str(stage_path)+suffix).unlink()
            except FileNotFoundError: pass
        stage=JanusTwin(stage_path)
        try:
            self.conn.backup(stage.conn)
            auth=stage.import_and_replay_trust_lineage(trust_bundle,envelopes,causal_manifest)
            causal=stage.incremental_sync_causal_evidence(causal_bundle,causal_manifest,local_causal_chunks,fetched_causal_chunks)
            if auth.get("authorization_decision_digest") != trust_bundle.get("authorization_decision_digest"):
                raise ValueError("joint_authorization_reproduction_failed")
            if causal.get("certificate_digest") != causal_bundle.get("certificate",{}).get("digest"):
                raise ValueError("joint_causal_reproduction_failed")
            if self.state_digest()!=session.get("receiver_state_digest"):
                raise ValueError("concurrent_receiver_state_changed")
            self.assert_promotion_lease(sid,"atomic:"+sid)
            guard=self.assert_promotion_guard(sid)
            journal=self.prepare_promotion_intent(sid,"atomic:"+sid)
            # Copy the durable prepared intent into staging so a promoted database still
            # contains an unresolved journal if the process dies before resolution.
            stage.conn.execute("INSERT OR REPLACE INTO promotion_journal(session_id,fence_epoch,owner_id,expected_receipt_head,receiver_state_digest,status,prepared_at,resolved_at,receipt_digest,failure_reason) VALUES (?,?,?,?,?,?,?,?,?,?)", tuple(journal.get(k) for k in ("session_id","fence_epoch","owner_id","expected_receipt_head","receiver_state_digest","status","prepared_at","resolved_at","receipt_digest","failure_reason")))
            stage.conn.commit()
            if hard_crash_at=="after_prepare": os._exit(86)
            if hard_wait_at=="after_prepare":
                while True: time.sleep(1)
            if crash_at=="after_prepare": raise RuntimeError("injected_crash_after_prepare")
            if crash_at=="before_promotion": raise RuntimeError("injected_crash_before_promotion")
            previous=guard.get("expected_receipt_head")
            receipt_core={"format":"janus-joint-proof-receipt-v1","previous_receipt_digest":previous,"fence_epoch":guard["fence_epoch"],"lease_owner":"atomic:"+sid,"lease_expires_at":lease["expires_at"],"expected_receipt_head":previous,"session_id":sid,"change_id":causal_bundle["change_id"],"causal_merkle_root":causal_manifest["root_digest"],"trust_bundle_digest":trust_bundle["bundle_digest"],"authorization_decision_digest":auth["authorization_decision_digest"],"causal_certificate_digest":causal["certificate_digest"],"subsystem":trust_bundle["subsystem"],"evidence_class":trust_bundle["evidence_class"],"valid_at":trust_bundle["valid_at"],"known_at":trust_bundle["known_at"],"verified":True}
            receipt={**receipt_core,"receipt_digest":sha256_bytes(stable_json(receipt_core).encode())}
            if receipt_signer: receipt=self.sign_joint_receipt(receipt,receipt_signer[0],receipt_signer[1])
            stage.conn.execute("INSERT INTO joint_receipts(receipt_digest,session_id,previous_receipt_digest,signer_authority,signature_b64,receipt_json,created_at) VALUES (?,?,?,?,?,?,?)",(receipt["receipt_digest"],sid,previous,receipt.get("signer_authority"),(receipt.get("signature") or {}).get("signature_b64"),stable_json(receipt),utcnow()))
            stage.conn.execute("UPDATE sync_sessions SET status='completed',updated_at=?,receipt_json=?,failure_reason=NULL WHERE session_id=?",(utcnow(),stable_json(receipt),sid)); stage.conn.commit()
            if storage_fault_at == "enospc_before_promotion":
                raise OSError("ENOSPC: injected storage write failure before promotion")
            if storage_fault_at in ("corrupt_stage_before_promotion","truncate_stage_before_promotion"):
                stage.close()
                raw=stage_path.read_bytes()
                if storage_fault_at == "truncate_stage_before_promotion":
                    stage_path.write_bytes(raw[:max(64,len(raw)//5)])
                else:
                    damaged=bytearray(raw); damaged[:min(256,len(damaged))]=b"JANUS-CORRUPT"*20; stage_path.write_bytes(bytes(damaged))
                integrity="unreadable"
                try:
                    with contextlib.closing(sqlite3.connect(stage_path)) as probe: integrity=str(probe.execute("PRAGMA integrity_check").fetchone()[0])
                except sqlite3.DatabaseError as err:
                    integrity="database_error:"+str(err)
                self._quarantine_stage(sid,stage_path,storage_fault_at,integrity)
                raise ValueError("storage_stage_integrity_failed:"+integrity)
            integrity=stage.conn.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                self._quarantine_stage(sid,stage_path,"unexpected_stage_integrity_failure",str(integrity))
                raise ValueError("storage_stage_integrity_failed:"+str(integrity))
            stage.conn.backup(self.conn); self.conn.commit()
            if hard_crash_at=="after_promotion_backup": os._exit(86)
            if hard_wait_at=="after_promotion_backup":
                while True: time.sleep(1)
            self._resolve_promotion_intent(sid,'committed',receipt["receipt_digest"],None)
            return receipt
        except Exception as exc:
            self.conn.execute("UPDATE sync_sessions SET status='failed',updated_at=?,failure_reason=? WHERE session_id=?",(utcnow(),str(exc),sid)); self.conn.commit()
            j=self.conn.execute("SELECT status FROM promotion_journal WHERE session_id=?",(sid,)).fetchone()
            if j and j[0]=='prepared': self._resolve_promotion_intent(sid,'aborted',None,str(exc))
            raise
        finally:
            stage.close()
            for suffix in ("", "-wal", "-shm"):
                try: Path(str(stage_path)+suffix).unlink()
                except FileNotFoundError: pass

    def authorized_incremental_sync(self, sender_bundle: dict[str, Any], manifest: dict[str, Any], local_chunks: dict[str, Any], fetched_chunks: dict[str, Any], envelopes: list[dict[str, Any]], subsystem: str, evidence_class: str, valid_at: str, known_at: str) -> dict[str, Any]:
        auth=self.verify_authorized_merkle_root_at(envelopes,manifest,subsystem,evidence_class,valid_at,known_at)
        if not auth.get("authorized"): raise ValueError("authorization_failed:"+",".join(auth.get("errors",[])))
        receipt=self.incremental_sync_causal_evidence(sender_bundle,manifest,local_chunks,fetched_chunks)
        core={k:v for k,v in receipt.items() if k != "receipt_digest"}
        core["authorization_decision_digest"]=auth["authorization_decision_digest"]
        core["authorization_policy_id"]=auth["policy_id"]
        core["authorized_signers"]=auth["valid_signers"]
        return {**core,"receipt_digest":sha256_bytes(stable_json(core).encode())}

    def incremental_sync_causal_evidence(self, sender_bundle: dict[str, Any], manifest: dict[str, Any], local_chunks: dict[str, Any], fetched_chunks: dict[str, Any]) -> dict[str, Any]:
        """Verify each available/fetched object against the Merkle root, then import only after full closure is proven."""
        if manifest.get("format") != "janus-merkle-evidence-manifest-v1": raise ValueError("unsupported merkle manifest")
        combined=dict(local_chunks); combined.update(fetched_chunks)
        required=set(manifest.get("leaves",[]))
        if set(combined) != required: raise ValueError("incomplete_or_extra_evidence_set")
        for h,chunk in combined.items():
            actual=sha256_bytes(stable_json(chunk.get("payload")).encode())
            if chunk.get("sha256") != h or actual != h: raise ValueError(f"chunk_hash_mismatch:{h}")
            if not self.verify_merkle_inclusion(h,manifest.get("proofs",{}).get(h,[]),manifest.get("root_digest","")):
                raise ValueError(f"invalid_merkle_inclusion:{h}")
        assembled={"format":sender_bundle["format"],"change_id":sender_bundle["change_id"],"certificate":sender_bundle["certificate"],"manifest":sender_bundle["manifest"],"chunks":combined}
        imported=self.import_causal_evidence_bundle(assembled)
        if not imported.get("valid"): raise ValueError("assembled_bundle_verification_failed")
        reproduced=self.generalized_truth_delta(sender_bundle["change_id"])["certificate"]["digest"]
        if reproduced != sender_bundle["certificate"]["digest"]: raise ValueError("certificate_reproduction_failed")
        receipt_core={"format":"janus-sync-receipt-v1","change_id":sender_bundle["change_id"],"merkle_root":manifest["root_digest"],"certificate_digest":reproduced,"fetched_chunk_count":len(fetched_chunks),"verified":True}
        return {**receipt_core,"receipt_digest":sha256_bytes(stable_json(receipt_core).encode())}

    def verify_causal_evidence_bundle(self, bundle: dict[str, Any]) -> dict[str, Any]:
        if bundle.get("format") != "janus-causal-evidence-bundle-v1": return {"valid":False,"errors":["unsupported_format"]}
        errors=[]; chunks=bundle.get("chunks",{})
        for key,c in chunks.items():
            actual=sha256_bytes(stable_json(c.get("payload")).encode())
            if key != c.get("sha256") or key != actual: errors.append(f"chunk_hash_mismatch:{key}")
        hashes=sorted(chunks)
        if hashes != bundle.get("manifest",{}).get("chunk_hashes",[]): errors.append("manifest_chunk_set_mismatch")
        root=sha256_bytes(stable_json(hashes).encode())
        if root != bundle.get("manifest",{}).get("root_digest"): errors.append("root_digest_mismatch")
        return {"valid":not errors,"errors":errors,"root_digest":root}

    def import_causal_evidence_bundle(self, bundle: dict[str, Any]) -> dict[str, Any]:
        verification=self.verify_causal_evidence_bundle(bundle)
        if not verification["valid"]: return verification
        payloads=[c["payload"] for c in bundle["chunks"].values()]
        # Deterministic dependency-safe import order.
        for o in sorted((x for x in payloads if x["kind"]=="component"), key=lambda x:x["name"]): self.add_component(o["name"],o.get("authority",""),json.loads(o.get("metadata_json") or "{}"))
        for o in sorted((x for x in payloads if x["kind"]=="dependency"), key=lambda x:(x["src"],x["dst"],x["kind"])): self.add_dependency(o["src"],o["dst"],o["kind"])
        for o in sorted((x for x in payloads if x["kind"]=="fact"), key=lambda x:(x["valid_from"],x["known_at"],x["fact_id"])):
            self.add_fact({"subject":o["subject"],"predicate":o["predicate"],"value":json.loads(o["value_json"]),"valid_from":o["valid_from"],"valid_to":o.get("valid_to"),"known_at":o["known_at"],"source":o["source"],"source_hash":o.get("source_hash"),"authority":o.get("authority"),"confidence":o.get("confidence"),"supersedes":o.get("supersedes")})
        for o in sorted((x for x in payloads if x["kind"]=="authority_precedence"), key=lambda x:(x["subject_prefix"],x["predicate"],x["authority"])): self.set_authority_precedence(o["subject_prefix"],o["predicate"],o["authority"],o["rank"])
        for o in sorted((x for x in payloads if x["kind"]=="evidence_precedence"), key=lambda x:x["confidence"]): self.set_evidence_precedence(o["confidence"],o["rank"])
        for o in sorted((x for x in payloads if x["kind"]=="proof_bundle"), key=lambda x:x["change_id"]): self.add_proof_bundle(o["bundle"])
        for o in sorted((x for x in payloads if x["kind"]=="proof_lifecycle_event"), key=lambda x:(x["known_at"],x["event_id"])): self.record_proof_lifecycle_event(o["change_id"],o["status"],o["known_at"],o["actor"],o.get("reason", ""),o.get("superseded_by"))
        for o in sorted((x for x in payloads if x["kind"]=="normalization_decision"), key=lambda x:(x["known_at"],x["decision_id"])):
            rec=self.record_normalization_decision(json.loads(o["proposal_json"]),o["decision"],o["decided_by"],json.loads(o["proof_refs_json"]),o["known_at"])
            if o.get("revoked_at"): self.revoke_normalization_decision(rec["decision_id"],o.get("revoked_by") or "unknown",o.get("revocation_reason") or "",o["revoked_at"])
        verification["imported_chunks"]=len(payloads); return verification

    def _historical_archive_payload(self) -> dict[str, Any]:
        return {
            "format":"janus-historical-archive-v1",
            "components":[dict(r) for r in self.conn.execute("SELECT * FROM components ORDER BY name")],
            "dependencies":[dict(r) for r in self.conn.execute("SELECT * FROM dependencies ORDER BY src,dst,kind")],
            "facts":[dict(r) for r in self.conn.execute("SELECT fact_id,subject,predicate,value_json,valid_from,valid_to,known_at,source,authority,confidence,supersedes FROM facts ORDER BY subject,predicate,valid_from,known_at,fact_id")],
            "authority_precedence":[dict(r) for r in self.conn.execute("SELECT * FROM authority_precedence ORDER BY subject_prefix,predicate,authority")],
            "evidence_precedence":[dict(r) for r in self.conn.execute("SELECT * FROM evidence_precedence ORDER BY confidence")],
            "proof_bundles":[dict(r) for r in self.conn.execute("SELECT change_id,bundle_json,bundle_hash,status FROM proof_bundles ORDER BY change_id")],
            "proof_lifecycle_events":[dict(r) for r in self.conn.execute("SELECT event_id,change_id,status,known_at,actor,reason,superseded_by FROM proof_lifecycle_events ORDER BY known_at,event_id")],
            "normalization_decisions":[dict(r) for r in self.conn.execute("SELECT * FROM normalization_decisions ORDER BY known_at,decision_id")],
        }

    def historical_archive_digest(self) -> str:
        return sha256_bytes(stable_json(self._historical_archive_payload()).encode())

    def export_historical_archive(self, out_dir: str | os.PathLike[str]) -> dict[str, Any]:
        out=Path(out_dir); out.mkdir(parents=True,exist_ok=True)
        payload=self._historical_archive_payload(); payload["archive_digest"]=self.historical_archive_digest()
        path=out/"historical_archive.json"; path.write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8")
        return {"archive_json":str(path),"archive_digest":payload["archive_digest"]}

    def import_historical_archive(self, archive_json: str | os.PathLike[str]) -> dict[str, Any]:
        data=json.loads(Path(archive_json).read_text(encoding="utf-8"))
        if data.get("format") != "janus-historical-archive-v1": raise ValueError("unsupported historical archive format")
        for c in data.get("components",[]): self.add_component(c["name"],c.get("authority",""),c.get("description",""))
        for d in data.get("dependencies",[]): self.add_dependency(d["src"],d["dst"],d.get("kind","depends_on"))
        for f in data.get("facts",[]):
            item={k:f[k] for k in ("subject","predicate","valid_from","known_at","source") if k in f}
            item["value"]=json.loads(f["value_json"]); item["valid_to"]=f.get("valid_to"); item["authority"]=f.get("authority"); item["confidence"]=f.get("confidence"); item["supersedes"]=f.get("supersedes")
            self.add_fact(item)
        for a in data.get("authority_precedence",[]): self.set_authority_precedence(a["subject_prefix"],a["predicate"],a["authority"],a["rank"])
        for e in data.get("evidence_precedence",[]): self.set_evidence_precedence(e["confidence"],e["rank"])
        for p in data.get("proof_bundles",[]): self.add_proof_bundle(json.loads(p["bundle_json"]))
        for e in data.get("proof_lifecycle_events",[]): self.record_proof_lifecycle_event(e["change_id"],e["status"],e["known_at"],e["actor"],e.get("reason", ""),e.get("superseded_by"))
        for n in data.get("normalization_decisions",[]):
            proposal=json.loads(n["proposal_json"]); refs=json.loads(n["proof_refs_json"]); rec=self.record_normalization_decision(proposal,n["decision"],n["decided_by"],refs,n["known_at"])
            if n.get("revoked_at"): self.revoke_normalization_decision(rec["decision_id"],n.get("revoked_by") or "unknown",n.get("revocation_reason") or "",n["revoked_at"])
        actual=self.historical_archive_digest(); expected=data.get("archive_digest")
        return {"expected_archive_digest":expected,"actual_archive_digest":actual,"archive_digest_match":actual==expected}

    def state_digest(self) -> str:
        payload = {
            "components": [dict(r) for r in self.conn.execute("SELECT * FROM components ORDER BY name")],
            "dependencies": [dict(r) for r in self.conn.execute("SELECT * FROM dependencies ORDER BY src,dst,kind")],
            "facts": self.current_facts(),
            "invariants": [dict(r) for r in self.conn.execute("SELECT invariant_hash,text,source FROM invariants ORDER BY invariant_hash")],
            "candidates": self.prioritized_candidates(),
            "authority_precedence": [dict(r) for r in self.conn.execute("SELECT * FROM authority_precedence ORDER BY subject_prefix,predicate,authority")],
            "evidence_precedence": [dict(r) for r in self.conn.execute("SELECT * FROM evidence_precedence ORDER BY confidence")],
            "proof_bundles": [dict(r) for r in self.conn.execute("SELECT change_id,bundle_hash,status FROM proof_bundles ORDER BY change_id")],
            "proof_lifecycle_events": [dict(r) for r in self.conn.execute("SELECT event_id,change_id,status,known_at,actor,reason,superseded_by FROM proof_lifecycle_events ORDER BY known_at,event_id")],
            "normalization_decisions": [dict(r) for r in self.conn.execute("SELECT * FROM normalization_decisions ORDER BY known_at,decision_id")],
        }
        return sha256_bytes(stable_json(payload).encode())

    def status(self) -> dict[str, Any]:
        return {
            "state_digest": self.state_digest(),
            "components": self.conn.execute("SELECT COUNT(*) FROM components").fetchone()[0],
            "facts": self.conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0],
            "current_facts": len(self.current_facts()),
            "contradictions": len(self.contradictions()),
            "temporal_conflicts": len(self.temporal_conflicts()),
            "quarantined_temporal_conflicts": sum(1 for c in self.temporal_conflicts() if c["resolution"]["status"] == "quarantined"),
            "temporal_normalization_proposals": len(self.temporal_normalization_proposals()),
            "candidates": self.conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0],
            "snapshots": self.conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0],
            "proof_bundles": self.conn.execute("SELECT COUNT(*) FROM proof_bundles").fetchone()[0],
            "proof_lifecycle_events": self.conn.execute("SELECT COUNT(*) FROM proof_lifecycle_events").fetchone()[0],
            "normalization_decisions": self.conn.execute("SELECT COUNT(*) FROM normalization_decisions").fetchone()[0],
            "active_normalization_overlays": len(self.normalization_overlays()),
            "verified_normalization_overlays": len(self.verified_normalization_overlays()),
        }

    def import_handoff(self, handoff_json: str | os.PathLike[str]) -> dict[str, Any]:
        """Import an exported authoritative-current-state handoff into a fresh twin.

        Historical facts intentionally are not reconstructed from the compact handoff;
        the purpose of this path is deterministic current-state transfer. Full archival
        history should travel as a separate evidence archive when required.
        """
        data = json.loads(Path(handoff_json).read_text(encoding="utf-8"))
        if data.get("format") != "janus-handoff-v1":
            raise ValueError("unsupported handoff format")

        for c in data.get("components", []):
            metadata = c.get("metadata_json", {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    metadata = {"raw_metadata": metadata}
            self.add_component(c["name"], c["authority"], metadata)

        for d in data.get("dependencies", []):
            self.add_dependency(d["src"], d["dst"], d.get("kind", "depends_on"))

        for p in data.get("authority_precedence", []):
            self.set_authority_precedence(p["subject_prefix"], p["predicate"], p["authority"], p["rank"])

        for p in data.get("evidence_precedence", []):
            self.set_evidence_precedence(p["confidence"], p["rank"])

        for f in data.get("current_facts", []):
            self.add_fact({
                "subject": f["subject"],
                "predicate": f["predicate"],
                "value": f.get("value"),
                "valid_from": f["valid_from"],
                "valid_to": f.get("valid_to"),
                "known_at": f["known_at"],
                "source": f["source"],
                "source_hash": f.get("source_hash"),
                "confidence": f.get("confidence", "reported"),
                "authority": f.get("authority"),
                "supersedes": f.get("supersedes"),
            })

        for inv in data.get("invariants", []):
            self.add_invariant(inv["text"], inv.get("source"))

        for c in data.get("prioritized_candidates", []):
            candidate = {"id": c["id"], "title": c["title"], **c.get("metrics", {})}
            candidate["status"] = c.get("status", "proposed")
            self.add_candidate(candidate)

        for n in data.get("normalization_decisions", []):
            proposal = json.loads(n["proposal_json"]) if isinstance(n.get("proposal_json"), str) else n["proposal_json"]
            proof_refs = json.loads(n["proof_refs_json"]) if isinstance(n.get("proof_refs_json"), str) else n["proof_refs_json"]
            rec = self.record_normalization_decision(proposal, n["decision"], n["decided_by"], proof_refs, n["known_at"])
            if n.get("revoked_at"):
                self.revoke_normalization_decision(rec["decision_id"], n.get("revoked_by") or "unknown", n.get("revocation_reason") or "", n["revoked_at"])

        for p in data.get("proof_bundles", []):
            raw = p.get("bundle_json")
            bundle = json.loads(raw) if isinstance(raw, str) else raw
            if bundle:
                self.add_proof_bundle(bundle)

        for e in data.get("proof_lifecycle_events", []):
            self.record_proof_lifecycle_event(
                e["change_id"], e["status"], e["known_at"], e["actor"],
                e.get("reason", ""), e.get("superseded_by"),
            )

        actual = self.state_digest()
        expected = data.get("state_digest")
        return {
            "expected_state_digest": expected,
            "actual_state_digest": actual,
            "digest_match": actual == expected,
        }

    @staticmethod
    def _storage_certificate_core(certificate: dict[str, Any]) -> dict[str, Any]:
        return {k:certificate.get(k) for k in (
            "format","session_id","project_state_digest","storage_state","storage_state_digest","fence_epoch",
            "receipt_head_digest","recovery_certificate_digest","forensic_root_link_digest","forensic_dag_digest",
            "quarantine_evidence_digests","signer_authority","created_at"
        )}

    @staticmethod
    def _verify_storage_certificate_signature_only(certificate: dict[str, Any], trust_store: dict[str,str]) -> bool:
        if certificate.get("format")!="janus-storage-state-certificate-v1": return False
        core=JanusTwin._storage_certificate_core(certificate)
        digest=sha256_bytes(stable_json(core).encode())
        if digest!=certificate.get("certificate_digest"): return False
        authority=certificate.get("signer_authority"); sig=certificate.get("signature") or {}
        expected={
            "domain":"JANUS_STORAGE_STATE_CERTIFICATE_V1","certificate_digest":digest,"session_id":certificate.get("session_id"),
            "project_state_digest":certificate.get("project_state_digest"),"storage_state_digest":certificate.get("storage_state_digest"),
            "receipt_head_digest":certificate.get("receipt_head_digest"),"recovery_certificate_digest":certificate.get("recovery_certificate_digest"),
            "forensic_root_link_digest":certificate.get("forensic_root_link_digest"),"forensic_dag_digest":certificate.get("forensic_dag_digest"),
            "authority":authority,
        }
        if authority not in trust_store or sig.get("algorithm")!="Ed25519" or sig.get("statement")!=expected: return False
        try:
            Ed25519PublicKey.from_public_bytes(base64.b64decode(trust_store[authority])).verify(
                base64.b64decode(sig.get("signature_b64","")),stable_json(expected).encode()
            )
            return True
        except (ValueError,InvalidSignature,TypeError):
            return False

    def _replay_tables_snapshot(self) -> dict[str, Any]:
        tables={}
        # Receiver-local truth-revalidation chain is control evidence, not project truth, and must never be imported from a sender.
        names=[r[0] for r in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name!='truth_revalidation_receipt_chain' ORDER BY name")]
        for name in names:
            cols=[r[1] for r in self.conn.execute(f'PRAGMA table_info("{name}")')]
            order_clause=",".join(f'"{c}"' for c in cols) if cols else "rowid"
            rows=[list(r) for r in self.conn.execute(f'SELECT * FROM "{name}" ORDER BY {order_clause}')]
            tables[name]={"columns":cols,"rows":rows}
        return tables

    @staticmethod
    def _receiver_replay_bundle_core(bundle: dict[str, Any]) -> dict[str, Any]:
        return {k:bundle.get(k) for k in ("format","certificate","forensic_dag","tables","storage_artifacts")}

    def build_receiver_replay_bundle(self, certificate: dict[str, Any], forensic_dag: dict[str, Any] | None = None) -> dict[str, Any]:
        """Export a portable, content-addressed replay package for a fresh receiver."""
        if certificate.get("format")!="janus-storage-state-certificate-v1": raise ValueError("unsupported_storage_certificate")
        observed=self._portable_storage_summary(self.classify_storage_artifacts_non_mutating(self.db_path))
        if observed!=certificate.get("storage_state"): raise ValueError("sender_storage_state_changed")
        if certificate.get("forensic_dag_digest"):
            if forensic_dag is None or forensic_dag.get("dag_digest")!=certificate.get("forensic_dag_digest"):
                raise ValueError("forensic_dag_required")
        artifacts={}
        for key,path in (("main_db",self.db_path),("wal",Path(str(self.db_path)+"-wal")),("shm",Path(str(self.db_path)+"-shm"))):
            if path.exists():
                data=path.read_bytes(); artifacts[key]={"exists":True,"sha256":sha256_bytes(data),"bytes_b64":base64.b64encode(data).decode()}
            else:
                artifacts[key]={"exists":False,"sha256":None,"bytes_b64":None}
        core={
            "format":"janus-receiver-replay-bundle-v1",
            "certificate":certificate,
            "forensic_dag":forensic_dag,
            "tables":self._replay_tables_snapshot(),
            "storage_artifacts":artifacts,
        }
        return {**core,"bundle_digest":sha256_bytes(stable_json(core).encode())}

    @staticmethod
    def _write_replay_storage_snapshot(bundle: dict[str, Any], snapshot_db: Path) -> None:
        snapshot_db.parent.mkdir(parents=True,exist_ok=True)
        for key,suffix in (("main_db",""),("wal","-wal"),("shm","-shm")):
            item=(bundle.get("storage_artifacts") or {}).get(key) or {}
            target=Path(str(snapshot_db)+suffix)
            if target.exists(): target.unlink()
            if item.get("exists"):
                try: data=base64.b64decode(item.get("bytes_b64") or "",validate=True)
                except Exception as exc: raise ValueError("replay_storage_artifact_invalid") from exc
                if sha256_bytes(data)!=item.get("sha256"): raise ValueError("replay_storage_artifact_hash_mismatch")
                target.write_bytes(data)

    @staticmethod
    def _import_replay_tables(target: "JanusTwin", tables: dict[str, Any]) -> None:
        expected=[r[0] for r in target.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name!='truth_revalidation_receipt_chain' ORDER BY name")]
        if sorted(tables)!=sorted(expected): raise ValueError("replay_table_set_mismatch")
        target.conn.execute("PRAGMA foreign_keys=OFF")
        try:
            target.conn.execute("BEGIN")
            for name in expected:
                spec=tables.get(name) or {}; cols=spec.get("columns") or []
                actual=[r[1] for r in target.conn.execute(f'PRAGMA table_info("{name}")')]
                if cols!=actual: raise ValueError("replay_table_schema_mismatch")
                target.conn.execute(f'DELETE FROM "{name}"')
                if spec.get("rows"):
                    quoted=",".join(f'"{c}"' for c in cols); marks=",".join("?" for _ in cols)
                    target.conn.executemany(f'INSERT INTO "{name}" ({quoted}) VALUES ({marks})',spec["rows"])
            target.conn.commit()
        except Exception:
            target.conn.rollback(); raise
        finally:
            target.conn.execute("PRAGMA foreign_keys=ON")

    def import_and_verify_receiver_replay_bundle(self, bundle: dict[str, Any], trust_store: dict[str,str]) -> dict[str, Any]:
        """Stage, verify, then promote a portable replay bundle into this receiver."""
        if bundle.get("format")!="janus-receiver-replay-bundle-v1": raise ValueError("unsupported_replay_bundle")
        core=self._receiver_replay_bundle_core(bundle); computed=sha256_bytes(stable_json(core).encode())
        if computed!=bundle.get("bundle_digest"): raise ValueError("replay_bundle_digest_mismatch")
        cert=bundle.get("certificate") or {}; dag=bundle.get("forensic_dag")
        if not self._verify_storage_certificate_signature_only(cert,trust_store): raise ValueError("replay_certificate_signature_invalid")
        token=str(bundle["bundle_digest"])[:16]
        stage_path=self.db_path.with_name(self.db_path.name+f".replay-stage-{token}")
        snapshot_dir=self.db_path.parent/(self.db_path.name+f".replay-evidence-{token}")
        snapshot_db=snapshot_dir/'certified.db'
        for path in (stage_path,Path(str(stage_path)+"-wal"),Path(str(stage_path)+"-shm")):
            if path.exists(): path.unlink()
        self._write_replay_storage_snapshot(bundle,snapshot_db)
        stage=JanusTwin(stage_path)
        try:
            self._import_replay_tables(stage,bundle.get("tables") or {})
            verified=stage.verify_storage_state_certificate(cert,trust_store,forensic_dag=dag,db_path=snapshot_db)
            if not verified.get("valid"):
                raise ValueError("replay_reconstruction_failed:"+",".join(verified.get("errors") or []))
            stage.conn.backup(self.conn); self.conn.commit()
            if self.state_digest()!=cert.get("project_state_digest"): raise ValueError("replay_promotion_state_mismatch")
            return {
                "valid":True,"format":"janus-receiver-replay-result-v1","bundle_digest":computed,
                "certificate_digest":cert.get("certificate_digest"),"project_state_digest":self.state_digest(),
                "storage_snapshot_verified":True,"storage_snapshot_db_path":str(snapshot_db),
                "certificate_verification":verified,
            }
        finally:
            stage.close()
            for path in (stage_path,Path(str(stage_path)+"-wal"),Path(str(stage_path)+"-shm")):
                if path.exists(): path.unlink()

    @staticmethod
    def _storage_certificate_delta(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
        prev_q=set(previous.get("quarantine_evidence_digests") or []); cur_q=set(current.get("quarantine_evidence_digests") or [])
        def scalar(field: str) -> dict[str, Any]:
            a=previous.get(field); b=current.get(field); return {"from":a,"to":b,"changed":a!=b}
        return {
            "project_state":scalar("project_state_digest"),
            "storage_state":scalar("storage_state_digest"),
            "receipt_head":scalar("receipt_head_digest"),
            "recovery":scalar("recovery_certificate_digest"),
            "forensic_dag":scalar("forensic_dag_digest"),
            "fence_epoch":scalar("fence_epoch"),
            "quarantine":{"added":sorted(cur_q-prev_q),"removed":sorted(prev_q-cur_q),"changed":prev_q!=cur_q},
        }

    def build_storage_certificate_chain_entry(self, previous_certificate: dict[str, Any], current_certificate: dict[str, Any], authority: str, private_key_b64: str, previous_chain_digest: str | None = None) -> dict[str, Any]:
        if previous_certificate.get("format")!="janus-storage-state-certificate-v1" or current_certificate.get("format")!="janus-storage-state-certificate-v1":
            raise ValueError("unsupported_storage_certificate")
        core={
            "format":"janus-storage-certificate-chain-entry-v1",
            "previous_chain_digest":previous_chain_digest,
            "previous_certificate_digest":previous_certificate.get("certificate_digest"),
            "current_certificate_digest":current_certificate.get("certificate_digest"),
            "delta":self._storage_certificate_delta(previous_certificate,current_certificate),
            "signer_authority":authority,
            "created_at":utcnow(),
        }
        digest=sha256_bytes(stable_json(core).encode())
        statement={"domain":"JANUS_STORAGE_CERTIFICATE_CHAIN_V1","chain_digest":digest,"previous_chain_digest":previous_chain_digest,"previous_certificate_digest":core["previous_certificate_digest"],"current_certificate_digest":core["current_certificate_digest"],"delta_digest":sha256_bytes(stable_json(core["delta"]).encode()),"authority":authority}
        sig=base64.b64encode(Ed25519PrivateKey.from_private_bytes(base64.b64decode(private_key_b64)).sign(stable_json(statement).encode())).decode()
        return {**core,"chain_digest":digest,"signature":{"algorithm":"Ed25519","statement":statement,"signature_b64":sig}}

    def verify_storage_certificate_chain_entry(self, entry: dict[str, Any], previous_certificate: dict[str, Any], current_certificate: dict[str, Any], trust_store: dict[str,str], expected_previous_chain_digest: str | None = None) -> dict[str, Any]:
        errors=[]
        if entry.get("format")!="janus-storage-certificate-chain-entry-v1": errors.append("unsupported_format")
        core={k:entry.get(k) for k in ("format","previous_chain_digest","previous_certificate_digest","current_certificate_digest","delta","signer_authority","created_at")}
        digest=sha256_bytes(stable_json(core).encode())
        if digest!=entry.get("chain_digest"): errors.append("chain_digest_mismatch")
        if entry.get("previous_chain_digest")!=expected_previous_chain_digest: errors.append("previous_chain_digest_mismatch")
        if entry.get("previous_certificate_digest")!=previous_certificate.get("certificate_digest"): errors.append("previous_certificate_digest_mismatch")
        if entry.get("current_certificate_digest")!=current_certificate.get("certificate_digest"): errors.append("current_certificate_digest_mismatch")
        if entry.get("delta")!=self._storage_certificate_delta(previous_certificate,current_certificate): errors.append("certificate_delta_mismatch")
        if not self._verify_storage_certificate_signature_only(previous_certificate,trust_store): errors.append("previous_certificate_signature_invalid")
        if not self._verify_storage_certificate_signature_only(current_certificate,trust_store): errors.append("current_certificate_signature_invalid")
        authority=entry.get("signer_authority"); sig=entry.get("signature") or {}
        statement={"domain":"JANUS_STORAGE_CERTIFICATE_CHAIN_V1","chain_digest":digest,"previous_chain_digest":entry.get("previous_chain_digest"),"previous_certificate_digest":entry.get("previous_certificate_digest"),"current_certificate_digest":entry.get("current_certificate_digest"),"delta_digest":sha256_bytes(stable_json(entry.get("delta") or {}).encode()),"authority":authority}
        if authority not in trust_store or sig.get("algorithm")!="Ed25519" or sig.get("statement")!=statement:
            errors.append("chain_signature_invalid")
        else:
            try:
                Ed25519PublicKey.from_public_bytes(base64.b64decode(trust_store[authority])).verify(base64.b64decode(sig.get("signature_b64","")),stable_json(statement).encode())
            except (ValueError,InvalidSignature,TypeError): errors.append("chain_signature_invalid")
        return {"valid":not errors,"errors":sorted(set(errors)),"chain_digest":digest}

    def verify_storage_certificate_chain(self, entries: list[dict[str, Any]], certificates: dict[str,dict[str,Any]], trust_store: dict[str,str]) -> dict[str, Any]:
        errors=[]; expected_previous_chain=None; expected_previous_certificate=None; seen=set()
        for entry in entries:
            digest=entry.get("chain_digest")
            if digest in seen: errors.append("chain_cycle_detected")
            seen.add(digest)
            prev_digest=entry.get("previous_certificate_digest"); cur_digest=entry.get("current_certificate_digest")
            previous=certificates.get(prev_digest); current=certificates.get(cur_digest)
            if previous is None or current is None:
                errors.append("certificate_missing"); continue
            if expected_previous_certificate is not None and prev_digest!=expected_previous_certificate: errors.append("certificate_chain_discontinuity")
            checked=self.verify_storage_certificate_chain_entry(entry,previous,current,trust_store,expected_previous_chain)
            errors.extend(checked.get("errors") or [])
            expected_previous_chain=digest; expected_previous_certificate=cur_digest
        return {"valid":not errors,"errors":sorted(set(errors)),"entry_count":len(entries),"head_chain_digest":expected_previous_chain}

    @staticmethod
    def run_host_fd_exhaustion_probe(root: str | Path, max_open_files: int = 32) -> dict[str, Any]:
        root=Path(root); root.mkdir(parents=True,exist_ok=True)
        script="""import errno,json,os,resource,sys\nlimit=int(sys.argv[1])\nresource.setrlimit(resource.RLIMIT_NOFILE,(limit,limit))\nfds=[]; err=None\ntry:\n    while True:\n        fds.append(os.open('/dev/null',os.O_RDONLY))\nexcept OSError as exc:\n    err=exc\nresult={'opened_fds':len(fds),'errno':getattr(err,'errno',None),'errno_name':errno.errorcode.get(getattr(err,'errno',None),None),'write_succeeded':False}\nprint(json.dumps(result,sort_keys=True))\n"""
        proc=subprocess.run([sys.executable,"-c",script,str(int(max_open_files))],cwd=root,text=True,capture_output=True,check=False)
        try: child=json.loads((proc.stdout or "").strip().splitlines()[-1])
        except Exception: child={"opened_fds":0,"errno":None,"errno_name":None}
        core={
            "format":"janus-host-fd-fault-probe-v1","classification":"kernel_fd_limit" if child.get("errno")==24 else "unexpected",
            "max_open_files":int(max_open_files),"opened_fds":int(child.get("opened_fds") or 0),"errno":child.get("errno"),"errno_name":child.get("errno_name"),
            "returncode":proc.returncode,"authoritative_path_touched":False,
        }
        return {**core,"probe_digest":sha256_bytes(stable_json(core).encode())}


    @staticmethod
    def _object_replay_graph_core(graph: dict[str, Any]) -> dict[str, Any]:
        objects=graph.get("objects") or {}
        return {
            "format":graph.get("format"),
            "root_object":graph.get("root_object"),
            "object_count":graph.get("object_count"),
            "included_tables":graph.get("included_tables"),
            "object_hashes":sorted(objects),
        }

    @staticmethod
    def _content_object(kind: str, payload: dict[str, Any], refs: Iterable[str] = ()) -> tuple[str, dict[str, Any]]:
        obj={"kind":kind,"payload":payload,"refs":sorted(set(refs))}
        return sha256_bytes(stable_json(obj).encode()),obj

    def _minimal_replay_tables_snapshot(self, certificate: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Return only rows required to reproduce certified JANUS project/proof state.

        This deliberately excludes unrelated control-plane and runtime tables. The receiver
        still starts from the canonical schema, but only the content reachable from the
        certificate is transferred.
        """
        sid=certificate.get("session_id")
        project_tables=(
            "components","dependencies","facts","invariants","candidates",
            "authority_precedence","evidence_precedence","proof_bundles",
            "proof_lifecycle_events","normalization_decisions",
        )
        out: dict[str,dict[str,Any]]={}

        def snapshot(name: str, where: str | None = None, params: tuple[Any,...] = ()) -> None:
            cols=[r[1] for r in self.conn.execute(f'PRAGMA table_info("{name}")')]
            order_clause=",".join(f'"{c}"' for c in cols) if cols else "rowid"
            sql=f'SELECT * FROM "{name}"'
            if where: sql+=" WHERE "+where
            sql+=f" ORDER BY {order_clause}"
            rows=[list(r) for r in self.conn.execute(sql,params)]
            out[name]={"columns":cols,"rows":rows}

        for name in project_tables: snapshot(name)
        snapshot("promotion_journal","session_id=?",(sid,))
        snapshot("recovery_certificates","session_id=? AND certificate_digest=?",(sid,certificate.get("recovery_certificate_digest")))
        quarantine=tuple(certificate.get("quarantine_evidence_digests") or [])
        if quarantine:
            marks=",".join("?" for _ in quarantine)
            snapshot("storage_quarantine",f"session_id=? AND evidence_digest IN ({marks})",(sid,*quarantine))
        else:
            snapshot("storage_quarantine","1=0")
        head=certificate.get("receipt_head_digest")
        if head: snapshot("joint_receipts","receipt_digest=?",(head,))
        else: snapshot("joint_receipts","1=0")
        return out

    def build_object_replay_graph(self, certificate: dict[str, Any], forensic_dag: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build an exact, content-addressed transitive replay closure for a fresh receiver."""
        if certificate.get("format")!="janus-storage-state-certificate-v1": raise ValueError("unsupported_storage_certificate")
        observed=self._portable_storage_summary(self.classify_storage_artifacts_non_mutating(self.db_path))
        if observed!=certificate.get("storage_state"): raise ValueError("sender_storage_state_changed")
        if certificate.get("forensic_dag_digest"):
            if forensic_dag is None or forensic_dag.get("dag_digest")!=certificate.get("forensic_dag_digest"):
                raise ValueError("forensic_dag_required")

        objects: dict[str,dict[str,Any]]={}
        def put(kind: str, payload: dict[str, Any], refs: Iterable[str] = ()) -> str:
            digest,obj=self._content_object(kind,payload,refs)
            existing=objects.get(digest)
            if existing is not None and existing!=obj: raise ValueError("content_object_hash_collision")
            objects[digest]=obj; return digest

        cert_ref=put("storage_certificate",certificate)
        dag_ref=put("forensic_dag",forensic_dag) if forensic_dag is not None else None

        table_refs: dict[str,str]={}
        tables=self._minimal_replay_tables_snapshot(certificate)
        for name in sorted(tables):
            spec=tables[name]; row_refs=[]
            for row in spec["rows"]:
                row_refs.append(put("table_row",{"table":name,"row":row}))
            table_refs[name]=put("table_manifest",{"table":name,"columns":spec["columns"],"row_refs":sorted(row_refs)},row_refs)

        artifact_refs: dict[str,str]={}
        for key,path in (("main_db",self.db_path),("wal",Path(str(self.db_path)+"-wal")),("shm",Path(str(self.db_path)+"-shm"))):
            if path.exists():
                data=path.read_bytes(); payload={"name":key,"exists":True,"sha256":sha256_bytes(data),"bytes_b64":base64.b64encode(data).decode()}
            else:
                payload={"name":key,"exists":False,"sha256":None,"bytes_b64":None}
            artifact_refs[key]=put("storage_artifact",payload)

        root_payload={
            "format":"janus-object-replay-root-v1",
            "certificate_ref":cert_ref,"forensic_dag_ref":dag_ref,
            "table_refs":table_refs,"storage_artifact_refs":artifact_refs,
        }
        root_refs=[cert_ref,*table_refs.values(),*artifact_refs.values()]
        if dag_ref: root_refs.append(dag_ref)
        root_ref=put("replay_root",root_payload,root_refs)
        graph={
            "format":"janus-object-replay-graph-v1","root_object":root_ref,
            "object_count":len(objects),"included_tables":sorted(table_refs),"objects":objects,
        }
        return {**graph,"graph_digest":sha256_bytes(stable_json(self._object_replay_graph_core(graph)).encode())}

    @staticmethod
    def _verify_object_replay_closure(graph: dict[str, Any]) -> dict[str, Any]:
        if graph.get("format")!="janus-object-replay-graph-v1": raise ValueError("unsupported_object_replay_graph")
        objects=graph.get("objects") or {}
        if int(graph.get("object_count",-1))!=len(objects): raise ValueError("object_graph_count_mismatch")
        expected=sha256_bytes(stable_json(JanusTwin._object_replay_graph_core(graph)).encode())
        if expected!=graph.get("graph_digest"): raise ValueError("object_graph_digest_mismatch")
        root=graph.get("root_object")
        if root not in objects: raise ValueError("object_graph_missing_object:"+str(root))
        reachable=set(); stack=[root]
        while stack:
            digest=stack.pop()
            if digest in reachable: continue
            obj=objects.get(digest)
            if obj is None: raise ValueError("object_graph_missing_object:"+str(digest))
            if sha256_bytes(stable_json(obj).encode())!=digest: raise ValueError("object_graph_hash_mismatch:"+str(digest))
            reachable.add(digest)
            refs=obj.get("refs") or []
            if refs!=sorted(set(refs)): raise ValueError("object_graph_nondeterministic_refs:"+str(digest))
            for ref in refs:
                if ref not in objects: raise ValueError("object_graph_missing_object:"+str(ref))
                stack.append(ref)
        extras=sorted(set(objects)-reachable)
        if extras: raise ValueError("object_graph_extra_object:"+extras[0])
        return {"valid":True,"root_object":root,"reachable":reachable,"graph_digest":expected}

    @staticmethod
    def _import_partial_replay_tables(target: "JanusTwin", tables: dict[str, Any]) -> None:
        target.conn.execute("PRAGMA foreign_keys=OFF")
        try:
            target.conn.execute("BEGIN")
            for name in sorted(tables):
                spec=tables[name]; cols=spec.get("columns") or []
                actual=[r[1] for r in target.conn.execute(f'PRAGMA table_info("{name}")')]
                if not actual: raise ValueError("object_graph_unknown_table:"+name)
                if cols!=actual: raise ValueError("object_graph_table_schema_mismatch:"+name)
                target.conn.execute(f'DELETE FROM "{name}"')
                rows=spec.get("rows") or []
                if rows:
                    quoted=",".join(f'"{c}"' for c in cols); marks=",".join("?" for _ in cols)
                    target.conn.executemany(f'INSERT INTO "{name}" ({quoted}) VALUES ({marks})',rows)
            target.conn.commit()
        except Exception:
            target.conn.rollback(); raise
        finally:
            target.conn.execute("PRAGMA foreign_keys=ON")

    def import_and_verify_object_replay_graph(self, graph: dict[str, Any], trust_store: dict[str,str]) -> dict[str, Any]:
        """Verify exact object closure before staging, reconstruct, verify certificate, then promote."""
        closure=self._verify_object_replay_closure(graph)
        objects=graph["objects"]; root_obj=objects[graph["root_object"]]
        if root_obj.get("kind")!="replay_root": raise ValueError("object_graph_root_kind_invalid")
        root=root_obj.get("payload") or {}
        if root.get("format")!="janus-object-replay-root-v1": raise ValueError("object_graph_root_format_invalid")
        expected_root_refs=sorted(set([
            root.get("certificate_ref"),*(root.get("table_refs") or {}).values(),*(root.get("storage_artifact_refs") or {}).values(),
            *([root.get("forensic_dag_ref")] if root.get("forensic_dag_ref") else []),
        ]))
        if expected_root_refs!=root_obj.get("refs"): raise ValueError("object_graph_root_refs_mismatch")

        cert_obj=objects.get(root.get("certificate_ref")) or {}
        if cert_obj.get("kind")!="storage_certificate": raise ValueError("object_graph_certificate_object_invalid")
        cert=cert_obj.get("payload") or {}
        if not self._verify_storage_certificate_signature_only(cert,trust_store): raise ValueError("object_graph_certificate_signature_invalid")
        dag=None
        if root.get("forensic_dag_ref"):
            dag_obj=objects.get(root["forensic_dag_ref"]) or {}
            if dag_obj.get("kind")!="forensic_dag": raise ValueError("object_graph_forensic_dag_object_invalid")
            dag=dag_obj.get("payload")

        tables={}
        for name,manifest_ref in sorted((root.get("table_refs") or {}).items()):
            manifest=objects.get(manifest_ref) or {}
            if manifest.get("kind")!="table_manifest": raise ValueError("object_graph_table_manifest_invalid:"+name)
            payload=manifest.get("payload") or {}
            if payload.get("table")!=name: raise ValueError("object_graph_table_manifest_name_mismatch:"+name)
            row_refs=payload.get("row_refs") or []
            if sorted(row_refs)!=row_refs or sorted(set(row_refs))!=row_refs: raise ValueError("object_graph_table_row_refs_invalid:"+name)
            if manifest.get("refs")!=row_refs: raise ValueError("object_graph_table_manifest_refs_mismatch:"+name)
            rows=[]
            for row_ref in row_refs:
                row_obj=objects.get(row_ref) or {}
                if row_obj.get("kind")!="table_row": raise ValueError("object_graph_table_row_invalid:"+name)
                row_payload=row_obj.get("payload") or {}
                if row_payload.get("table")!=name: raise ValueError("object_graph_table_row_name_mismatch:"+name)
                if row_obj.get("refs"): raise ValueError("object_graph_table_row_refs_forbidden:"+name)
                rows.append(row_payload.get("row"))
            tables[name]={"columns":payload.get("columns") or [],"rows":rows}
        if sorted(tables)!=sorted(graph.get("included_tables") or []): raise ValueError("object_graph_included_tables_mismatch")

        artifacts={}
        for name,ref in sorted((root.get("storage_artifact_refs") or {}).items()):
            obj=objects.get(ref) or {}
            if obj.get("kind")!="storage_artifact": raise ValueError("object_graph_storage_artifact_invalid:"+name)
            payload=obj.get("payload") or {}
            if payload.get("name")!=name or obj.get("refs"): raise ValueError("object_graph_storage_artifact_name_mismatch:"+name)
            artifacts[name]={k:payload.get(k) for k in ("exists","sha256","bytes_b64")}
        if set(artifacts)!={"main_db","wal","shm"}: raise ValueError("object_graph_storage_artifact_set_mismatch")

        token=str(graph["graph_digest"])[:16]
        stage_path=self.db_path.with_name(self.db_path.name+f".object-stage-{token}")
        snapshot_dir=self.db_path.parent/(self.db_path.name+f".object-evidence-{token}")
        snapshot_db=snapshot_dir/'certified.db'
        for path in (stage_path,Path(str(stage_path)+"-wal"),Path(str(stage_path)+"-shm")):
            if path.exists(): path.unlink()
        self._write_replay_storage_snapshot({"storage_artifacts":artifacts},snapshot_db)
        stage=JanusTwin(stage_path)
        try:
            self._import_partial_replay_tables(stage,tables)
            verified=stage.verify_storage_state_certificate(cert,trust_store,forensic_dag=dag,db_path=snapshot_db)
            if not verified.get("valid"):
                raise ValueError("object_replay_reconstruction_failed:"+",".join(verified.get("errors") or []))
            local_revalidation_rows=[tuple(r) for r in self.conn.execute("SELECT sequence,entry_digest,previous_entry_digest,truth_receipt_digest,entry_json,recorded_at FROM truth_revalidation_receipt_chain ORDER BY sequence")]
            stage.conn.backup(self.conn); self.conn.commit()
            if local_revalidation_rows:
                self.conn.executemany("INSERT INTO truth_revalidation_receipt_chain(sequence,entry_digest,previous_entry_digest,truth_receipt_digest,entry_json,recorded_at) VALUES (?,?,?,?,?,?)",local_revalidation_rows)
                self.conn.commit()
            if self.state_digest()!=cert.get("project_state_digest"): raise ValueError("object_replay_promotion_state_mismatch")
            receipt_core={
                "format":"janus-object-reconstruction-receipt-v1","graph_digest":graph.get("graph_digest"),
                "root_object":graph.get("root_object"),"certificate_digest":cert.get("certificate_digest"),
                "project_state_digest":self.state_digest(),"object_count":len(objects),"verified":True,
            }
            receipt={**receipt_core,"receipt_digest":sha256_bytes(stable_json(receipt_core).encode())}
            return {
                "valid":True,"format":"janus-object-replay-result-v1","graph_digest":graph.get("graph_digest"),
                "certificate_digest":cert.get("certificate_digest"),"project_state_digest":self.state_digest(),
                "exact_closure_verified":True,"object_count":len(objects),"storage_snapshot_verified":True,
                "storage_snapshot_db_path":str(snapshot_db),"certificate_verification":verified,
                "reconstruction_receipt":receipt,
            }
        finally:
            stage.close()
            for path in (stage_path,Path(str(stage_path)+"-wal"),Path(str(stage_path)+"-shm")):
                if path.exists(): path.unlink()

    def detect_storage_certificate_forks(self, entries: list[dict[str, Any]], certificates: dict[str,dict[str,Any]], trust_store: dict[str,str]) -> dict[str, Any]:
        """Verify signed branch entries and report forks without selecting a winner."""
        errors=[]; entry_errors=[]; groups: dict[tuple[str|None,str],dict[str,list[str]]]={}
        for entry in sorted(entries,key=lambda e:(str(e.get("previous_chain_digest")),str(e.get("previous_certificate_digest")),str(e.get("current_certificate_digest")),str(e.get("chain_digest")))):
            prev_digest=entry.get("previous_certificate_digest"); cur_digest=entry.get("current_certificate_digest")
            previous=certificates.get(prev_digest); current=certificates.get(cur_digest)
            if previous is None or current is None:
                errors.append("certificate_missing"); entry_errors.append({"chain_digest":entry.get("chain_digest"),"errors":["certificate_missing"]}); continue
            checked=self.verify_storage_certificate_chain_entry(entry,previous,current,trust_store,entry.get("previous_chain_digest"))
            if not checked.get("valid"):
                errors.append("invalid_chain_entry"); entry_errors.append({"chain_digest":entry.get("chain_digest"),"errors":checked.get("errors") or []}); continue
            key=(entry.get("previous_chain_digest"),str(prev_digest))
            groups.setdefault(key,{}).setdefault(str(cur_digest),[]).append(str(entry.get("chain_digest")))

        forks=[]
        for (previous_chain,previous_cert),descendants in sorted(groups.items(),key=lambda kv:(str(kv[0][0]),kv[0][1])):
            if len(descendants)<2: continue
            current_digests=sorted(descendants)
            branch_digests=sorted({d for values in descendants.values() for d in values})
            core={
                "format":"janus-storage-certificate-fork-evidence-v1","previous_chain_digest":previous_chain,
                "previous_certificate_digest":previous_cert,"current_certificate_digests":current_digests,
                "branch_chain_digests":branch_digests,
            }
            forks.append({**core,"evidence_digest":sha256_bytes(stable_json(core).encode())})
        return {
            "format":"janus-storage-certificate-fork-report-v1","valid":not errors,"errors":sorted(set(errors)),
            "entry_errors":entry_errors,"fork_detected":bool(forks),"forks":forks,"examined_entry_count":len(entries),
        }

    @staticmethod
    def negotiate_object_fetch(graph: dict[str, Any], cached_objects: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
        """Derive the exact missing content-addressed closure without transferring cached objects."""
        closure=JanusTwin._verify_object_replay_closure(graph)
        cached=cached_objects or {}; objects=graph["objects"]
        valid_cached=[]
        for digest,obj in sorted(cached.items()):
            if digest in objects and sha256_bytes(stable_json(obj).encode())==digest and obj==objects[digest]: valid_cached.append(digest)
        missing=sorted(set(closure["reachable"])-set(valid_cached))
        core={"format":"janus-object-fetch-negotiation-v1","graph_digest":graph["graph_digest"],"root_object":graph["root_object"],"cached_object_hashes":valid_cached,"missing_object_hashes":missing}
        return {**core,"missing_proof_digest":sha256_bytes(stable_json(core).encode())}

    @staticmethod
    def fulfill_object_fetch(graph: dict[str, Any], negotiation: dict[str, Any]) -> dict[str, Any]:
        if negotiation.get("format")!="janus-object-fetch-negotiation-v1": raise ValueError("unsupported_object_fetch_negotiation")
        core={k:negotiation.get(k) for k in ("format","graph_digest","root_object","cached_object_hashes","missing_object_hashes")}
        if sha256_bytes(stable_json(core).encode())!=negotiation.get("missing_proof_digest"): raise ValueError("missing_object_proof_invalid")
        if graph.get("graph_digest")!=negotiation.get("graph_digest") or graph.get("root_object")!=negotiation.get("root_object"): raise ValueError("fetch_negotiation_graph_mismatch")
        expected=JanusTwin.negotiate_object_fetch(graph,{h:graph["objects"][h] for h in negotiation.get("cached_object_hashes",[]) if h in graph["objects"]})
        if expected["missing_object_hashes"]!=negotiation.get("missing_object_hashes"): raise ValueError("missing_object_set_mismatch")
        supplied={h:graph["objects"][h] for h in negotiation["missing_object_hashes"]}
        return {"format":"janus-object-fetch-response-v1","graph_digest":graph["graph_digest"],"objects":supplied,"object_hashes":sorted(supplied)}

    @staticmethod
    def assemble_fetched_object_graph(graph_header: dict[str, Any], cached_objects: dict[str, dict[str, Any]], response: dict[str, Any]) -> dict[str, Any]:
        objects=dict(cached_objects); supplied=response.get("objects") or {}
        if sorted(supplied)!=response.get("object_hashes"): raise ValueError("fetch_response_overdelivery_or_omission")
        for h,obj in supplied.items():
            if sha256_bytes(stable_json(obj).encode())!=h: raise ValueError("fetch_response_hash_mismatch")
            if h in objects and objects[h]!=obj: raise ValueError("fetch_response_equivocation")
            objects[h]=obj
        assembled={**graph_header,"objects":objects,"object_count":len(objects)}
        JanusTwin._verify_object_replay_closure(assembled)
        return assembled

    @staticmethod
    def _seal_acquisition_session(core: dict[str, Any]) -> dict[str, Any]:
        return {**core,"receipt_digest":sha256_bytes(stable_json(core).encode())}

    @staticmethod
    def begin_object_acquisition_session(graph: dict[str, Any], cached_objects: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
        """Start a deterministic proof-carrying acquisition session from verified cached objects."""
        closure=JanusTwin._verify_object_replay_closure(graph); cached=cached_objects or {}; accepted={}
        for h,obj in sorted(cached.items()):
            if h not in graph["objects"] or sha256_bytes(stable_json(obj).encode())!=h or obj!=graph["objects"][h]:
                raise ValueError("cached_object_invalid")
            if h in closure["reachable"]: accepted[h]=obj
        missing=sorted(set(closure["reachable"])-set(accepted))
        core={"format":"janus-object-acquisition-session-v1","graph_digest":graph["graph_digest"],"root_object":graph["root_object"],"round":0,"previous_receipt_digest":None,"accepted_object_hashes":sorted(accepted),"accepted_objects":accepted,"missing_object_hashes":missing,"complete":not missing,"winner_selected":False}
        return JanusTwin._seal_acquisition_session(core)

    @staticmethod
    def advance_object_acquisition_session(graph: dict[str, Any], session: dict[str, Any], supplied_objects: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Accept one interruption-safe round; previous receipt authenticates cache continuity."""
        if session.get("format")!="janus-object-acquisition-session-v1": raise ValueError("unsupported_acquisition_session")
        if session.get("graph_digest")!=graph.get("graph_digest") or session.get("root_object")!=graph.get("root_object"):
            raise ValueError("session_graph_mismatch")
        core={k:v for k,v in session.items() if k!="receipt_digest"}
        if sha256_bytes(stable_json(core).encode())!=session.get("receipt_digest"): raise ValueError("session_receipt_invalid")
        accepted=dict(session.get("accepted_objects") or {})
        if sorted(accepted)!=session.get("accepted_object_hashes"): raise ValueError("session_receipt_invalid")
        for h,obj in accepted.items():
            if h not in graph["objects"] or sha256_bytes(stable_json(obj).encode())!=h or obj!=graph["objects"][h]: raise ValueError("session_receipt_invalid")
        requested=set(session.get("missing_object_hashes") or [])
        for h,obj in sorted((supplied_objects or {}).items()):
            if h not in requested: raise ValueError("unrequested_object")
            if sha256_bytes(stable_json(obj).encode())!=h or graph["objects"].get(h)!=obj: raise ValueError("object_hash_mismatch")
            accepted[h]=obj
        closure=JanusTwin._verify_object_replay_closure(graph); missing=sorted(set(closure["reachable"])-set(accepted))
        next_core={"format":"janus-object-acquisition-session-v1","graph_digest":graph["graph_digest"],"root_object":graph["root_object"],"round":int(session.get("round") or 0)+1,"previous_receipt_digest":session["receipt_digest"],"accepted_object_hashes":sorted(accepted),"accepted_objects":accepted,"missing_object_hashes":missing,"complete":not missing,"winner_selected":False}
        return JanusTwin._seal_acquisition_session(next_core)

    @staticmethod
    def finalize_object_acquisition_session(graph: dict[str, Any], session: dict[str, Any]) -> dict[str, Any]:
        """Finalize only a complete authenticated session and re-run exact closure verification."""
        if session.get("graph_digest")!=graph.get("graph_digest") or session.get("root_object")!=graph.get("root_object"): raise ValueError("session_graph_mismatch")
        core={k:v for k,v in session.items() if k!="receipt_digest"}
        if sha256_bytes(stable_json(core).encode())!=session.get("receipt_digest"): raise ValueError("session_receipt_invalid")
        if not session.get("complete") or session.get("missing_object_hashes"): raise ValueError("acquisition_incomplete")
        objects=dict(session.get("accepted_objects") or {})
        assembled={**{k:v for k,v in graph.items() if k!="objects"},"objects":objects,"object_count":len(objects)}
        JanusTwin._verify_object_replay_closure(assembled)
        return assembled

    @staticmethod
    def _compact_cache_digest(accepted_hashes: list[str]) -> str:
        return sha256_bytes(stable_json({"format":"janus-compact-cache-commitment-v1","accepted_object_hashes":sorted(accepted_hashes)}).encode())

    @staticmethod
    def _verify_compact_receipt(receipt: dict[str, Any], graph: dict[str, Any]) -> None:
        if receipt.get("format")!="janus-compact-acquisition-receipt-v1": raise ValueError("unsupported_acquisition_session")
        if receipt.get("graph_digest")!=graph.get("graph_digest") or receipt.get("root_object")!=graph.get("root_object"):
            raise ValueError("session_graph_mismatch")
        core={k:v for k,v in receipt.items() if k!="receipt_digest"}
        if sha256_bytes(stable_json(core).encode())!=receipt.get("receipt_digest"): raise ValueError("session_receipt_invalid")
        accepted=receipt.get("accepted_object_hashes") or []
        if accepted!=sorted(set(accepted)): raise ValueError("session_receipt_invalid")
        if receipt.get("cache_commitment")!=JanusTwin._compact_cache_digest(accepted): raise ValueError("session_receipt_invalid")
        closure=JanusTwin._verify_object_replay_closure(graph); reachable=set(closure["reachable"])
        if not set(accepted).issubset(reachable): raise ValueError("session_receipt_invalid")
        expected_missing=sorted(reachable-set(accepted))
        if receipt.get("missing_object_hashes")!=expected_missing or bool(receipt.get("complete"))!=bool(not expected_missing):
            raise ValueError("session_receipt_invalid")
        if receipt.get("winner_selected") is not False: raise ValueError("session_receipt_invalid")

    @staticmethod
    def begin_compact_acquisition_session(graph: dict[str, Any], cached_objects: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
        """Create a portable receipt that commits to cache hashes without embedding object bytes."""
        closure=JanusTwin._verify_object_replay_closure(graph); cached=cached_objects or {}; accepted=[]
        for h,obj in sorted(cached.items()):
            if h not in graph["objects"] or h not in closure["reachable"] or sha256_bytes(stable_json(obj).encode())!=h or obj!=graph["objects"][h]:
                raise ValueError("cached_object_invalid")
            accepted.append(h)
        accepted=sorted(accepted); missing=sorted(set(closure["reachable"])-set(accepted))
        core={"format":"janus-compact-acquisition-receipt-v1","graph_digest":graph["graph_digest"],"root_object":graph["root_object"],"round":0,"previous_receipt_digest":None,"accepted_object_hashes":accepted,"cache_commitment":JanusTwin._compact_cache_digest(accepted),"missing_object_hashes":missing,"complete":not missing,"winner_selected":False}
        return JanusTwin._seal_acquisition_session(core)

    @staticmethod
    def advance_compact_acquisition_session(graph: dict[str, Any], receipt: dict[str, Any], cache: dict[str, dict[str, Any]], supplied_objects: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Advance using an independently held content-addressed cache; reject rollback, poison and retransmit."""
        JanusTwin._verify_compact_receipt(receipt,graph)
        prior=set(receipt["accepted_object_hashes"]); supplied=supplied_objects or {}; requested=set(receipt["missing_object_hashes"])
        for h in supplied:
            if h not in requested: raise ValueError("unrequested_object")
        expected_keys=prior|set(supplied)
        if set(cache)!=expected_keys: raise ValueError("cache_continuity_mismatch")
        for h,obj in sorted(cache.items()):
            if h not in graph["objects"] or sha256_bytes(stable_json(obj).encode())!=h or obj!=graph["objects"][h]: raise ValueError("cache_object_invalid")
        for h,obj in sorted(supplied.items()):
            if cache.get(h)!=obj or sha256_bytes(stable_json(obj).encode())!=h or graph["objects"].get(h)!=obj: raise ValueError("object_hash_mismatch")
        accepted=sorted(expected_keys); closure=JanusTwin._verify_object_replay_closure(graph); missing=sorted(set(closure["reachable"])-expected_keys)
        core={"format":"janus-compact-acquisition-receipt-v1","graph_digest":graph["graph_digest"],"root_object":graph["root_object"],"round":int(receipt["round"])+1,"previous_receipt_digest":receipt["receipt_digest"],"accepted_object_hashes":accepted,"cache_commitment":JanusTwin._compact_cache_digest(accepted),"missing_object_hashes":missing,"complete":not missing,"winner_selected":False}
        return JanusTwin._seal_acquisition_session(core)

    @staticmethod
    def finalize_compact_acquisition_session(graph: dict[str, Any], receipt: dict[str, Any], cache: dict[str, dict[str, Any]]) -> dict[str, Any]:
        JanusTwin._verify_compact_receipt(receipt,graph)
        if not receipt.get("complete"): raise ValueError("acquisition_incomplete")
        if set(cache)!=set(receipt["accepted_object_hashes"]): raise ValueError("cache_continuity_mismatch")
        for h,obj in cache.items():
            if sha256_bytes(stable_json(obj).encode())!=h or graph["objects"].get(h)!=obj: raise ValueError("cache_object_invalid")
        assembled={**{k:v for k,v in graph.items() if k!="objects"},"objects":dict(cache),"object_count":len(cache)}
        JanusTwin._verify_object_replay_closure(assembled); return assembled

    @staticmethod
    def verify_compact_acquisition_receipt_chain(receipts: list[dict[str, Any]], graph: dict[str, Any]) -> dict[str, Any]:
        errors=[]; previous=None; expected_round=0
        for receipt in receipts:
            try: JanusTwin._verify_compact_receipt(receipt,graph)
            except ValueError as exc: errors.append(str(exc)); continue
            if receipt.get("round")!=expected_round: errors.append("round_sequence_mismatch")
            if receipt.get("previous_receipt_digest")!=previous: errors.append("receipt_chain_splice")
            previous=receipt.get("receipt_digest"); expected_round+=1
        return {"format":"janus-compact-acquisition-chain-verification-v1","valid":not errors,"errors":sorted(set(errors)),"receipt_count":len(receipts),"head_receipt_digest":previous if not errors else None,"winner_selected":False}

    @staticmethod
    def crosslink_compact_acquisition_provenance(receipts: list[dict[str, Any]], graph: dict[str, Any]) -> dict[str, Any]:
        """Bind a verified compact acquisition chain into proof lineage as descriptive evidence only."""
        if not receipts:
            raise ValueError("acquisition_receipt_chain_empty")
        checked=JanusTwin.verify_compact_acquisition_receipt_chain(receipts,graph)
        if not checked.get("valid"):
            raise ValueError("acquisition_receipt_chain_invalid:"+",".join(checked.get("errors") or []))
        head=receipts[-1]
        root_obj=(graph.get("objects") or {}).get(graph.get("root_object")) or {}
        root_payload=root_obj.get("payload") or {}
        core={
            "format":"janus-acquisition-provenance-crosslink-v1",
            "graph_digest":graph.get("graph_digest"),
            "root_object":graph.get("root_object"),
            "certificate_ref":root_payload.get("certificate_ref"),
            "head_receipt_digest":checked.get("head_receipt_digest"),
            "receipt_count":checked.get("receipt_count"),
            "accepted_object_hashes":list(head.get("accepted_object_hashes") or []),
            "missing_object_hashes":list(head.get("missing_object_hashes") or []),
            "complete":bool(head.get("complete")),
            "possession_continuity_verified":True,
            "temporal_truth_validity_asserted":False,
            "authority":"descriptive_only",
            "winner_selected":False,
        }
        edge={
            "relation":"descriptive_acquisition_provenance",
            "from_receipt_digest":core["head_receipt_digest"],
            "to_graph_digest":core["graph_digest"],
            "to_certificate_ref":core["certificate_ref"],
            "authority":"none",
        }
        core["proof_lineage_edges"]=[edge]
        return {**core,"crosslink_digest":sha256_bytes(stable_json(core).encode())}

    @staticmethod
    def build_compact_cache_snapshot(graph: dict[str, Any], receipt: dict[str, Any], cache: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Snapshot possession bytes separately from the compact receipt; no truth-validity claim is created."""
        JanusTwin._verify_compact_receipt(receipt,graph)
        accepted=receipt.get("accepted_object_hashes") or []
        if set(cache)!=set(accepted):
            raise ValueError("cache_continuity_mismatch")
        for h,obj in sorted(cache.items()):
            if h not in graph.get("objects",{}) or sha256_bytes(stable_json(obj).encode())!=h or graph["objects"].get(h)!=obj:
                raise ValueError("cache_object_invalid")
        core={
            "format":"janus-compact-cache-snapshot-v1",
            "graph_digest":graph.get("graph_digest"),
            "root_object":graph.get("root_object"),
            "receipt":receipt,
            "receipt_digest":receipt.get("receipt_digest"),
            "accepted_object_hashes":list(accepted),
            "cache_commitment":receipt.get("cache_commitment"),
            "objects":{h:cache[h] for h in sorted(cache)},
            "temporal_truth_validity_asserted":False,
            "winner_selected":False,
        }
        return {**core,"snapshot_digest":sha256_bytes(stable_json(core).encode())}

    @staticmethod
    def restore_compact_cache_snapshot(graph: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
        """Verify and restore possession continuity while explicitly requiring separate temporal-truth revalidation."""
        if snapshot.get("format")!="janus-compact-cache-snapshot-v1":
            raise ValueError("unsupported_cache_snapshot")
        core={k:v for k,v in snapshot.items() if k!="snapshot_digest"}
        if sha256_bytes(stable_json(core).encode())!=snapshot.get("snapshot_digest"):
            raise ValueError("cache_snapshot_invalid")
        if snapshot.get("graph_digest")!=graph.get("graph_digest") or snapshot.get("root_object")!=graph.get("root_object"):
            raise ValueError("cache_snapshot_graph_mismatch")
        receipt=snapshot.get("receipt") or {}
        JanusTwin._verify_compact_receipt(receipt,graph)
        if receipt.get("receipt_digest")!=snapshot.get("receipt_digest"):
            raise ValueError("cache_snapshot_receipt_mismatch")
        accepted=receipt.get("accepted_object_hashes") or []
        if accepted!=snapshot.get("accepted_object_hashes") or receipt.get("cache_commitment")!=snapshot.get("cache_commitment"):
            raise ValueError("cache_snapshot_commitment_mismatch")
        objects=dict(snapshot.get("objects") or {})
        if set(objects)!=set(accepted):
            raise ValueError("cache_snapshot_object_set_mismatch")
        for h,obj in sorted(objects.items()):
            if h not in graph.get("objects",{}) or sha256_bytes(stable_json(obj).encode())!=h or graph["objects"].get(h)!=obj:
                raise ValueError("cache_snapshot_object_invalid")
        proof_core={
            "format":"janus-cache-snapshot-restore-proof-v1",
            "graph_digest":graph.get("graph_digest"),
            "snapshot_digest":snapshot.get("snapshot_digest"),
            "receipt_digest":receipt.get("receipt_digest"),
            "cache_commitment":receipt.get("cache_commitment"),
            "restored_object_hashes":sorted(objects),
            "possession_continuity_verified":True,
            "temporal_truth_validity_asserted":False,
            "requires_independent_truth_revalidation":True,
            "winner_selected":False,
        }
        proof={**proof_core,"proof_digest":sha256_bytes(stable_json(proof_core).encode())}
        return {"cache":objects,"proof":proof}

    @staticmethod
    def generate_compact_receipt_chain_adversarial_schedules(receipts: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """Generate deterministic splice/out-of-order/duplicate-round schedules for verifier testing."""
        if len(receipts)<2:
            raise ValueError("insufficient_receipts_for_adversarial_schedule")
        duplicate=[dict(r) for r in receipts]
        duplicate.insert(1,dict(receipts[0]))
        out_of_order=[dict(r) for r in receipts]
        out_of_order[0],out_of_order[1]=out_of_order[1],out_of_order[0]
        spliced=[dict(r) for r in receipts]
        tampered=dict(spliced[1]); tampered["previous_receipt_digest"]="f"*64
        tampered_core={k:v for k,v in tampered.items() if k!="receipt_digest"}
        tampered["receipt_digest"]=sha256_bytes(stable_json(tampered_core).encode())
        spliced[1]=tampered
        return {"duplicate_round":duplicate,"out_of_order":out_of_order,"splice":spliced}

    @staticmethod
    def _portable_provenance_replay_bundle_core(bundle: dict[str, Any]) -> dict[str, Any]:
        return {k:bundle.get(k) for k in (
            "format","graph","receipts","provenance_crosslink","cache_snapshot",
            "possession_continuity_only","temporal_truth_validity_asserted",
            "requires_independent_truth_revalidation","winner_selected",
        )}

    @staticmethod
    def build_portable_provenance_replay_bundle(graph: dict[str, Any], receipts: list[dict[str, Any]], snapshot: dict[str, Any]) -> dict[str, Any]:
        """Package compact acquisition provenance + cache snapshot for independent receiver replay.

        The bundle verifies possession/provenance only. Temporal truth may be asserted only by a
        separate fresh-receiver object replay/certificate verification.
        """
        if not receipts:
            raise ValueError("acquisition_receipt_chain_empty")
        chain=JanusTwin.verify_compact_acquisition_receipt_chain(receipts,graph)
        if not chain.get("valid"):
            raise ValueError("acquisition_receipt_chain_invalid:"+",".join(chain.get("errors") or []))
        crosslink=JanusTwin.crosslink_compact_acquisition_provenance(receipts,graph)
        restored=JanusTwin.restore_compact_cache_snapshot(graph,snapshot)
        if receipts[-1].get("receipt_digest")!=snapshot.get("receipt_digest"):
            raise ValueError("portable_snapshot_head_mismatch")
        if receipts[-1].get("receipt_digest")!=crosslink.get("head_receipt_digest"):
            raise ValueError("portable_crosslink_head_mismatch")
        core={
            "format":"janus-portable-provenance-replay-bundle-v1",
            "graph":graph,
            "receipts":receipts,
            "provenance_crosslink":crosslink,
            "cache_snapshot":snapshot,
            "possession_continuity_only":True,
            "temporal_truth_validity_asserted":False,
            "requires_independent_truth_revalidation":True,
            "winner_selected":False,
        }
        return {**core,"bundle_digest":sha256_bytes(stable_json(core).encode())}

    @staticmethod
    def verify_portable_provenance_replay_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
        if bundle.get("format")!="janus-portable-provenance-replay-bundle-v1":
            raise ValueError("unsupported_portable_provenance_bundle")
        core=JanusTwin._portable_provenance_replay_bundle_core(bundle)
        if sha256_bytes(stable_json(core).encode())!=bundle.get("bundle_digest"):
            raise ValueError("portable_provenance_bundle_digest_mismatch")
        if bundle.get("possession_continuity_only") is not True or bundle.get("temporal_truth_validity_asserted") is not False:
            raise ValueError("portable_provenance_authority_violation")
        if bundle.get("requires_independent_truth_revalidation") is not True or bundle.get("winner_selected") is not False:
            raise ValueError("portable_provenance_authority_violation")
        graph=bundle.get("graph") or {}; receipts=bundle.get("receipts") or []; snapshot=bundle.get("cache_snapshot") or {}
        JanusTwin._verify_object_replay_closure(graph)
        chain=JanusTwin.verify_compact_acquisition_receipt_chain(receipts,graph)
        if not chain.get("valid"):
            raise ValueError("acquisition_receipt_chain_invalid:"+",".join(chain.get("errors") or []))
        expected_crosslink=JanusTwin.crosslink_compact_acquisition_provenance(receipts,graph)
        if stable_json(expected_crosslink)!=stable_json(bundle.get("provenance_crosslink") or {}):
            raise ValueError("portable_provenance_crosslink_mismatch")
        restored=JanusTwin.restore_compact_cache_snapshot(graph,snapshot)
        head=receipts[-1] if receipts else {}
        if head.get("receipt_digest")!=snapshot.get("receipt_digest"):
            raise ValueError("portable_snapshot_head_mismatch")
        if head.get("receipt_digest")!=expected_crosslink.get("head_receipt_digest"):
            raise ValueError("portable_crosslink_head_mismatch")
        if not head.get("complete") or head.get("missing_object_hashes"):
            raise ValueError("portable_provenance_incomplete")
        return {
            "format":"janus-portable-provenance-replay-verification-v1",
            "valid":True,
            "bundle_digest":bundle.get("bundle_digest"),
            "graph_digest":graph.get("graph_digest"),
            "snapshot_digest":snapshot.get("snapshot_digest"),
            "restore_proof_digest":restored["proof"]["proof_digest"],
            "head_receipt_digest":head.get("receipt_digest"),
            "possession_continuity_verified":True,
            "temporal_truth_validity_asserted":False,
            "requires_independent_truth_revalidation":True,
            "winner_selected":False,
        }

    @staticmethod
    def build_replay_truth_revalidation_receipt(bundle: dict[str, Any], restore_proof: dict[str, Any], replay_result: dict[str, Any]) -> dict[str, Any]:
        """Bind possession proof to independent receiver replay evidence without deriving truth from possession."""
        if not replay_result.get("valid") or not replay_result.get("exact_closure_verified"):
            raise ValueError("truth_revalidation_not_verified")
        certificate_verification=replay_result.get("certificate_verification") or {}
        reconstruction=replay_result.get("reconstruction_receipt") or {}
        if not certificate_verification.get("valid") or not reconstruction.get("verified"):
            raise ValueError("truth_revalidation_not_verified")
        if restore_proof.get("possession_continuity_verified") is not True or restore_proof.get("temporal_truth_validity_asserted") is not False:
            raise ValueError("truth_revalidation_possession_proof_invalid")
        if restore_proof.get("graph_digest")!=(bundle.get("graph") or {}).get("graph_digest"):
            raise ValueError("truth_revalidation_graph_mismatch")
        if replay_result.get("graph_digest")!=(bundle.get("graph") or {}).get("graph_digest"):
            raise ValueError("truth_revalidation_graph_mismatch")
        core={
            "format":"janus-replay-truth-revalidation-receipt-v1",
            "bundle_digest":bundle.get("bundle_digest"),
            "graph_digest":replay_result.get("graph_digest"),
            "snapshot_digest":restore_proof.get("snapshot_digest"),
            "restore_proof_digest":restore_proof.get("proof_digest"),
            "reconstruction_receipt_digest":reconstruction.get("receipt_digest"),
            "certificate_digest":replay_result.get("certificate_digest"),
            "project_state_digest":replay_result.get("project_state_digest"),
            "basis":"independent_receiver_object_replay",
            "possession_continuity_verified":True,
            "possession_evidence_truth_authority":False,
            "temporal_truth_revalidated":True,
            "winner_selected":False,
        }
        return {**core,"receipt_digest":sha256_bytes(stable_json(core).encode())}

    def replay_portable_provenance_bundle(self, bundle: dict[str, Any], trust_store: dict[str,str]) -> dict[str, Any]:
        """Verify portable possession evidence first, then independently revalidate temporal truth on this receiver."""
        portable=JanusTwin.verify_portable_provenance_replay_bundle(bundle)
        graph=bundle["graph"]; snapshot=bundle["cache_snapshot"]
        restored=JanusTwin.restore_compact_cache_snapshot(graph,snapshot)
        # Possession continuity is intentionally insufficient here. The receiver must independently
        # reconstruct the graph and verify the certified state before truth is revalidated.
        replay=self.import_and_verify_object_replay_graph(graph,trust_store)
        truth=JanusTwin.build_replay_truth_revalidation_receipt(bundle,restored["proof"],replay)
        return {
            "format":"janus-portable-provenance-fresh-receiver-result-v1",
            "valid":True,
            "portable_verification":portable,
            "restore_proof":restored["proof"],
            "receiver_replay":replay,
            "truth_revalidation_receipt":truth,
            "winner_selected":False,
        }

    @staticmethod
    def _reseal_portable_provenance_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
        out=json.loads(json.dumps(bundle))
        core=JanusTwin._portable_provenance_replay_bundle_core(out)
        out["bundle_digest"]=sha256_bytes(stable_json(core).encode())
        return out

    @staticmethod
    def generate_portable_provenance_corruption_schedules(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Generate deterministic semantic corruptions whose outer bundle digests remain self-consistent."""
        base=json.loads(json.dumps(bundle))

        truncated=json.loads(json.dumps(base)); truncated["receipts"]=truncated["receipts"][:-1]
        truncated=JanusTwin._reseal_portable_provenance_bundle(truncated)

        cross=json.loads(json.dumps(base)); crosslink=cross["provenance_crosslink"]
        crosslink["head_receipt_digest"]="0"*64
        cross_core={k:v for k,v in crosslink.items() if k!="crosslink_digest"}
        crosslink["crosslink_digest"]=sha256_bytes(stable_json(cross_core).encode())
        cross=JanusTwin._reseal_portable_provenance_bundle(cross)

        snap=json.loads(json.dumps(base)); snapshot=snap["cache_snapshot"]
        object_hash=sorted(snapshot.get("objects") or {})[0]
        snapshot["objects"][object_hash]={"corrupted":True}
        snapshot_core={k:v for k,v in snapshot.items() if k!="snapshot_digest"}
        snapshot["snapshot_digest"]=sha256_bytes(stable_json(snapshot_core).encode())
        snap=JanusTwin._reseal_portable_provenance_bundle(snap)
        return {
            "receipt_chain_truncation":truncated,
            "crosslink_head_mismatch":cross,
            "snapshot_object_substitution":snap,
        }

    @staticmethod
    def verify_replay_truth_revalidation_receipt(receipt: dict[str, Any], bundle: dict[str, Any] | None = None, replay_result: dict[str, Any] | None = None) -> dict[str, Any]:
        if receipt.get("format")!="janus-replay-truth-revalidation-receipt-v1":
            raise ValueError("unsupported_truth_revalidation_receipt")
        core={k:v for k,v in receipt.items() if k!="receipt_digest"}
        if sha256_bytes(stable_json(core).encode())!=receipt.get("receipt_digest"):
            raise ValueError("truth_revalidation_receipt_digest_invalid")
        if receipt.get("basis")!="independent_receiver_object_replay" or receipt.get("temporal_truth_revalidated") is not True:
            raise ValueError("truth_revalidation_receipt_invalid")
        if receipt.get("possession_continuity_verified") is not True or receipt.get("possession_evidence_truth_authority") is not False or receipt.get("winner_selected") is not False:
            raise ValueError("truth_revalidation_receipt_invalid")
        if bundle is not None:
            if receipt.get("bundle_digest")!=bundle.get("bundle_digest") or receipt.get("graph_digest")!=(bundle.get("graph") or {}).get("graph_digest"):
                raise ValueError("truth_revalidation_bundle_binding_mismatch")
        if replay_result is not None:
            reconstruction=replay_result.get("reconstruction_receipt") or {}
            if not replay_result.get("valid") or not replay_result.get("exact_closure_verified") or not (replay_result.get("certificate_verification") or {}).get("valid"):
                raise ValueError("truth_revalidation_not_verified")
            if receipt.get("graph_digest")!=replay_result.get("graph_digest"):
                raise ValueError("truth_revalidation_replay_binding_mismatch")
            if receipt.get("certificate_digest")!=replay_result.get("certificate_digest") or receipt.get("project_state_digest")!=replay_result.get("project_state_digest"):
                raise ValueError("truth_revalidation_replay_binding_mismatch")
            if receipt.get("reconstruction_receipt_digest")!=reconstruction.get("receipt_digest"):
                raise ValueError("truth_revalidation_replay_binding_mismatch")
        return {"valid":True,"receipt_digest":receipt.get("receipt_digest"),"winner_selected":False}

    @staticmethod
    def _truth_revalidation_chain_entry_core(entry: dict[str, Any]) -> dict[str, Any]:
        return {k:entry.get(k) for k in (
            "format","sequence","previous_entry_digest","truth_receipt_digest","bundle_digest",
            "graph_digest","certificate_digest","project_state_digest",
        )}

    def append_truth_revalidation_receipt(self, receipt: dict[str, Any], replay_result: dict[str, Any], expected_previous_entry_digest: str | None) -> dict[str, Any]:
        """Append one independently verified truth-revalidation receipt to a receiver-local durable chain."""
        JanusTwin.verify_replay_truth_revalidation_receipt(receipt,replay_result=replay_result)
        row=self.conn.execute("SELECT sequence,entry_digest FROM truth_revalidation_receipt_chain ORDER BY sequence DESC LIMIT 1").fetchone()
        current_head=row["entry_digest"] if row else None
        if current_head!=expected_previous_entry_digest:
            raise ValueError("revalidation_chain_stale_head")
        sequence=(int(row["sequence"])+1) if row else 1
        core={
            "format":"janus-truth-revalidation-chain-entry-v1",
            "sequence":sequence,
            "previous_entry_digest":current_head,
            "truth_receipt_digest":receipt.get("receipt_digest"),
            "bundle_digest":receipt.get("bundle_digest"),
            "graph_digest":receipt.get("graph_digest"),
            "certificate_digest":receipt.get("certificate_digest"),
            "project_state_digest":receipt.get("project_state_digest"),
        }
        entry={**core,"entry_digest":sha256_bytes(stable_json(core).encode())}
        self.conn.execute(
            "INSERT INTO truth_revalidation_receipt_chain(sequence,entry_digest,previous_entry_digest,truth_receipt_digest,entry_json,recorded_at) VALUES (?,?,?,?,?,?)",
            (sequence,entry["entry_digest"],current_head,receipt.get("receipt_digest"),stable_json(entry),utcnow()),
        )
        self.conn.commit()
        return entry

    def export_truth_revalidation_receipt_chain(self) -> list[dict[str, Any]]:
        rows=self.conn.execute("SELECT entry_json FROM truth_revalidation_receipt_chain ORDER BY sequence").fetchall()
        return [json.loads(r["entry_json"]) for r in rows]

    @staticmethod
    def verify_truth_revalidation_receipt_chain(entries: list[dict[str, Any]], expected_head_digest: str | None = None) -> dict[str, Any]:
        errors=[]; previous=None; expected_sequence=1
        for entry in entries:
            core=JanusTwin._truth_revalidation_chain_entry_core(entry)
            if entry.get("format")!="janus-truth-revalidation-chain-entry-v1" or sha256_bytes(stable_json(core).encode())!=entry.get("entry_digest"):
                errors.append("revalidation_entry_digest_invalid")
            if entry.get("sequence")!=expected_sequence:
                errors.append("revalidation_chain_sequence_mismatch")
            if entry.get("previous_entry_digest")!=previous:
                errors.append("revalidation_chain_splice")
            previous=entry.get("entry_digest"); expected_sequence+=1
        if expected_head_digest is not None and previous!=expected_head_digest:
            errors.append("revalidation_chain_rollback")
        return {
            "format":"janus-truth-revalidation-chain-verification-v1","valid":not errors,
            "errors":sorted(set(errors)),"entry_count":len(entries),"head_entry_digest":previous if not errors else None,
            "winner_selected":False,
        }

    @staticmethod
    def build_cross_receiver_replay_equivalence(receiver_a_id: str, receipt_a: dict[str, Any], receiver_b_id: str, receipt_b: dict[str, Any]) -> dict[str, Any]:
        if not receiver_a_id or not receiver_b_id or receiver_a_id==receiver_b_id:
            raise ValueError("cross_receiver_identity_invalid")
        JanusTwin.verify_replay_truth_revalidation_receipt(receipt_a)
        JanusTwin.verify_replay_truth_revalidation_receipt(receipt_b)
        fields=("bundle_digest","graph_digest","certificate_digest","project_state_digest")
        if any(receipt_a.get(k)!=receipt_b.get(k) for k in fields):
            raise ValueError("cross_receiver_replay_mismatch")
        core={
            "format":"janus-cross-receiver-replay-equivalence-v1",
            "receiver_ids":sorted([receiver_a_id,receiver_b_id]),
            "truth_receipt_digests":sorted([receipt_a.get("receipt_digest"),receipt_b.get("receipt_digest")]),
            "bundle_digest":receipt_a.get("bundle_digest"),
            "graph_digest":receipt_a.get("graph_digest"),
            "certificate_digest":receipt_a.get("certificate_digest"),
            "project_state_digest":receipt_a.get("project_state_digest"),
            "equivalent":True,
            "authority":"descriptive_cross_receiver_consistency",
            "winner_selected":False,
        }
        return {**core,"equivalence_digest":sha256_bytes(stable_json(core).encode())}

    @staticmethod
    def generate_truth_revalidation_receipt_corruption_schedules(receipt: dict[str, Any]) -> dict[str, dict[str, Any]]:
        def mutate(field: str, value: str) -> dict[str, Any]:
            out=json.loads(json.dumps(receipt)); out[field]=value
            core={k:v for k,v in out.items() if k!="receipt_digest"}
            out["receipt_digest"]=sha256_bytes(stable_json(core).encode())
            return out
        return {
            "stale_bundle":mutate("bundle_digest","0"*64),
            "forged_certificate":mutate("certificate_digest","1"*64),
            "forged_reconstruction":mutate("reconstruction_receipt_digest","2"*64),
        }

    @staticmethod
    def crosslink_certificate_forks_to_temporal_conflicts(fork_report: dict[str, Any]) -> dict[str, Any]:
        """Map verified storage branches into descriptive JANUS conflict evidence; never adjudicate a winner."""
        if not fork_report.get("valid"): raise ValueError("invalid_fork_report")
        conflicts=[]
        for fork in fork_report.get("forks") or []:
            core={"kind":"certificate_branch_conflict","previous_certificate_digest":fork["previous_certificate_digest"],"branch_certificate_digests":sorted(fork["current_certificate_digests"]),"fork_evidence_digest":fork["evidence_digest"],"resolution":{"status":"quarantined","reason":"external_branch_resolution_required"},"proof_required":True}
            conflicts.append({**core,"conflict_digest":sha256_bytes(stable_json(core).encode())})
        return {"format":"janus-certificate-temporal-conflict-crosslink-v1","conflicts":conflicts,"winner_selected":False}

    @staticmethod
    def run_host_enospc_probe() -> dict[str, Any]:
        """Use the kernel /dev/full device, when exposed, to obtain a safe real ENOSPC write failure."""
        target=Path('/dev/full')
        core={"format":"janus-host-enospc-fault-probe-v1","mechanism":"dev_full","classification":"unavailable","errno":None,"errno_name":None,"authoritative_path_touched":False}
        if target.exists():
            try:
                with target.open('wb',buffering=0) as f: f.write(b'JANUS')
            except OSError as exc:
                core.update({"classification":"kernel_storage_capacity" if exc.errno==28 else "kernel_storage_error","errno":exc.errno,"errno_name":errno.errorcode.get(exc.errno)})
        return {**core,"probe_digest":sha256_bytes(stable_json(core).encode())}

    @staticmethod
    def run_host_file_size_limit_probe(root: str | Path, max_file_bytes: int = 4096) -> dict[str, Any]:
        """Exercise a kernel-enforced RLIMIT_FSIZE failure in an isolated child process."""
        root=Path(root); root.mkdir(parents=True,exist_ok=True)
        target=root/'fsize.probe'
        script="""import errno,json,os,resource,signal,sys\nlimit=int(sys.argv[1]); path=sys.argv[2]\nresource.setrlimit(resource.RLIMIT_FSIZE,(limit,limit))\nsig=[0]\ndef on_xfsz(signum,frame): sig[0]+=1\nsignal.signal(signal.SIGXFSZ,on_xfsz)\nfd=os.open(path,os.O_CREAT|os.O_WRONLY|os.O_TRUNC,0o600); total=0; err=None\ntry:\n    while True:\n        n=os.write(fd,b'X'*1024); total+=n\nexcept OSError as exc:\n    err=exc\nfinally:\n    try: os.fsync(fd)\n    except OSError: pass\n    os.close(fd)\nprint(json.dumps({'bytes_written':total,'errno':getattr(err,'errno',None),'errno_name':errno.errorcode.get(getattr(err,'errno',None)),'sigxfsz_count':sig[0]},sort_keys=True))\n"""
        proc=subprocess.run([sys.executable,"-c",script,str(int(max_file_bytes)),str(target)],cwd=root,text=True,capture_output=True,check=False)
        try: child=json.loads((proc.stdout or "").strip().splitlines()[-1])
        except Exception: child={"bytes_written":0,"errno":None,"errno_name":None,"sigxfsz_count":0}
        core={
            "format":"janus-host-file-size-fault-probe-v1","mechanism":"RLIMIT_FSIZE",
            "classification":"kernel_file_size_limit" if child.get("errno")==27 else "unexpected",
            "max_file_bytes":int(max_file_bytes),"bytes_written":int(child.get("bytes_written") or 0),
            "errno":child.get("errno"),"errno_name":child.get("errno_name"),"sigxfsz_count":int(child.get("sigxfsz_count") or 0),
            "returncode":proc.returncode,"authoritative_path_touched":False,
        }
        return {**core,"probe_digest":sha256_bytes(stable_json(core).encode())}

    def export_handoff(self, out_dir: str | os.PathLike[str]) -> dict[str, Any]:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        data = {
            "format": "janus-handoff-v1",
            "exported_at": utcnow(),
            "state_digest": self.state_digest(),
            "status": self.status(),
            "components": [dict(r) for r in self.conn.execute("SELECT * FROM components ORDER BY name")],
            "dependencies": [dict(r) for r in self.conn.execute("SELECT * FROM dependencies ORDER BY src,dst,kind")],
            "current_facts": self.current_facts(),
            "contradictions": self.contradictions(),
            "temporal_conflicts": self.temporal_conflicts(),
            "temporal_normalization_proposals": self.temporal_normalization_proposals(),
            "normalization_decisions": [dict(r) for r in self.conn.execute("SELECT * FROM normalization_decisions ORDER BY known_at,decision_id")],
            "normalization_overlays": self.normalization_overlays(),
            "authority_precedence": [dict(r) for r in self.conn.execute("SELECT * FROM authority_precedence ORDER BY subject_prefix,predicate,authority")],
            "evidence_precedence": [dict(r) for r in self.conn.execute("SELECT * FROM evidence_precedence ORDER BY confidence")],
            "invariants": [dict(r) for r in self.conn.execute("SELECT invariant_hash,text,source FROM invariants ORDER BY invariant_hash")],
            "prioritized_candidates": self.prioritized_candidates(),
            "proof_bundles": [dict(r) for r in self.conn.execute("SELECT change_id,bundle_hash,status,bundle_json FROM proof_bundles ORDER BY change_id")],
            "proof_lifecycle_events": [dict(r) for r in self.conn.execute("SELECT event_id,change_id,status,known_at,actor,reason,superseded_by FROM proof_lifecycle_events ORDER BY known_at,event_id")],
        }
        json_path = out / "handoff.json"
        json_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        top = data["prioritized_candidates"][0] if data["prioritized_candidates"] else None
        lines = [
            "# JANUS Generated Handoff",
            "",
            f"State digest: `{data['state_digest']}`",
            "",
            "## Current status",
            "",
            "```json",
            json.dumps(data["status"], indent=2, sort_keys=True),
            "```",
            "",
            "## Top next action",
            "",
        ]
        if top:
            lines += [f"**{top['id']} — {top['title']}**", "", f"Priority score: `{top['score']:.6f}`", ""]
        else:
            lines += ["No active candidate is registered.", ""]
        lines += [
            "## Receive rule",
            "",
            "Verify the live project state before mutation. Treat this handoff as evidence with a content digest, not as a substitute for reconciliation.",
            "",
            "## Authority rule",
            "",
            "JANUS owns project-twin/reconciliation/handoff logic only. Preserve declared sibling authority boundaries.",
            "",
            "## Contradictions requiring attention",
            "",
        ]
        if data["contradictions"]:
            for c in data["contradictions"]:
                lines.append(f"- {c['subject']} / {c['predicate']} @ {c['valid_from']}: {len(c['facts'])} conflicting values")
        else:
            lines.append("- None detected under the current strict same-valid-boundary rule.")
        lines += ["", "## State digest reproduction", "", "Import `handoff.json` into a fresh JANUS instance and require an equivalent authoritative-state digest after normalization."]
        md_path = out / "HANDOFF.md"
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return {"handoff_json": str(json_path), "handoff_md": str(md_path), "state_digest": data["state_digest"]}

    def _fact_row(self, r: sqlite3.Row) -> dict[str, Any]:
        return {
            "fact_id": r["fact_id"],
            "subject": r["subject"],
            "predicate": r["predicate"],
            "value": json.loads(r["value_json"]),
            "valid_from": r["valid_from"],
            "valid_to": r["valid_to"],
            "known_at": r["known_at"],
            "source": r["source"],
            "source_hash": r["source_hash"],
            "confidence": r["confidence"],
            "authority": r["authority"],
            "supersedes": r["supersedes"],
        }
