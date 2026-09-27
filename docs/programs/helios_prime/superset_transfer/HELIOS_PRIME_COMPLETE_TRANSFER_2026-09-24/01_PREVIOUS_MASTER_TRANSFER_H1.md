

====================================================================================================
README_FIRST.md
====================================================================================================

# HELIOS PRIME — FULL TRANSFER ARCHIVE
Generated: 2026-09-24
Status: DESIGN / AUDIT / IMPLEMENTATION-PACKET COMPLETE THROUGH H1 TASK 8
Repository mutations performed by this chat: NONE
Tests executed by this chat against a HELIOS repository: NONE

## READ THIS FIRST

This archive captures the durable work completed in the HELIOS PRIME design/audit loop.

It contains:
1. The user's original HELIOS PRIME source requirements.
2. The architectural rulings that were frozen after sibling-system inspection.
3. Repository audit findings for ICARUS, AION, DAEDALUS and the CSV Evidence Lab.
4. The H1 implementation plan.
5. Concrete implementation packets for H1 Tasks 1–8.
6. Remaining Tasks 9–12.
7. Execution/firewall/security requirements.
8. Exact TDD and verification instructions.
9. Known risks and unresolved integration blockers.
10. A continuation prompt for a repo-capable Codex/Work session.

IMPORTANT:
- The code in this archive is a DESIGN/IMPLEMENTATION PACKET. It has NOT been applied to a repo by this chat.
- No test result in this archive should be treated as a fresh passing test unless a future repo-capable session actually runs it.
- Do not merge/deploy automatically.
- Preserve the ownership boundaries in 02_ARCHITECTURE_AND_INVARIANTS.md.
- HELIOS must never gain broker/order authority.

Recommended next action:
Create a new sibling repo named `helios-prime`, use an isolated branch/worktree, then implement Tasks 1–12 with RED→GREEN TDD exactly as described here.


====================================================================================================
01_REPOSITORY_AUDIT.md
====================================================================================================

# REPOSITORY / ECOSYSTEM AUDIT FINDINGS

## Canonical ownership

NEXUS:
- Owns market-data infrastructure, identity, causal synchronization, native clocks, representation semantics, quality telemetry, cross-market topology, replay, stream health and derivation genealogy.

ARGUS:
- Owns microstructure truth, authenticated trades, depth/order-book, genuine order flow and related microstructure evidence.

AION:
- Owns durable historical memory, observations, event history, revisions, historical analogues, durable evidence, genealogy, event/availability semantics, replay history.

DAEDALUS:
- Owns scientific validation, falsification, statistical testing, walk-forward analysis, robustness, multiple-comparison correction, ablation, validation and promotion evidence.

ATHENA:
- Owns supervisory intelligence, uncertainty, reliability, operational confidence, risk, abstention, health, disagreement and supervisory routing.

ORACLE:
- Owns financial/research coordination, hypothesis lifecycle, research scheduling, financial-state projection, thesis lifecycle, research triggers, prioritization and evidence requirements.

HELIOS:
- Owns information acquisition, source discovery, source economics, knowledge-gap detection, adaptive interrogation, uncertainty-reduction planning, information-value estimation, evidence-independence analysis, source-substitution discovery, information-seeking policy and external knowledge discovery.

ICARUS:
- Remains final operational/execution authority.
- No research/acquisition/interrogation/discovery system may silently gain production trading authority.

## Repository state observed

Known repos under reppiks490:
- Icarus
- Icarus-engine
- multi-level-csv
- csv-data-multi-chart-type
- more-instructions-for-sol-and-astra-effort-swapping
- new
- icarus-owner-actions
- daedalus-research-os
- aion-parallax-research
- icarus-csv-evidence-lab

Known heads observed:
- Icarus: 007e70189945b8e112904cf92b2b1a12e43792d6
- daedalus-research-os: 74ad94149b02ddd3f69d535ee5fdc00c1fdbe096
- aion-parallax-research: 12a7cb8ef99e84ce50b766db0aea1592b3906f80
- icarus-csv-evidence-lab: d6a5868e3f3202ef82579aca40b83cb3f8a4b491

No matching HELIOS feature repo/branch/commit was found in connected scope.

## ICARUS findings

`reppiks490/Icarus` is the canonical active repo; `Icarus-engine` identifies itself as older/stub/wrong runtime.

Observed bridge path:
TradingView-style payload
→ `icarus_bridge/models.py: parse_alert`
→ `icarus_bridge/webhook.py: /webhook`
→ `ExecutionEngine.handle_alert`
→ market / stop / bracket broker actions.

Critical finding:
Unknown non-text event types are not explicitly rejected before fill dispatch. In the verified dispatch path:
- `text` is journaled.
- `stop_update` goes to stop handling.
- otherwise the event falls through into fill handling.

Record this as:

ICARUS-RISK-001
Severity: HIGH integration blocker
Finding: unknown non-text event types can enter fill dispatch.

HELIOS consequence:
- no HELIOS adapter may call the ICARUS webhook;
- no HELIOS adapter may call state-changing `/admin/*`;
- no `/admin/simulate`;
- no `/admin/flatten`;
- no import of `icarus_bridge.executor`;
- no broker adapter import;
- no use of ICARUS execution `Settings`;
- no ALPACA_API_KEY;
- no ALPACA_SECRET_KEY;
- no WEBHOOK_SECRET;
- no ADMIN_TOKEN;
- no order-shaped outbound fields such as action/contracts/order_id/position_size/market_position/prev_market_position/stop/secret.

Structural separation is mandatory; `execution_authorized=false` alone is not sufficient.

Additional observed ICARUS inconsistency:
- existing instructions say "No 0.0.0.0"
- current `icarus_bridge/config.py` defaults host to `0.0.0.0`
This is an existing ICARUS hardening discrepancy, not a HELIOS H1 implementation requirement.

## AION findings

Repo: `reppiks490/aion-parallax-research`

Observed:
- Python >=3.11
- zero runtime dependencies
- deterministic compact sorted JSON
- SHA-256 hashes
- integer nanosecond causal times
- append-only source-aware SQLite event ledger
- `BEGIN IMMEDIATE`
- explicit DB lifecycle
- source identity immutability
- revision monotonicity
- as-of visibility uses `available_ns`
- sequenced-source gap detection
- replay constrained by causal visibility
- synthetic evidence remains synthetic
- true depth degrades when stale
- predictions freeze ledger cutoffs
- `execution_authorized=false`
- `performance_eligible=false`

Important limitation:
AION `verify_chain()` covers sources/events but not all durable state families. `source_gap_history` is append-only but outside the event hash chain. Therefore do not call AION fully tamper-evident.

HELIOS ruling:
Adopt AION's strongest useful serialization/timing patterns, but do not duplicate AION memory ownership and do not reuse AION numeric evidence tiers as universal cross-system semantics.

## DAEDALUS findings

Repo: `reppiks490/daedalus-research-os`

Observed:
- Python >=3.11
- explicit SQLite connection lifecycle
- experiment registry
- stable SHA-256 of sorted JSON
- protected holdout ledger
- research-only bridge semantics
- `production_authorized=false`
- unmapped source identity becomes UNLABELED/research-only
- path traversal / outside-root rejection
- source byte hash and descriptive mechanics do not imply execution safety

Recorded repo checkpoint said 59/59 tests pass, but that was repository-recorded evidence, not a fresh test run from this chat.

HELIOS ruling:
- structural validity != semantic authority
- hash identity != market meaning
- source qualification must remain externally asserted.

## CSV Evidence Lab findings

Repo: `reppiks490/icarus-csv-evidence-lab`

Current main implements:
- `audit.py`
- `reconcile.py`
- `cli.py`
- associated tests/fixtures

Current behavior:
- structural CSV triage
- byte snapshot before parse
- SHA-256
- finite numeric parsing
- delimiter inference/fallback marked unverified
- mixed timestamp/duplicate/out-of-order detection
- structural OHLC/volume checks
- provenance remains unverified
- eligibility remains `quarantined_pending_source_verification`
- AION/NEXUS inventory reconciliation is descriptive and explicitly not authority/coverage proof.

Important:
The planned cross-system evidence contract is DESIGN/PLAN ONLY on current main.
The following planned modules were not present when checked:
- contracts.py
- provenance.py
- ledger.py
- reporting.py
- archive_inventory.py

Therefore HELIOS H1 must NOT runtime-depend on those planned APIs.

Future compatibility target from evidence-lab design:
per-observation knowledge time:
knowledge_ns = max(source_publish_ns, first_observed_ns, ingest_ns, parent_knowledge_ns...)
Do not synthesize knowledge time.

## Adapter readiness

AION: READY_FOR_CONTRACT_MAPPING
DAEDALUS: READY_FOR_CONTRACT_MAPPING
ICARUS: READY_FOR_FIREWALL_CONTRACTS
NEXUS: EVIDENCE_ONLY / SOURCE_REQUIRED
ORACLE: PARTIAL / SOURCE_REQUIRED
ATHENA: DESIGN_ONLY / SOURCE_REQUIRED
ARGUS: DESIGN_ONLY / SOURCE_REQUIRED
AEGIS: UNVERIFIED / SOURCE_REQUIRED

No placeholder adapter should impersonate an unavailable sibling.


====================================================================================================
02_ARCHITECTURE_AND_INVARIANTS.md
====================================================================================================

# HELIOS PRIME H1 — ARCHITECTURE AND FROZEN INVARIANTS

## H1 purpose

H1 is the foundation/contracts layer for HELIOS PRIME. It is not yet the Adaptive Interrogation Engine itself.

