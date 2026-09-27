"""Canonical registry of the Divine Providence / ICARUS subsystems.

Each system keeps its own source tree under ``systems/<name>`` and runs in its
own interpreter process with only its own import roots on ``sys.path``; several
systems ship flat top-level modules (``scripts``, ``recovery_*``, evaluator
modules), so they are never imported into one shared process. Authority text is
taken from the recovered master handoff (section 13 sibling authority map).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def systems_root() -> Path:
    return repo_root() / "systems"


@dataclass(frozen=True)
class System:
    name: str
    title: str
    version: str
    role: str
    owns: str
    must_not: str
    import_roots: tuple[str, ...] = (".",)
    test_args: tuple[str, ...] = ("-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "addopts=")
    docs: tuple[str, ...] = ("README.md",)
    test_timeout_s: int = 900
    extra: dict = field(default_factory=dict)

    @property
    def path(self) -> Path:
        return systems_root() / self.name

    def pythonpath(self) -> list[str]:
        return [str((self.path / r).resolve()) for r in self.import_roots]


SYSTEMS: dict[str, System] = {s.name: s for s in [
    System("nexus", "NEXUS Adaptive Market Fabric", "1.15.0 (iteration 32)",
           "Causal market-data substrate: identity/clocks, causal replay, source health, representation evidence, sibling-safe market packets.",
           "Market-data fabric and sibling-safe instant bundles.",
           "Absorb AION/ARGUS/ATHENA/DAEDALUS/ICARUS authority; call candle proxies L2; forward-fill truth; production authorization.",
           import_roots=("src",), docs=("README.md", "VALIDATION_STATUS.md", "docs/current-state.md", "docs/INTEGRATION_MAP.md")),
    System("daedalus", "DAEDALUS Research OS", "0.1.0 (NEXUS-integrated receiver)",
           "Scientific validation, protected evidence, research-candidate testing, promotion authority.",
           "Protected holdouts and promotion decisions.",
           "Spend protected holdouts on scanned history; grant production execution.",
           import_roots=("src",), docs=("README.md", "NEXUS_INTEGRATION_CHECKPOINT.txt", "docs/NEXUS_INTEGRATION.md"),
           test_timeout_s=1200),
    System("aion", "AION Market Memory", "0.1.0",
           "Durable evidence memory / historical atlas: append-only hash-linked event ledger, as-of replay, tamper detection.",
           "Long-lived provenance/evidence persistence.",
           "Execute orders (exports stay execution_authorized=false); treat the PARALLAX proposal as built.",
           docs=("README.md",)),
    System("argus", "ARGUS Microstructure OS", "0.1.0 (starter foundation)",
           "Authenticated microstructure / order-flow / execution-physics authority.",
           "True microstructure truth tiers.",
           "Relabel candle-derived proxies as L2/order-book truth; hold broker/order authority.",
           import_roots=("src",)),
    System("athena", "ATHENA Supervisory Fabric", "0.1.0 (Phase-0 foundation)",
           "Supervisory world-state interpretation, confidence, abstention, risk and routing.",
           "Advisory supervision, uncertainty and abstention.",
           "Place broker orders; claim a trained world model.",
           import_roots=("src",)),
    System("oracle", "ORACLE Financial & Research Automation Fabric", "Checkpoint C 75% @ 6255339",
           "Research automation: autonomous loop, outbox/journal, scheduler, thesis monitor, action board, tab API.",
           "Research orchestration only.",
           "Promote, supervise or execute (sibling authorities retain those); rebuild layers already present at checkpoint C.",
           import_roots=("src",), docs=("README.md", "START_HERE_SOL_EXTRA_HIGH.md")),
    System("prometheus", "PROMETHEUS Evolution Loop", "0.5 unified (merge 136563e, ADR 0004)",
           "Closed research/meta-evolution loop (SENTINEL -> FORGE -> ASCENSION): disagreement mining, deterministic replay, negative-result memory.",
           "Falsifiable research hypotheses and experiment routing.",
           "Self-authorize production; perform cryptographic verification it does not implement.",
           import_roots=("src",), docs=("README.md", "docs/VALIDATION_STATUS.md")),
    System("ascension", "ASCENSION Evaluator / Trust / Collision Layer", "Conformance Kit 0.1 + Adapter 0.4 + Evaluator 0.8",
           "Evaluator fabric, manifest-trust collision adapter, collision detector, context distillation, sibling-manifest conformance.",
           "Evaluation and transfer gating.",
           "Manufacture sibling signatures/trust roots; treat conformance as authentication or Transfer.",
           docs=("kits/ASCENSION_Sibling_Manifest_Conformance_Kit_v0.1/README.md", "PROMETHEUS_v0.5_GAP_MAP.md", "AUTHORITY_HANDOFF_CHECKLIST.md")),
    System("aegis", "AEGIS Challenger Forge", "Checkpoint 009",
           "Candidate generation, causal/holdout integrity, incumbent-vs-challenger validation, red-team program.",
           "Candidate discovery and adversarial validation.",
           "Hold live execution authority; spend the final NQ/BTC holdouts; un-quarantine directional alphas.",
           docs=("README.md", "state_capsule_v009.json")),
    System("janus", "JANUS Infinity", "Run 038",
           "Project-twin temporal truth, conflict/proof synchronization, acquisition/recovery lineage.",
           "Descriptive project-twin truth and proof synchronization.",
           "Select branch winners; absorb Infrastructure/AEGIS/VECTOR/NEXUS/SuperMesh/live-trading authority.",
           import_roots=("src",), docs=("README.md", "STATE_CAPSULE_RUN_038.md", "MASTER_HANDOFF.md")),
    System("infrastructure", "Infrastructure Supervisory Loop", "V49",
           "Persistence, recovery, locking, leases, authenticated restoration, supervisory safety.",
           "Durable persistence/recovery/locking.",
           "Hold market or research authority; claim production adoption (READY_TO_COMMIT=false).",
           docs=("README.md",)),
    System("supermesh_x", "SuperMesh-X", "3.7.0 (Cycle 7 FINAL2)",
           "Canonical provider/tool/model capability mesh; runtime/control plane; trusted-time and witnessed transparency.",
           "Capability/provider/runtime orchestration.",
           "Grant automatic business/trading authority.",
           docs=("README.md", "BUILD_REPORT_V370.md", "SKILL.md")),
]}

# Recovered integration direction (master handoff section 1). Descriptive only.
INTEGRATION_DIRECTION = ["NEXUS", "JANUS", "AEGIS", "VECTOR", "ASCENSION", "SuperMesh-X"]

GLOBAL_INVARIANTS = [
    "BUILT != VERIFIED != READY_TO_COMMIT",
    "execution_authorized=false and production_authorized=false are the safe defaults everywhere",
    "Engineering tests do not prove trading edge, profitability or causality",
    "Protected holdouts, temporal causality, provenance and deterministic replay are non-negotiable",
    "Subsystems exchange proof-carrying handoffs; none silently absorbs sibling authority",
]


def get(name: str) -> System:
    try:
        return SYSTEMS[name]
    except KeyError:
        raise KeyError(f"unknown system {name!r}; known: {', '.join(sorted(SYSTEMS))}") from None