H1 domains:
- Contracts
- Sources
- Tasks
- Provenance
- Audit
- Persistence
- Recovery / integrity
- Integration readiness
- Execution firewall

## Repo shape

helios-prime/
  pyproject.toml
  src/helios/
    contracts/
    persistence/
    sources/
    provenance/
    tasks/
    services/
    recovery/
    audit/
  tests/
  docs/

## Runtime baseline

Python >=3.11
Core dependencies: standard library first
Persistence: SQLite reference implementation
Clock: integer UTC nanoseconds
Serialization: deterministic strict JSON, allow_nan=False
Writes: BEGIN IMMEDIATE where serialization matters
DB lifecycle: explicit commit / rollback / close
Source authority: external assertion based
Evidence admission: fail closed
Revision model: immutable version chain
Historical replay: knowledge-time constrained
Execution authority: impossible by HELIOS contract

## Hard invariants

1. Determinism
Same durable logical state must serialize/hash identically.

2. Causality
Future knowledge cannot enter past decisions.

3. Prefix invariance
Appending a future revision cannot change a historical snapshot.

4. Provenance
Every derived evidence item can trace to upstream evidence.

5. Evidence independence
Different IDs/vendors/models do not imply independent evidence.

6. Synthetic provenance
Synthetic upstream evidence remains synthetic downstream.

7. Source authority separation
HELIOS can record/use external source qualification assertions but cannot self-promote source identity/timing/research eligibility.

8. Execution authority separation
HELIOS cannot declare, import or obtain execution/broker authority.

9. Transport firewall
HELIOS cannot call money-moving ICARUS routes.

10. Credential firewall
HELIOS cannot consume broker/execution credentials.

11. Payload firewall
Order-shaped payloads cannot cross HELIOS advisory interfaces.

12. Transactional atomicity
Task state, idempotency, decisions and audit must not commit partially.

13. Restart equivalence
Committed durable state survives process restart exactly.

14. External side-effect uncertainty
A possibly-dispatched external mutation is never blindly repeated after an ambiguous crash.

15. Contract drift
Unsupported contract/schema major versions fail closed.

16. Anti-complexity
An advanced mechanism must beat a simpler baseline before inclusion.

## Causal time

Per-observation timing should preserve:
- event_ns
- source_publish_ns / published_ns
- first_observed_ns
- available/knowledge time
- ingest_ns
- revision timing
- decision_ns

Conceptual rule:
knowledge_ns = max(
    source_publish_ns,
    first_observed_ns,
    ingest_ns,
    parent_knowledge_ns...
)

If receipt/ingest timing is unknown, do not fabricate knowledge time.

Example:
v0: event=100, knowledge=110
v1: revision_of=v0, event=100, knowledge=150

At decision=120:
- v0 visible
- v1 invisible

Appending v1 later cannot alter historical state at 120.

## Source qualification

Separate:
- SourceReference: what source/artifact is this?
- SourceVersionReference: which immutable source version?
- QualificationAssertion: who asserts which qualification state?
- VerificationRecord: what check was actually performed?
- ObservationReference: which observation/revision?
- EvidenceReference: which durable evidence object?
- IntegrationReadiness: may HELIOS safely call/use a system now?

HELIOS must not itself grant:
- IDENTITY_VERIFIED
- POINT_IN_TIME_VERIFIED
- RESEARCH_ELIGIBLE

without an external assertion owned by the appropriate source/validation layer.

## Evidence independence

If:
Vendor A ← Exchange X
Vendor B ← Exchange X

then evidence from Vendor A and Vendor B shares root Exchange X and cannot be counted as two independent confirmations.

Likewise:
raw observation → factor → model → research summary
does not become four independent votes.

## Persistence architecture

Full event sourcing was considered and rejected for H1.

Use:
1. normalized canonical operational state;
2. immutable hash-linked audit history;
3. deterministic checkpoints.

Normalized tables remain the working authoritative state.

The audit chain is internal integrity evidence, not external attestation.

## Investigation terminal states

RESOLVED
PARTIALLY_RESOLVED
UNRESOLVED
UNKNOWN_NOVEL
ABSTAIN

## Durable task states

PENDING
CLAIMED
RUNNING
BLOCKED
RETRY
DONE
DEAD_LETTER

## Effect classes

INTERNAL
EXTERNAL_READ
EXTERNAL_SIDE_EFFECT

## Integration readiness states

Recommended:
VERIFIED_AVAILABLE
VERIFIED_DEGRADED
CONTRACT_ONLY
DESIGN_ONLY
SOURCE_REQUIRED
UNVERIFIED
INCOMPATIBLE

Suggested contract:
IntegrationReadiness
    system_id
    capability
    contract_version
    source_commit
    source_artifact_hash
    verification_state
    last_verified_ns
    availability_state
    failure_reason

## H1 → later stages

H1: contracts/persistence/provenance/recovery/firewalls
H2: belief graph / UNKNOWN_OR_NOVEL
H3: expected information gain / question planner
H4: acquisition / source economics
H5: sibling adapters
H6: meta-learning / ops / interface / production hardening

"Truth before intelligence."


====================================================================================================
03_H1_IMPLEMENTATION_PLAN.md
====================================================================================================

# H1 IMPLEMENTATION PLAN

Goal:
Produce an executable HELIOS foundation with versioned contracts, source identity, causal timing, evidence/provenance, durable investigations/tasks, atomic decision audit, deterministic restart recovery and zero trading authority.

Use TDD:
1. Write focused failing test.
2. Run and observe expected RED.
3. Implement minimum behavior.
4. Rerun focused test.
5. Run full regression.
6. Refactor only while green.
7. Verify with ResourceWarning strictness.
8. Commit one verified task.

Never implement directly on main/master.

## Tasks

Task 1 — Repo skeleton + canonical serialization
Task 2 — Versioned source registry + causal time
Task 3 — Evidence/provenance/dependency graph
Task 4 — Investigation + task state machine
Task 5 — SQLite persistence + explicit connection lifecycle
Task 6 — Decision trace + append-only hash-linked audit
Task 7 — Atomic investigation decision service
Task 8 — Checkpoint/restart recovery
Task 9 — Contract/execution firewall
Task 10 — Security admission
Task 11 — End-to-end synthetic NQ_STATE_ANOMALY fixture
Task 12 — Documentation/capability/security/unfinished matrix + final gate

## Verification commands

pytest -q
pytest -W error::ResourceWarning -q
python -m compileall -q src tests

SQLite connection audit:
grep -R "sqlite3.connect" -n src/helios --exclude="database.py"

Execution-authority symbol audit:
search runtime code for terms including:
submit_order
submit_market
submit_stop
submit_bracket
close_position
flatten
webhook_secret
alpaca_api_key
alpaca_secret_key
admin_token
execution_authorized
position_size
order_id
contracts

Manually classify documentation/negative-test matches.

Do not merge or deploy automatically.


====================================================================================================
04_TASKS_1_TO_8_CODE_AND_TEST_DRAFTS.md
====================================================================================================

# H1 TASKS 1–8 — CONCRETE CODE / TEST DRAFTS

IMPORTANT:
These drafts were produced in the design conversation and were NOT applied/tested in a HELIOS repository.
Treat them as the starting implementation packet. A repo-capable session must run RED→GREEN TDD and may make minimal corrections needed for coherence.

---

# TASK 1 — FOUNDATION / COMMON CONTRACTS

## pyproject.toml

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "helios-prime"
version = "0.1.0"
description = "HELIOS PRIME autonomous epistemic investigation fabric"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-q"
filterwarnings = ["error::ResourceWarning"]
```

## src/helios/__init__.py

```python
"""HELIOS PRIME.

Research/information-acquisition system only.
No broker or execution authority.
"""

__version__ = "0.1.0"
```

## src/helios/contracts/common.py

```python
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
import hashlib
import json
import math
import re
from typing import Any


_VERSION = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


class AuthorityViolation(ValueError):
    """Raised when a contract attempts to cross an authority boundary."""


class SystemId(str, Enum):
    HELIOS = "HELIOS"
    ICARUS = "ICARUS"
    NEXUS = "NEXUS"
    ARGUS = "ARGUS"
    AION = "AION"
    DAEDALUS = "DAEDALUS"
    ATHENA = "ATHENA"
    ORACLE = "ORACLE"
    AEGIS = "AEGIS"
    EVIDENCE_LAB = "EVIDENCE_LAB"


class AuthorityDomain(str, Enum):
    EXECUTION = "execution"
    MARKET_DATA = "market_data"
    MICROSTRUCTURE = "microstructure"
    MEMORY = "memory"
    VALIDATION = "validation"
    SUPERVISION = "supervision"
    COORDINATION = "coordination"
    INFORMATION_ACQUISITION = "information_acquisition"
    EVIDENCE_VERIFICATION = "evidence_verification"


@dataclass(frozen=True, order=True)
class ContractVersion:
    major: int
    minor: int

    def __post_init__(self) -> None:
        for field, value in (("major", self.major), ("minor", self.minor)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field} must be a nonnegative integer")

    @classmethod
    def parse(cls, value: str) -> "ContractVersion":
        if not isinstance(value, str):
            raise ValueError("contract version must be a string")
        match = _VERSION.fullmatch(value)
        if not match:
            raise ValueError("contract version must be MAJOR.MINOR")
        return cls(int(match.group(1)), int(match.group(2)))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"


@dataclass(frozen=True)
class SystemIdentity:
    system_id: SystemId
    authority_domains: tuple[AuthorityDomain, ...]
    contract_version: ContractVersion = ContractVersion(1, 0)

    def __post_init__(self) -> None:
        if not isinstance(self.system_id, SystemId):
            raise ValueError("system_id must be a known SystemId")
        if (
            not isinstance(self.authority_domains, tuple)
            or not self.authority_domains
            or any(not isinstance(domain, AuthorityDomain) for domain in self.authority_domains)
        ):
            raise ValueError("authority_domains must contain known domains")
        if len(self.authority_domains) != len(set(self.authority_domains)):
            raise ValueError("duplicate authority domain")
        if self.system_id is SystemId.HELIOS and AuthorityDomain.EXECUTION in self.authority_domains:
            raise AuthorityViolation("HELIOS cannot declare execution authority")


def require_ns(value: Any, field: str = "timestamp_ns") -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a nonnegative integer nanosecond timestamp")
    return value


def _normalize(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _normalize(asdict(value))
    if isinstance(value, Enum):
        return _normalize(value.value)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite float is not canonicalizable")
        return value
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("canonical object keys must be strings")
        return {key: _normalize(item) for key, item in value.items()}
    raise TypeError(f"unsupported canonical value type: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    normalized = _normalize(value)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
```

## Task 1 required tests

- mapping order independent canonical JSON/hash
- NaN/+Inf/-Inf rejected
- non-string mapping keys rejected
- bool rejected as timestamp
- nonnegative integer ns accepted
- contract version round-trip
- invalid version strings fail closed
- unknown SystemId fails
- unknown AuthorityDomain fails
- HELIOS cannot declare EXECUTION authority
- ICARUS may be described as execution authority
- dataclass canonicalization deterministic
- unsupported Python objects rejected

---

# TASK 2 — SOURCES / QUALIFICATION / CAUSAL REVISIONS

## src/helios/contracts/causal.py

```python
from __future__ import annotations
from dataclasses import dataclass
from .common import canonical_hash, require_ns


@dataclass(frozen=True)
class KnowledgeTime:
    event_ns: int
    source_publish_ns: int | None
    first_observed_ns: int | None
    ingest_ns: int | None
    parent_knowledge_ns: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        require_ns(self.event_ns, "event_ns")
        for field in ("source_publish_ns", "first_observed_ns", "ingest_ns"):
            value = getattr(self, field)
            if value is not None:
                require_ns(value, field)
        if not isinstance(self.parent_knowledge_ns, tuple):
            raise ValueError("parent_knowledge_ns must be a tuple")
        for value in self.parent_knowledge_ns:
            require_ns(value, "parent_knowledge_ns")
        if self.first_observed_ns is not None and self.ingest_ns is not None and self.first_observed_ns > self.ingest_ns:
            raise ValueError("first observation cannot follow ingestion")
        if self.source_publish_ns is not None and self.first_observed_ns is not None and self.source_publish_ns > self.first_observed_ns:
            raise ValueError("source publication cannot follow first observation")

    @property
    def knowledge_ns(self) -> int | None:
        if self.first_observed_ns is None or self.ingest_ns is None:
            return None
        values = [self.first_observed_ns, self.ingest_ns, *self.parent_knowledge_ns]
        if self.source_publish_ns is not None:
            values.append(self.source_publish_ns)
        return max(values)

    def visible_as_of(self, decision_ns: int) -> bool:
        require_ns(decision_ns, "decision_ns")
        knowledge = self.knowledge_ns
        return knowledge is not None and knowledge <= decision_ns


@dataclass(frozen=True)
class ObservationRevision:
    observation_id: str
    revision_id: str
    revision_of: str | None
    source_ref_id: str
    timing: KnowledgeTime
    payload_hash: str

    def __post_init__(self) -> None:
        for field in ("observation_id", "revision_id", "source_ref_id", "payload_hash"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{field} is required")
        if self.revision_of is not None and (not isinstance(self.revision_of, str) or not self.revision_of):
            raise ValueError("revision_of must be a nonempty string or None")
        if len(self.payload_hash) != 64 or any(c not in "0123456789abcdef" for c in self.payload_hash):
            raise ValueError("payload_hash must be lowercase SHA-256")

    @property
    def revision_hash(self) -> str:
        return canonical_hash(self)


def select_revision_as_of(revisions: list[ObservationRevision], decision_ns: int) -> ObservationRevision | None:
    require_ns(decision_ns, "decision_ns")
    if not revisions:
        return None
    identities = {(r.observation_id, r.source_ref_id) for r in revisions}
    if len(identities) != 1:
        raise ValueError("revision set contains multiple observations or sources")
    revision_ids = [r.revision_id for r in revisions]
    if len(revision_ids) != len(set(revision_ids)):
        raise ValueError("duplicate revision_id")
    eligible = []
    for revision in revisions:
        knowledge = revision.timing.knowledge_ns
        if knowledge is not None and knowledge <= decision_ns:
            eligible.append((knowledge, revision))
    if not eligible:
        return None
    newest = max(t for t, _ in eligible)
    candidates = [r for t, r in eligible if t == newest]
    if len(candidates) != 1:
        return None
    return candidates[0]
```

## src/helios/contracts/source.py

```python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import re
from .common import AuthorityViolation, ContractVersion, SystemId, canonical_hash, require_ns

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class SourceCapability(str, Enum):
    BAR = "bar"
    SCHEDULE = "schedule"
    MACRO = "macro"
    TRADE = "trade"
    BOOK_SNAPSHOT = "book_snapshot"
    BOOK_DELTA = "book_delta"
    CONTEXT = "context"
    RESEARCH_ARTIFACT = "research_artifact"
    SYSTEM_HEALTH = "system_health"


class RightsStatus(str, Enum):
    UNKNOWN = "unknown"
    INTERNAL_ONLY = "internal_only"
    PRIVATE_RESEARCH = "private_research"
    REDISTRIBUTABLE = "redistributable"
    RESTRICTED = "restricted"


@dataclass(frozen=True)
class SourceRights:
    status: RightsStatus = RightsStatus.UNKNOWN
    license_reference: str | None = None
    redistribution_allowed: bool | None = None
    automated_access_allowed: bool | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, RightsStatus):
            raise ValueError("unknown rights status")
        if self.license_reference is not None and (
            not isinstance(self.license_reference, str) or not self.license_reference.strip()
        ):
            raise ValueError("license_reference must be nonempty or None")
        for field in ("redistribution_allowed", "automated_access_allowed"):
            value = getattr(self, field)
            if value is not None and type(value) is not bool:
                raise ValueError(f"{field} must be bool or None")
        if self.status is RightsStatus.UNKNOWN and (
            self.redistribution_allowed is not None or self.automated_access_allowed is not None
        ):
            raise ValueError("unknown rights cannot imply permissions")


@dataclass(frozen=True)
class SourceReference:
    source_id: str
    owner_system: SystemId
    representation_id: str
    source_version: str
    capabilities: tuple[SourceCapability, ...]
    rights: SourceRights = SourceRights()
    content_sha256: str | None = None
    contract_version: ContractVersion = ContractVersion(1, 0)

    def __post_init__(self) -> None:
        for field in ("source_id", "representation_id", "source_version"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip() or len(value) > 160:
                raise ValueError(f"invalid {field}")
        if not isinstance(self.owner_system, SystemId):
            raise ValueError("owner_system must be a known SystemId")
        if not isinstance(self.capabilities, tuple) or not self.capabilities:
            raise ValueError("at least one source capability is required")
        if any(not isinstance(item, SourceCapability) for item in self.capabilities):
            raise ValueError("unknown source capability")
        object.__setattr__(self, "capabilities", tuple(sorted(set(self.capabilities), key=lambda x: x.value)))
        if self.content_sha256 is not None and not _SHA256.fullmatch(self.content_sha256):
            raise ValueError("content_sha256 must be lowercase SHA-256")

    @property
    def source_ref_id(self) -> str:
        return canonical_hash(self)


class QualificationState(str, Enum):
    QUARANTINED = "quarantined"
    STRUCTURALLY_CHECKED = "structurally_checked"
    IDENTITY_VERIFIED = "identity_verified"
    POINT_IN_TIME_VERIFIED = "point_in_time_verified"
    RESEARCH_ELIGIBLE = "research_eligible"


class AssertionStatus(str, Enum):
    ASSERTED = "asserted"
    VERIFIED = "verified"
    REVOKED = "revoked"


_SELF_PROMOTION_FORBIDDEN = {
    QualificationState.IDENTITY_VERIFIED,
    QualificationState.POINT_IN_TIME_VERIFIED,
    QualificationState.RESEARCH_ELIGIBLE,
}


@dataclass(frozen=True)
class QualificationAssertion:
    source_ref_id: str
    asserted_state: QualificationState
    asserting_system: SystemId
    evidence_refs: tuple[str, ...]
    observed_ns: int
    status: AssertionStatus = AssertionStatus.ASSERTED
    expires_ns: int | None = None
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.source_ref_id, str) or not _SHA256.fullmatch(self.source_ref_id):
            raise ValueError("invalid source_ref_id")
        if not isinstance(self.asserted_state, QualificationState):
            raise ValueError("unknown qualification state")
        if not isinstance(self.asserting_system, SystemId):
            raise ValueError("unknown asserting system")
        if not isinstance(self.status, AssertionStatus):
            raise ValueError("unknown assertion status")
        require_ns(self.observed_ns, "observed_ns")
        if self.expires_ns is not None:
            require_ns(self.expires_ns, "expires_ns")
            if self.expires_ns <= self.observed_ns:
                raise ValueError("expires_ns must follow observed_ns")
        if not isinstance(self.evidence_refs, tuple):
            raise ValueError("evidence_refs must be a tuple")
        if any(not isinstance(ref, str) or not _SHA256.fullmatch(ref) for ref in self.evidence_refs):
            raise ValueError("evidence references must be lowercase SHA-256 IDs")
        object.__setattr__(self, "evidence_refs", tuple(sorted(set(self.evidence_refs))))
        if not isinstance(self.reason_codes, tuple):
            raise ValueError("reason_codes must be a tuple")
        if any(not isinstance(code, str) or not code or len(code) > 80 for code in self.reason_codes):
            raise ValueError("invalid reason code")
        object.__setattr__(self, "reason_codes", tuple(sorted(set(self.reason_codes))))
        if self.asserted_state is not QualificationState.QUARANTINED and not self.evidence_refs:
            raise ValueError("qualification requires supporting evidence")
        if self.asserting_system is SystemId.HELIOS and self.asserted_state in _SELF_PROMOTION_FORBIDDEN:
            raise AuthorityViolation("HELIOS cannot self-promote source qualification")

    @property
    def assertion_id(self) -> str:
        return canonical_hash(self)

    def active_as_of(self, at_ns: int) -> bool:
        require_ns(at_ns, "at_ns")
        if self.status is AssertionStatus.REVOKED:
            return False
        if self.observed_ns > at_ns:
            return False
        if self.expires_ns is not None and at_ns >= self.expires_ns:
            return False
        return True
```

Task 2 required tests:
- deterministic source identity across capability order
- unknown rights imply no permissions
- invalid content digest rejected
- verified qualification requires evidence
- HELIOS cannot self-promote source
- external systems can assert qualification
- future/expired/revoked assertions inactive
- future revision invisible to past decision
- future revision does not change past snapshot
- equal knowledge-time revision ambiguous/fail closed
- derived timing inherits latest parent time

---

# TASK 3 — EVIDENCE PROVENANCE / DEPENDENCY DAG

## src/helios/contracts/evidence.py

```python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import re
from .causal import KnowledgeTime
from .common import ContractVersion, canonical_hash

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _require_hash(value: str, field: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be lowercase SHA-256")
    return value


class EvidenceKind(str, Enum):
    SOURCE_OBSERVATION = "source_observation"
    DERIVED = "derived"


@dataclass(frozen=True)
class EvidenceRecord:
    kind: EvidenceKind
    timing: KnowledgeTime
    payload_hash: str
    synthetic: bool
    source_ref_id: str | None = None
    observation_revision_hash: str | None = None
    parent_evidence_refs: tuple[str, ...] = ()
    quality_flags: tuple[str, ...] = ()
    contract_version: ContractVersion = ContractVersion(1, 0)

    def __post_init__(self) -> None:
        if not isinstance(self.kind, EvidenceKind):
            raise ValueError("unknown evidence kind")
        _require_hash(self.payload_hash, "payload_hash")
        if type(self.synthetic) is not bool:
            raise ValueError("synthetic must be bool")
        if not isinstance(self.parent_evidence_refs, tuple):
            raise ValueError("parent_evidence_refs must be a tuple")
        for ref in self.parent_evidence_refs:
            _require_hash(ref, "parent_evidence_ref")
        object.__setattr__(self, "parent_evidence_refs", tuple(sorted(set(self.parent_evidence_refs))))
        if not isinstance(self.quality_flags, tuple):
            raise ValueError("quality_flags must be a tuple")
        for flag in self.quality_flags:
            if not isinstance(flag, str) or not flag or len(flag) > 80:
                raise ValueError("invalid quality flag")
        object.__setattr__(self, "quality_flags", tuple(sorted(set(self.quality_flags))))

        if self.kind is EvidenceKind.SOURCE_OBSERVATION:
            if self.source_ref_id is None:
                raise ValueError("source observation requires source_ref_id")
            if self.observation_revision_hash is None:
                raise ValueError("source observation requires observation revision")
            _require_hash(self.source_ref_id, "source_ref_id")
            _require_hash(self.observation_revision_hash, "observation_revision_hash")
            if self.parent_evidence_refs:
                raise ValueError("source observation cannot declare evidence parents")
        elif self.kind is EvidenceKind.DERIVED:
            if not self.parent_evidence_refs:
                raise ValueError("derived evidence requires explicit parents")
            if self.source_ref_id is not None or self.observation_revision_hash is not None:
                raise ValueError("derived evidence must reference parents rather than masquerade as a source observation")

    @property
    def evidence_id(self) -> str:
        return canonical_hash(self)
```

## src/helios/provenance/graph.py

```python
from __future__ import annotations
from dataclasses import dataclass
from helios.contracts.common import require_ns
from helios.contracts.evidence import EvidenceKind, EvidenceRecord


@dataclass(frozen=True)
class IndependenceResult:
    independent: bool
    left_roots: tuple[str, ...]
    right_roots: tuple[str, ...]
    shared_roots: tuple[str, ...]
    shared_evidence: tuple[str, ...]


class SourceDependencyGraph:
    def __init__(self) -> None:
        self._parents: dict[str, tuple[str, ...]] = {}

    def register(self, source_ref_id: str, *, upstream_source_refs: tuple[str, ...] = ()) -> None:
        if not isinstance(source_ref_id, str) or not source_ref_id:
            raise ValueError("source_ref_id required")
        normalized = tuple(sorted(set(upstream_source_refs)))
        if source_ref_id in self._parents:
            if self._parents[source_ref_id] != normalized:
                raise ValueError("source dependency identity is immutable")
            return
        if not isinstance(upstream_source_refs, tuple):
            raise ValueError("upstream_source_refs must be a tuple")
        if source_ref_id in normalized:
            raise ValueError("source cannot depend on itself")
        missing = [ref for ref in normalized if ref not in self._parents]
        if missing:
            raise ValueError(f"unknown upstream sources: {missing}")
        self._parents[source_ref_id] = normalized

    def contains(self, source_ref_id: str) -> bool:
        return source_ref_id in self._parents

    def ultimate_roots(self, source_ref_id: str) -> tuple[str, ...]:
        if source_ref_id not in self._parents:
            raise ValueError(f"unknown source dependency node: {source_ref_id}")
        seen: set[str] = set()
        def visit(node: str) -> set[str]:
            if node in seen:
                raise ValueError("source dependency cycle detected")
            parents = self._parents[node]
            if not parents:
                return {node}
            seen.add(node)
            roots: set[str] = set()
            for parent in parents:
                roots.update(visit(parent))
            seen.remove(node)
            return roots
        return tuple(sorted(visit(source_ref_id)))


class EvidenceGraph:
    def __init__(self, *, source_dependencies: SourceDependencyGraph | None = None) -> None:
        self._records: dict[str, EvidenceRecord] = {}
        self._source_dependencies = source_dependencies or SourceDependencyGraph()

    def add(self, record: EvidenceRecord) -> str:
        evidence_id = record.evidence_id
        existing = self._records.get(evidence_id)
        if existing is not None:
            if existing != record:
                raise ValueError("evidence hash collision or conflicting immutable record")
            return evidence_id
        missing = [p for p in record.parent_evidence_refs if p not in self._records]
        if missing:
            raise ValueError(f"unknown parent evidence: {missing}")
        if record.kind is EvidenceKind.SOURCE_OBSERVATION:
            if not self._source_dependencies.contains(record.source_ref_id):
                raise ValueError("source observation requires registered source dependency identity")
        if record.kind is EvidenceKind.DERIVED:
            parents = [self._records[p] for p in record.parent_evidence_refs]
            if any(parent.synthetic for parent in parents) and not record.synthetic:
                raise ValueError("derived evidence cannot erase synthetic provenance")
            child_knowledge = record.timing.knowledge_ns
            if child_knowledge is not None:
                for parent in parents:
                    parent_knowledge = parent.timing.knowledge_ns
                    if parent_knowledge is not None and child_knowledge < parent_knowledge:
                        raise ValueError("derived evidence cannot become known before its parent evidence")
        self._records[evidence_id] = record
        return evidence_id

    def get(self, evidence_id: str) -> EvidenceRecord:
        try:
            return self._records[evidence_id]
        except KeyError as exc:
            raise ValueError(f"unknown evidence: {evidence_id}") from exc

    def upstream_evidence(self, evidence_id: str) -> tuple[str, ...]:
        self.get(evidence_id)
        visited: set[str] = set()
        def walk(node_id: str) -> None:
            node = self._records[node_id]
            for parent in node.parent_evidence_refs:
                if parent not in visited:
                    visited.add(parent)
                    walk(parent)
        walk(evidence_id)
        return tuple(sorted(visited))

    def root_evidence(self, evidence_id: str) -> tuple[str, ...]:
        self.get(evidence_id)
        roots: set[str] = set()
        def walk(node_id: str) -> None:
            node = self._records[node_id]
            if not node.parent_evidence_refs:
                roots.add(node_id)
                return
            for parent in node.parent_evidence_refs:
                walk(parent)
        walk(evidence_id)
        return tuple(sorted(roots))

    def source_roots(self, evidence_id: str) -> tuple[str, ...]:
        source_roots: set[str] = set()
        for root_id in self.root_evidence(evidence_id):
            record = self._records[root_id]
            if record.source_ref_id is None:
                raise ValueError("root evidence has no source identity")
            source_roots.update(self._source_dependencies.ultimate_roots(record.source_ref_id))
        return tuple(sorted(source_roots))

    def visible_as_of(self, evidence_id: str, decision_ns: int) -> bool:
        require_ns(decision_ns, "decision_ns")
        visited: set[str] = set()
        def visible(node_id: str) -> bool:
            if node_id in visited:
                return True
            visited.add(node_id)
            node = self.get(node_id)
            if not node.timing.visible_as_of(decision_ns):
                return False
            return all(visible(parent) for parent in node.parent_evidence_refs)
        return visible(evidence_id)

    def independence(self, left_id: str, right_id: str) -> IndependenceResult:
        left_roots = set(self.source_roots(left_id))
        right_roots = set(self.source_roots(right_id))
        left_upstream = set(self.upstream_evidence(left_id)) | {left_id}
        right_upstream = set(self.upstream_evidence(right_id)) | {right_id}
        shared_roots = left_roots & right_roots
        shared_evidence = left_upstream & right_upstream
        return IndependenceResult(
            independent=not shared_roots and not shared_evidence,
            left_roots=tuple(sorted(left_roots)),
            right_roots=tuple(sorted(right_roots)),
            shared_roots=tuple(sorted(shared_roots)),
            shared_evidence=tuple(sorted(shared_evidence)),
        )
```

Required tests:
- source observation requires source/revision identity
- derived evidence requires parents
- derived evidence cannot masquerade as source
- parent ordering does not change identity
- unknown parent rejected
- source must exist in source dependency graph
- child cannot be known before parent
- synthetic provenance cannot be erased
- recursive visibility
- same source not independent
- distinct root sources may be independent
- shared derived parent not independent
- different vendor IDs sharing one root not independent
- source dependency identity immutable
- upstream/root lineage queryable

---

# TASK 4 — INVESTIGATION + TASK STATE MACHINE

## src/helios/contracts/investigation.py

```python
from __future__ import annotations
from dataclasses import dataclass, replace
from enum import Enum
import re
from .common import ContractVersion, canonical_hash, require_ns

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class InvestigationState(str, Enum):
    OPEN = "open"
    ACTIVE = "active"
    BLOCKED = "blocked"
    RESOLVED = "resolved"
    PARTIALLY_RESOLVED = "partially_resolved"
    UNRESOLVED = "unresolved"
    UNKNOWN_NOVEL = "unknown_novel"
    ABSTAIN = "abstain"


TERMINAL_INVESTIGATION_STATES = frozenset({
    InvestigationState.RESOLVED,
    InvestigationState.PARTIALLY_RESOLVED,
    InvestigationState.UNRESOLVED,
    InvestigationState.UNKNOWN_NOVEL,
    InvestigationState.ABSTAIN,
})

_ALLOWED = {
    InvestigationState.OPEN: {InvestigationState.ACTIVE, InvestigationState.BLOCKED, *TERMINAL_INVESTIGATION_STATES},
    InvestigationState.ACTIVE: {InvestigationState.BLOCKED, *TERMINAL_INVESTIGATION_STATES},
    InvestigationState.BLOCKED: {InvestigationState.ACTIVE, *TERMINAL_INVESTIGATION_STATES},
}


@dataclass(frozen=True)
class Investigation:
    investigation_id: str
    phenomenon: str
    created_ns: int
    updated_ns: int
    state: InvestigationState = InvestigationState.OPEN
    evidence_refs: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    contract_version: ContractVersion = ContractVersion(1, 0)

    def __post_init__(self) -> None:
        if not isinstance(self.investigation_id, str) or not self.investigation_id.strip() or len(self.investigation_id) > 160:
            raise ValueError("invalid investigation_id")
        if not isinstance(self.phenomenon, str) or not self.phenomenon.strip() or len(self.phenomenon) > 4096:
            raise ValueError("invalid phenomenon")
        require_ns(self.created_ns, "created_ns")
        require_ns(self.updated_ns, "updated_ns")
        if self.updated_ns < self.created_ns:
            raise ValueError("updated_ns cannot precede created_ns")
        if not isinstance(self.state, InvestigationState):
            raise ValueError("unknown investigation state")
        for ref in self.evidence_refs:
            if not isinstance(ref, str) or not _SHA256.fullmatch(ref):
                raise ValueError("invalid evidence reference")
        object.__setattr__(self, "evidence_refs", tuple(sorted(set(self.evidence_refs))))
        for code in self.reason_codes:
            if not isinstance(code, str) or not code or len(code) > 80:
                raise ValueError("invalid reason code")
        object.__setattr__(self, "reason_codes", tuple(sorted(set(self.reason_codes))))

    @property
    def terminal(self) -> bool:
        return self.state in TERMINAL_INVESTIGATION_STATES

    @property
    def investigation_hash(self) -> str:
        return canonical_hash(self)


def advance_investigation(investigation: Investigation, target: InvestigationState, *, at_ns: int,
                          reason_codes: tuple[str, ...] = (), evidence_refs: tuple[str, ...] = ()) -> Investigation:
    require_ns(at_ns, "at_ns")
    if not isinstance(target, InvestigationState):
        raise ValueError("unknown target investigation state")
    if investigation.terminal:
        raise ValueError("terminal investigation cannot be reopened")
    if target not in _ALLOWED[investigation.state]:
        raise ValueError(f"invalid investigation transition: {investigation.state.value}->{target.value}")
    if at_ns < investigation.updated_ns:
        raise ValueError("investigation time cannot move backward")
    merged_reasons = tuple(sorted(set(investigation.reason_codes) | set(reason_codes)))
    merged_evidence = tuple(sorted(set(investigation.evidence_refs) | set(evidence_refs)))
    if target in TERMINAL_INVESTIGATION_STATES and not merged_reasons:
        raise ValueError("terminal investigation requires reason codes")
    if target in {InvestigationState.RESOLVED, InvestigationState.PARTIALLY_RESOLVED} and not merged_evidence:
        raise ValueError("resolved investigation requires supporting evidence")
    return replace(investigation, state=target, updated_ns=at_ns,
                   reason_codes=merged_reasons, evidence_refs=merged_evidence)
```

## src/helios/contracts/task.py

```python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import re
from .common import ContractVersion, canonical_hash, require_ns

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TASK_TYPE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")


class TaskState(str, Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    RUNNING = "running"
    BLOCKED = "blocked"
    RETRY = "retry"
    DONE = "done"
    DEAD_LETTER = "dead_letter"


TERMINAL_TASK_STATES = frozenset({TaskState.DONE, TaskState.DEAD_LETTER})


class EffectClass(str, Enum):
    INTERNAL = "internal"
    EXTERNAL_READ = "external_read"
    EXTERNAL_SIDE_EFFECT = "external_side_effect"


@dataclass(frozen=True)
class TaskBudget:
    max_attempts: int = 3
    deadline_ns: int | None = None

    def __post_init__(self) -> None:
        if isinstance(self.max_attempts, bool) or not isinstance(self.max_attempts, int) or self.max_attempts < 1:
            raise ValueError("max_attempts must be positive integer")
        if self.deadline_ns is not None:
            require_ns(self.deadline_ns, "deadline_ns")


@dataclass(frozen=True)
class InvestigationTask:
    task_id: str
    investigation_id: str
    task_type: str
    state: TaskState
    created_ns: int
    updated_ns: int
    budget: TaskBudget = TaskBudget()
    effect_class: EffectClass = EffectClass.INTERNAL
    dependency_task_ids: tuple[str, ...] = ()
    attempt: int = 0
    claimed_by: str | None = None
    result_ref: str | None = None
    reason_code: str | None = None
    contract_version: ContractVersion = ContractVersion(1, 0)

    def __post_init__(self) -> None:
        for field in ("task_id", "investigation_id"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip() or len(value) > 160:
                raise ValueError(f"invalid {field}")
        if not isinstance(self.task_type, str) or not _TASK_TYPE.fullmatch(self.task_type):
            raise ValueError("invalid task_type")
        if not isinstance(self.state, TaskState):
            raise ValueError("unknown task state")
        if not isinstance(self.effect_class, EffectClass):
            raise ValueError("unknown effect class")
        require_ns(self.created_ns, "created_ns")
        require_ns(self.updated_ns, "updated_ns")
        if self.updated_ns < self.created_ns:
            raise ValueError("task updated_ns precedes created_ns")
        if isinstance(self.attempt, bool) or not isinstance(self.attempt, int) or self.attempt < 0:
            raise ValueError("attempt must be nonnegative integer")
        if self.attempt > self.budget.max_attempts:
            raise ValueError("attempt exceeds task budget")
        if not isinstance(self.dependency_task_ids, tuple):
            raise ValueError("dependency_task_ids must be tuple")
        if self.task_id in self.dependency_task_ids:
            raise ValueError("task cannot depend on itself")
        if any(not isinstance(dep, str) or not dep for dep in self.dependency_task_ids):
            raise ValueError("invalid dependency task id")
        object.__setattr__(self, "dependency_task_ids", tuple(sorted(set(self.dependency_task_ids))))
        if self.claimed_by is not None and (not isinstance(self.claimed_by, str) or not self.claimed_by.strip()):
            raise ValueError("invalid claimed_by")
        if self.result_ref is not None and not _SHA256.fullmatch(self.result_ref):
            raise ValueError("result_ref must be lowercase SHA-256")
        if self.reason_code is not None and (not isinstance(self.reason_code, str) or not self.reason_code or len(self.reason_code) > 80):
            raise ValueError("invalid reason_code")

    @property
    def terminal(self) -> bool:
        return self.state in TERMINAL_TASK_STATES

    @property
    def task_hash(self) -> str:
        return canonical_hash(self)
```

## src/helios/tasks/state_machine.py

```python
from __future__ import annotations
from dataclasses import dataclass, replace
from helios.contracts.common import canonical_hash, require_ns
from helios.contracts.task import InvestigationTask, TaskState


class InvalidTransition(ValueError): pass
class IdempotencyConflict(ValueError): pass


_ALLOWED = {
    TaskState.PENDING: {TaskState.CLAIMED, TaskState.BLOCKED, TaskState.DEAD_LETTER},
    TaskState.CLAIMED: {TaskState.RUNNING, TaskState.BLOCKED, TaskState.RETRY, TaskState.DEAD_LETTER},
    TaskState.RUNNING: {TaskState.DONE, TaskState.BLOCKED, TaskState.RETRY, TaskState.DEAD_LETTER},
    TaskState.BLOCKED: {TaskState.RETRY, TaskState.DEAD_LETTER},
    TaskState.RETRY: {TaskState.CLAIMED, TaskState.DEAD_LETTER},
}


@dataclass(frozen=True)
class TransitionCommand:
    idempotency_key: str
    target_state: TaskState
    at_ns: int
    worker_id: str | None = None
    reason_code: str | None = None
    result_ref: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.idempotency_key, str) or not self.idempotency_key.strip() or len(self.idempotency_key) > 200:
            raise ValueError("invalid idempotency key")
        if not isinstance(self.target_state, TaskState):
            raise ValueError("unknown target task state")
        require_ns(self.at_ns, "at_ns")
        if self.worker_id is not None and (not isinstance(self.worker_id, str) or not self.worker_id):
            raise ValueError("invalid worker_id")
        if self.reason_code is not None and (not isinstance(self.reason_code, str) or not self.reason_code or len(self.reason_code) > 80):
            raise ValueError("invalid reason_code")

    @property
    def command_hash(self) -> str:
        return canonical_hash(self)


@dataclass(frozen=True)
class TransitionResult:
    task: InvestigationTask
    transition_id: str
    changed: bool
    idempotent: bool


@dataclass(frozen=True)
class _Applied:
    command_hash: str
    task: InvestigationTask
    transition_id: str


class TaskStateMachine:
    def __init__(self) -> None:
        self._applied: dict[str, _Applied] = {}

    def apply(self, task: InvestigationTask, command: TransitionCommand,
              *, completed_dependency_ids: frozenset[str] = frozenset()) -> TransitionResult:
        prior = self._applied.get(command.idempotency_key)
        if prior is not None:
            if prior.command_hash != command.command_hash:
                raise IdempotencyConflict("idempotency key reused with different command")
            return TransitionResult(prior.task, prior.transition_id, False, True)

        if task.terminal:
            raise InvalidTransition("terminal task cannot transition")
        if command.at_ns < task.updated_ns:
            raise InvalidTransition("task time cannot move backward")
        if task.budget.deadline_ns is not None and command.at_ns > task.budget.deadline_ns and command.target_state is not TaskState.DEAD_LETTER:
            raise InvalidTransition("task deadline exceeded")

        allowed = _ALLOWED.get(task.state, set())
        if command.target_state not in allowed:
            raise InvalidTransition(f"invalid task transition: {task.state.value}->{command.target_state.value}")

        target = command.target_state

        if target is TaskState.CLAIMED:
            missing = set(task.dependency_task_ids) - set(completed_dependency_ids)
            if missing:
                raise InvalidTransition(f"task dependencies incomplete: {sorted(missing)}")
            if not command.worker_id:
                raise InvalidTransition("claim requires worker_id")

        if task.state in {TaskState.CLAIMED, TaskState.RUNNING}:
            if task.claimed_by is not None and command.worker_id != task.claimed_by:
                raise InvalidTransition("transition worker does not own claim")

        if target in {TaskState.BLOCKED, TaskState.RETRY, TaskState.DEAD_LETTER} and not command.reason_code:
            raise InvalidTransition(f"{target.value} requires reason_code")

        if target is TaskState.DONE and command.result_ref is None:
            raise InvalidTransition("completed task requires result_ref")

        attempt = task.attempt
        if target is TaskState.CLAIMED:
            attempt += 1
            if attempt > task.budget.max_attempts:
                raise InvalidTransition("claim exceeds maximum attempts")

        if target is TaskState.RETRY and attempt >= task.budget.max_attempts:
            target = TaskState.DEAD_LETTER

        claimed_by = task.claimed_by
        if target is TaskState.CLAIMED:
            claimed_by = command.worker_id
        elif target in {TaskState.BLOCKED, TaskState.RETRY, TaskState.DONE, TaskState.DEAD_LETTER}:
            claimed_by = None

        result_ref = command.result_ref if target is TaskState.DONE else None

        updated = replace(
            task, state=target, updated_ns=command.at_ns, attempt=attempt,
            claimed_by=claimed_by, result_ref=result_ref, reason_code=command.reason_code,
        )

        transition_id = canonical_hash({
            "task_id": task.task_id,
            "from_state": task.state.value,
            "to_state": updated.state.value,
            "command_hash": command.command_hash,
            "prior_task_hash": task.task_hash,
            "resulting_task_hash": updated.task_hash,
        })

        self._applied[command.idempotency_key] = _Applied(command.command_hash, updated, transition_id)
        return TransitionResult(updated, transition_id, True, False)
```

Task 4 required tests:
- PENDING→CLAIMED→RUNNING→DONE
- claim requires worker
- dependencies required
- wrong worker cannot mutate claim
- duplicate command exact one effect
- idempotency key conflict rejected
- retry bounded
- final retry becomes DEAD_LETTER
- retry can be reclaimed if budget remains
- terminal cannot restart
- BLOCKED requires reason
- time cannot move backwards
- UNKNOWN_NOVEL valid terminal result
- ABSTAIN valid terminal result
- resolved requires evidence + reason

---

# TASK 5 — SQLITE PERSISTENCE

## Core schema v1

```sql
CREATE TABLE IF NOT EXISTS investigations (
    investigation_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    updated_ns INTEGER NOT NULL,
    body TEXT NOT NULL,
    body_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    investigation_id TEXT NOT NULL REFERENCES investigations(investigation_id),
    state TEXT NOT NULL,
    updated_ns INTEGER NOT NULL,
    body TEXT NOT NULL,
    body_hash TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_investigation
ON tasks(investigation_id, state);

CREATE TABLE IF NOT EXISTS task_idempotency (
    idempotency_key TEXT PRIMARY KEY,
    command_hash TEXT NOT NULL,
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    transition_id TEXT NOT NULL,
    result_task_body TEXT NOT NULL,
    result_task_hash TEXT NOT NULL,
    applied_ns INTEGER NOT NULL
);

CREATE TRIGGER IF NOT EXISTS task_idempotency_no_update
BEFORE UPDATE ON task_idempotency
BEGIN
    SELECT RAISE(ABORT, 'immutable idempotency record');
END;

CREATE TRIGGER IF NOT EXISTS task_idempotency_no_delete
BEFORE DELETE ON task_idempotency
BEGIN
    SELECT RAISE(ABORT, 'immutable idempotency record');
END;
```

## database lifecycle

```python
from contextlib import contextmanager
from pathlib import Path
import sqlite3

@contextmanager
def connection(path):
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path, timeout=30, isolation_level=None)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA busy_timeout=30000")
        con.execute("PRAGMA journal_mode=WAL")
        migrate(con)
        yield con
    finally:
        con.close()

@contextmanager
def immediate_transaction(path):
    with connection(path) as con:
        con.execute("BEGIN IMMEDIATE")
        try:
            yield con
        except BaseException:
            con.rollback()
            raise
        else:
            con.commit()
```

## persistence codec

Implement canonical encode/decode for Investigation and InvestigationTask.
Enum/string conversion must be explicit.
Contract version must round-trip.

## TaskStore requirements

- create_investigation
- investigation
- create_task
- task
- apply_transition
- durable idempotency checked BEFORE current task state
- durable dependency completion check
- compare-and-swap body_hash on task update
- idempotency row written in same transaction
- restart returns same committed task and transition result

Required tests:
- schema initialized
- connection actually closed
- rollback on exception
- FK enabled
- task survives reopen
- idempotency survives restart
- same key/new command rejected after restart
- failure after UPDATE rolls everything back
- orphan task rejected
- dependency must be durably DONE
- immutable idempotency rows
- ResourceWarning strict test suite

---

# TASK 6 — DECISION TRACE + HASH-LINKED AUDIT

## DecisionAlternative fields

alternative_id
action_type
target_system
expected_information_value
evidence_reliability
independence_score
expected_cost
expected_latency_ns
risk_score
redundancy_score
feasible
infeasibility_reason

Keep these dimensions separate. Do not hide everything in one score.

## DecisionTrace fields

investigation_id
decision_ns
input_state_hash
alternatives
outcome
selected_alternative_id
reason_codes
evidence_refs
resulting_state_hash
realized_information_gain

DecisionOutcome:
SELECTED
ABSTAIN
BLOCKED
DEFERRED

Rules:
- selected alternative must exist
- selected alternative must be feasible
- non-selected outcome cannot carry selected_alternative_id
- reason codes required
- alternative ordering canonicalized

## Audit events

INVESTIGATION_CREATED
INVESTIGATION_STATE_CHANGED
TASK_CREATED
TASK_STATE_CHANGED
SOURCE_REFERENCE_REGISTERED
QUALIFICATION_ASSERTED
QUALIFICATION_REVOKED
EVIDENCE_REGISTERED
EVIDENCE_DEPENDENCY_ADDED
DECISION_RECORDED
DECISION_SUPERSEDED
INTEGRATION_READINESS_CHANGED
CHECKPOINT_CREATED
RECOVERY_CLASSIFIED

## AuditRecord

transaction_id
event_type
entity_type
entity_id
recorded_ns
payload_hash
resulting_entity_hash
previous_hash
prior_entity_hash
decision_ns
knowledge_ns
evidence_refs
reason_codes

audit_hash = canonical_hash(AuditRecord)

Use ZERO_HASH = "0"*64 for genesis.

## Schema v2 additions

```sql
CREATE TABLE IF NOT EXISTS decisions (
    decision_id TEXT PRIMARY KEY,
    investigation_id TEXT NOT NULL REFERENCES investigations(investigation_id),
    decision_ns INTEGER NOT NULL,
    body TEXT NOT NULL,
    body_hash TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS decisions_no_update
BEFORE UPDATE ON decisions
BEGIN
    SELECT RAISE(ABORT, 'immutable decision');
END;

CREATE TRIGGER IF NOT EXISTS decisions_no_delete
BEFORE DELETE ON decisions
BEGIN
    SELECT RAISE(ABORT, 'immutable decision');
END;

CREATE TABLE IF NOT EXISTS audit_log (
    position INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    recorded_ns INTEGER NOT NULL,
    previous_hash TEXT NOT NULL,
    audit_hash TEXT NOT NULL UNIQUE,
    body TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_state (
    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
    entry_count INTEGER NOT NULL,
    head_hash TEXT NOT NULL
);

INSERT OR IGNORE INTO audit_state(singleton, entry_count, head_hash)
VALUES(1, 0, '0000000000000000000000000000000000000000000000000000000000000000');

CREATE TRIGGER IF NOT EXISTS audit_log_no_update
BEFORE UPDATE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'immutable audit record');
END;

CREATE TRIGGER IF NOT EXISTS audit_log_no_delete
BEFORE DELETE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'immutable audit record');
END;
```

## AuditStore behavior

append:
- read audit_state
- build AuditRecord with previous head
- insert audit_log
- compare-and-swap audit_state entry_count/head
- same transaction

verify_chain:
- begin ZERO_HASH
- read audit rows in position order
- decode canonical body
- compare indexed columns to body
- verify previous_hash
- verify audit_hash
- verify entry count
- verify head hash

Important:
This catches ordinary corruption, truncation relative to audit_state, row modification/reordering/index mismatches.
It does NOT prove external cryptographic attestation if an attacker can rewrite the entire DB and recompute state.

Required tests:
- candidate ordering canonical
- infeasible alternative cannot be selected
- audit chain verifies
- audit SQL updates rejected
- deliberately bypassed middle-record corruption detected
- audit failure rolls task transition back
- decision persistence immutable/idempotent

---

# TASK 7 — ATOMIC INVESTIGATION DECISION SERVICE

Schema v3 addition:

```sql
CREATE TABLE IF NOT EXISTS decision_applications (
    decision_id TEXT PRIMARY KEY REFERENCES decisions(decision_id),
    investigation_id TEXT NOT NULL REFERENCES investigations(investigation_id),
    transaction_id TEXT NOT NULL UNIQUE,
    resulting_investigation_body TEXT NOT NULL,
    resulting_investigation_hash TEXT NOT NULL,
    created_task_ids TEXT NOT NULL,
    applied_ns INTEGER NOT NULL
);

CREATE TRIGGER IF NOT EXISTS decision_applications_no_update
BEFORE UPDATE ON decision_applications
BEGIN
    SELECT RAISE(ABORT, 'immutable decision application');
END;

CREATE TRIGGER IF NOT EXISTS decision_applications_no_delete
BEFORE DELETE ON decision_applications
BEGIN
    SELECT RAISE(ABORT, 'immutable decision application');
END;
```

Atomic service contract:

BEGIN IMMEDIATE
1. Check existing decision_application for durable idempotency.
2. Load investigation/body hash.
3. Reject stale decision if `decision.input_state_hash != current.investigation_hash`.
4. Derive target investigation state.
5. Require decision.resulting_state_hash to equal actual result.
6. Validate follow-up tasks.
7. Insert immutable decision.
8. Append decision audit.
9. Update investigation with compare-and-swap hash.
10. Append investigation audit.
11. Create follow-up tasks.
12. Append task-created audit records.
13. Insert immutable decision application receipt.
COMMIT

Any exception → rollback all.

Outcome/state semantic constraints:
- ABSTAIN decision → ABSTAIN investigation
- BLOCKED decision → BLOCKED investigation
- DEFERRED decision → BLOCKED investigation
- follow-up task belongs to same investigation
- follow-up task starts PENDING
- attempt=0
- not already claimed
- created_ns cannot predate decision

Required tests:
- entire bundle commits atomically
- application idempotent after restart
- stale input state rejected
- declared result hash mismatch rejected
- partial follow-up creation failure rolls back entire decision
- ABSTAIN/BLOCKED/DEFERRED semantics
- duplicate follow-up task IDs rejected

---

# TASK 8 — CHECKPOINT / RESTART RECOVERY

## External effect lifecycle

PREPARED
ACKNOWLEDGED
OUTCOME_RECORDED

## RecoveryDisposition

NO_ACTION
PRESERVE_BLOCKED
RETRYABLE
RESUME_ACKNOWLEDGED
FINALIZE_FROM_RECEIPT
EXTERNAL_EFFECT_UNCERTAIN
TERMINAL

Recovery classification is NOT a new task state.

## Core rule

INTERNAL crashed → retryable
EXTERNAL_READ crashed → retryable
EXTERNAL_SIDE_EFFECT:
- CLAIMED with no dispatch receipt → retryable
- RUNNING no receipt → UNCERTAIN
- PREPARED only → UNCERTAIN
- ACKNOWLEDGED → resume, DO NOT redispatch
- OUTCOME_RECORDED → finalize from existing receipt

## prepare-before-dispatch protocol

RUNNING task
→ persist PREPARED
→ COMMIT
→ perform external mutation
→ provider acknowledgement
→ persist ACKNOWLEDGED

Never dispatch first and record intention later.

## Schema v4 additions

```sql
CREATE TABLE IF NOT EXISTS external_effect_events (
    position INTEGER PRIMARY KEY AUTOINCREMENT,
    effect_id TEXT NOT NULL,
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    attempt INTEGER NOT NULL,
    phase TEXT NOT NULL,
    recorded_ns INTEGER NOT NULL,
    event_id TEXT NOT NULL UNIQUE,
    body TEXT NOT NULL,
    UNIQUE(effect_id, phase)
);

CREATE TRIGGER IF NOT EXISTS external_effect_events_no_update
BEFORE UPDATE ON external_effect_events
BEGIN
    SELECT RAISE(ABORT, 'immutable external effect event');
END;

CREATE TRIGGER IF NOT EXISTS external_effect_events_no_delete
BEFORE DELETE ON external_effect_events
BEGIN
    SELECT RAISE(ABORT, 'immutable external effect event');
END;

CREATE TABLE IF NOT EXISTS recovery_classifications (
    recovery_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    classified_ns INTEGER NOT NULL,
    disposition TEXT NOT NULL,
    body TEXT NOT NULL,
    body_hash TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS recovery_classifications_no_update
BEFORE UPDATE ON recovery_classifications
BEGIN
    SELECT RAISE(ABORT, 'immutable recovery classification');
END;

CREATE TRIGGER IF NOT EXISTS recovery_classifications_no_delete
BEFORE DELETE ON recovery_classifications
BEGIN
    SELECT RAISE(ABORT, 'immutable recovery classification');
END;

CREATE TABLE IF NOT EXISTS checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    created_ns INTEGER NOT NULL,
    logical_state_hash TEXT NOT NULL,
    covered_audit_entries INTEGER NOT NULL,
    covered_audit_head_hash TEXT NOT NULL,
    body TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS checkpoints_no_update
BEFORE UPDATE ON checkpoints
BEGIN
    SELECT RAISE(ABORT, 'immutable checkpoint');
END;

CREATE TRIGGER IF NOT EXISTS checkpoints_no_delete
BEFORE DELETE ON checkpoints
BEGIN
    SELECT RAISE(ABORT, 'immutable checkpoint');
END;
```

## Logical state manifest

Hash deterministic ordered identities for:
- investigations
- tasks
- decisions
- task idempotency records
- external effect events

Checkpoint stores:
- created_ns
- logical_state_hash
- covered_audit_entries
- covered_audit_head_hash

Checkpoint audit record is appended AFTER computing the covered audit head to avoid circularity.

## Restart order

1. Open DB.
2. Validate supported schema.
3. Verify audit chain.
4. Verify entity body hashes.
5. Verify durable-state consistency.
6. Inspect interrupted tasks.
7. Inspect effect receipts.
8. Classify each interrupted task.
9. Persist recovery classifications.
10. Only then allow workers to claim work.

If integrity fails:
- mark recovery/store DEGRADED
- block autonomous mutation
- never silently rewrite/repair to make verification pass.

Required tests:
- interrupted internal task retryable
- interrupted external read retryable
- PREPARED external mutation is UNCERTAIN
- RUNNING side effect with no receipt is UNCERTAIN
- ACKNOWLEDGED mutation resumes without redispatch
- outcome receipt finalizes
- restart same logical state hash
- insertion order does not change logical manifest hash
- tampered task/investigation/decision body blocks recovery
- broken audit chain blocks recovery
- unsupported schema blocks recovery

---

# GLOBAL TDD / VERIFICATION

For each task:
1. Write RED test first.
2. Run focused test and observe expected failure.
3. Add minimum implementation.
4. Run focused tests.
5. Run full regression.
6. Refactor only while green.
7. Commit only after fresh verification.

Final H1 baseline:
pytest -q
pytest -W error::ResourceWarning -q
python -m compileall -q src tests

Never claim GREEN without fresh output.


====================================================================================================
05_REMAINING_TASKS_9_TO_12.md
====================================================================================================

# TASKS 9–12 — REMAINING H1 WORK

## Task 9 — Contract and execution firewall

Purpose:
Prove HELIOS cannot acquire trading/execution authority accidentally or through integration drift.

Required runtime restrictions:
- no broker protocol/adapter
- no order submission functions
- no ICARUS webhook POST
- no state-changing ICARUS admin call
- no bridge Alert schema reuse
- no import of ICARUS executor/brokers/config
- no execution credential loading
- no execution-authorized=true state
- no order-shaped advisory payloads

Required negative tests:
- test_helios_cannot_target_icarus_webhook
- test_helios_contract_rejects_execution_authority
- test_helios_icarus_adapter_has_no_post_operation
- test_helios_config_rejects_broker_credentials
- test_order_shaped_payload_cannot_cross_advisory_boundary
- test_helios_does_not_import_icarus_execution_modules

Recommended CI/static audit:
scan `src/helios` for:
submit_order
submit_market
submit_stop
submit_bracket
close_position
flatten
webhook_secret
alpaca_api_key
alpaca_secret_key
admin_token
position_size
order_id
contracts
execution_authorized

Any occurrence must be manually classified:
- negative test?
- documentation?
- forbidden runtime capability?

Fail release if forbidden runtime code exists.

## Task 10 — Security admission

Goal:
Treat all external content as data, never instruction authority.

Fail-closed admission protections for:
- path traversal
- absolute-path escape
- archive traversal
- archive bomb / decompression ratio
- excessive archive members
- oversized files
- unsupported content type
- malformed JSON/CSV/structured input
- unsafe deserialization
- schema abuse
- untrusted executable content
- prompt injection strings
- code injection strings
- hash mismatch
- source/version mismatch
- nested content expansion limits

Security APIs should return structured reason codes.
Do not auto-execute code embedded in evidence, archives, documents or web content.

## Task 11 — End-to-end synthetic NQ_STATE_ANOMALY

Synthetic fixture only.
No performance/profit claims.

Flow:
1. Create investigation `NQ_STATE_ANOMALY`.
2. Register synthetic source references.
3. Register causal observations with different knowledge times.
4. Add evidence DAG.
5. Create correlated vendor evidence sharing one upstream root.
6. Verify independence logic prevents double-count.
7. Add a future revision; historical snapshot remains unchanged.
8. Build candidate actions.
9. Include an unavailable ARGUS action with theoretically high information value.
10. Readiness makes ARGUS action infeasible.
11. Select a feasible action.
12. Record DecisionTrace.
13. Atomically update investigation + create follow-up task.
14. Transition follow-up task.
15. Simulate external-side-effect PREPARED crash.
16. Restart.
17. Recovery classifies it EXTERNAL_EFFECT_UNCERTAIN.
18. Verify no redispatch.
19. Create deterministic checkpoint.
20. Verify audit chain and logical state hash.

Acceptance:
- synthetic label preserved
- future information excluded
- shared-root evidence not treated independent
- unavailable integration cannot be selected
- no execution authority created
- restart deterministic
- no duplicate external side effect

## Task 12 — Documentation / final gate

Create:
README.md
docs/ARCHITECTURE.md
docs/OWNERSHIP.md
docs/CONTRACTS.md
docs/SECURITY.md
docs/RECOVERY.md
docs/INTEGRATION_READINESS.md
docs/UNFINISHED_MATRIX.md
docs/CAPABILITY_MATRIX.md
docs/TEST_EVIDENCE.md

Document clearly:
- implemented vs planned
- source-derived requirements vs inferred engineering choice
- sibling ownership
- integration readiness
- causal-time semantics
- qualification authority
- evidence lineage
- synthetic evidence behavior
- restart semantics
- external side-effect uncertainty
- execution firewall
- security admission
- known blockers
- no live trading authority
- no profitability claim

Final verification:
pytest -q
pytest -W error::ResourceWarning -q
python -m compileall -q src tests

Then perform static audits described in Task 9.

Do not merge/deploy automatically.


====================================================================================================
06_RISK_AND_UNFINISHED_LEDGER.md
====================================================================================================

# RISK / BLOCKER / UNFINISHED LEDGER

## P0/P1 integration concerns

ICARUS-RISK-001
- Unknown non-text bridge events can enter fill dispatch.
- HELIOS must not integrate by writing to this surface.
- H5 integration requires a reviewed read-only interface or separate ICARUS hardening change.

AION-INTEGRITY-001
- AION event hash chain does not cover every durable state family.
- Do not describe AION or HELIOS as externally tamper-proof based on a local hash chain.
- HELIOS H1 audit ledger should cover all HELIOS durable decision-state mutation families.

EVIDENCE-LAB-IMPLEMENTATION-001
- Cross-system evidence contract is planned/documented but not implemented on current main.
- HELIOS must not runtime-depend on planned modules.

ARGUS-SOURCE-ACCESS-001
- No verified native ARGUS source package found in current connected scope.
- Adapter state: DESIGN_ONLY / SOURCE_REQUIRED.

ATHENA-SOURCE-ACCESS-001
- No verified native ATHENA package found.
- Adapter state: DESIGN_ONLY / SOURCE_REQUIRED.

ORACLE-SOURCE-ACCESS-001
- Secondary evidence of partial checkpoint exists, but native source package inaccessible in connected scope.
- Adapter state: PARTIAL / SOURCE_REQUIRED.

AEGIS-SOURCE-ACCESS-001
- Referenced secondarily; no verified native package found.
- Adapter state: UNVERIFIED / SOURCE_REQUIRED.

NEXUS-SOURCE-ACCESS-001
- Handoff/secondary evidence exists; no verified canonical connected repo located.
- Adapter state: EVIDENCE_ONLY / SOURCE_REQUIRED.

## Claims that must remain bounded

Do NOT claim:
- HELIOS software is implemented in GitHub from this conversation.
- H1 tests passed.
- HELIOS is production ready.
- HELIOS is tamper-proof.
- HELIOS has proven trading edge.
- user-reported backtests are independently verified.
- ORACLE/AION/DAEDALUS repo-recorded test claims were freshly reproduced unless future session actually runs them.

## Engineering risks for repo-capable implementation

1. Draft code packets may need small import/export/schema migration corrections.
2. Contract serialization must be tested against enum/dataclass/nested tuples.
3. Audit chain must remain atomic with mutable state updates.
4. Checkpoint coverage must avoid circular inclusion of its own audit record.
5. Restart classifier must distinguish safe retry vs ambiguous external mutation.
6. `EXTERNAL_SIDE_EFFECT` is for non-trading external mutation only; HELIOS still never gets broker/order capability.
7. Integration readiness must be separate from epistemic value so unavailable actions remain unselectable.
8. Source confidence, timing confidence, evidence independence and model/predictive confidence must not be collapsed into one dimension.


====================================================================================================
07_CONTINUATION_INSTRUCTIONS.md
====================================================================================================

# CONTINUATION INSTRUCTIONS FOR CODEX / WORK

You are continuing an already-audited HELIOS PRIME project.

Do NOT restart the architecture phase unless a concrete contradiction in repository state requires it.

## First action

Create or use the sibling repository:

`helios-prime`

Use a new isolated branch/worktree.

Do not develop on main/master.

## Source of truth

Read in order:
1. `00_SOURCE_REQUIREMENTS_ORIGINAL.txt`
2. `README_FIRST.md`
3. `01_REPOSITORY_AUDIT.md`
4. `02_ARCHITECTURE_AND_INVARIANTS.md`
5. `03_H1_IMPLEMENTATION_PLAN.md`
6. `04_TASKS_1_TO_8_CODE_AND_TEST_DRAFTS.md`
7. `05_REMAINING_TASKS_9_TO_12.md`
8. `06_RISK_AND_UNFINISHED_LEDGER.md`

## Execution mode

Implement Task 1 through Task 12 sequentially with strict RED→GREEN TDD.

For every task:
- show the RED command and expected failure;
- implement minimal code;
- show focused GREEN command/output;
- run full regression;
- run ResourceWarning-strict suite;
- compileall;
- commit;
- record commit SHA in `docs/TEST_EVIDENCE.md`.

Do not claim results you did not execute.

## Required progress ledger

Create:
`.superpowers/sdd/helios-prime-h1/progress.md`

Record:
- task
- tests added
- RED evidence
- implementation files
- focused GREEN evidence
- full suite evidence
- commit SHA
- unresolved findings
- next task

## Non-negotiable boundaries

HELIOS:
- does information acquisition/research planning;
- never sends broker orders;
- never owns ICARUS execution;
- never loads execution credentials;
- never self-certifies source authority;
- never invents knowledge timestamps;
- never treats correlated evidence as independent;
- never auto-retries ambiguous external side effects;
- never silently repairs integrity disagreement;
- never merges/deploys automatically.

## Completion definition

H1 is complete only when fresh tests prove:
- canonical deterministic serialization;
- strict timestamp validation;
- source qualification separation;
- causal/prefix invariance;
- provenance DAG correctness;
- correlated-source handling;
- synthetic provenance retention;
- durable state transitions;
- restart-safe idempotency;
- retry/dead-letter correctness;
- atomic rollback;
- immutable decisions;
- audit-chain integrity;
- stale-decision rejection;
- atomic decision application;
- crash recovery;
- ambiguous external effect protection;
- contract/schema fail-closed behavior;
- execution firewall;
- security admission;
- full synthetic NQ_STATE_ANOMALY scenario.

Final commands:
pytest -q
pytest -W error::ResourceWarning -q
python -m compileall -q src tests

Then perform the execution-symbol and sqlite-connect static audits.

Stop before merge/deploy and return:
- repo URL/name
- branch/worktree
- commit SHAs
- exact test outputs
- unresolved issues
- capability matrix
- implementation/design-only matrix
- recommended H2 start point
