# PROMETHEUS — Autonomous Systems Evolution Loop

PROMETHEUS is a **research-only meta-layer** for the Icarus intelligence stack. It observes causally compatible sibling evidence, mines disagreements, generates constrained hypotheses, attacks them with adversarial checks, replays candidates against the same eligible evidence, and preserves both successful and failed research.

PROMETHEUS does **not** own production execution, broker actions, supervisory world state, market-data truth, cryptographic trust roots, or statistical promotion.

## v0.5 unified slice

This build merges the two independently verified v0.5 lineages from the common v0.3 checkpoint:

- **v0.4 lineage + diagnosis → v0.5 experiment routing** (stale-aware research lineage, disagreement diagnosis, deterministic replay-eligibility routing); and
- **v0.4 provenance attestation → v0.5 external attestation + provenance lineage** (content-addressed provenance manifests, external attestation receipts, ancestry verification).

Both feature sets are active in the same loop. A `READY_FOR_DAEDALUS_REVIEW` packet now requires **both** a clean stale-aware lineage binding **and** a matching provenance manifest with a complete ancestry report. See `docs/changes/2026-09-26-prometheus-v0.5-unified-merge.md` for how the branches were reconciled.

### Experiment routing (v0.4 lineage-diagnosis lineage)

The executable slice includes all v0.4 lineage/diagnosis capabilities plus:

- immutable `ExperimentRouteDecision` artifacts between diagnosis and FORGE replay;
- preflight lineage and staleness checks before replay eligibility is granted;
- deterministic routing that prefers reducible/actionable disagreement over healthy role specialization;
- qualitative research priority bands instead of a misleading global score;
- explicit `DEFER_FRESH_EVIDENCE` and `ABSTAIN_SPECIALIZATION` outcomes;
- `DeferredExperiment` artifacts that distinguish “not eligible to run” from “tested and rejected”;
- stale contract/plugin lineage blocks replay itself, not only DAEDALUS review handoff;
- exact negative-result reuse is scoped to the immutable routing/contract context; and
- CLI route observability (`action`, `priority_band`, `reason_code`).

Stale-aware research lineage lives in `prometheus_loop.lineage` (`build_lineage_manifest`, `detect_stale_lineage`).

### External attestation + provenance lineage (v0.4 provenance lineage)

The executable slice extends the v0.4 provenance boundary with:

- immutable `ExternalExecutionAttestation` references bound to the exact `PluginExecutionEvidence` content digest;
- immutable `AttestationVerificationReceipt` artifacts identifying the external verifier, trusted-root identity, verification policy, and mandatory check outcomes;
- explicit `OPTIONAL` and `REQUIRE_VERIFIED` plugin-attestation policies, with the policy included in deterministic loop identity;
- fail-closed one-to-one plugin-evidence → attestation → receipt binding whenever external evidence is supplied;
- strict-mode degradation and promotion suppression when selected-plugin attestation coverage is missing, partial, or unverified;
- v0.5 `ResearchProvenanceManifest` binding the attestation/receipt IDs and policy alongside the existing plugin, observation, source-contract, and parent-manifest identities;
- a deterministic `ProvenanceLineageReport` that walks persisted ancestry and rejects missing parents, wrong artifact types, content-ID substitution, duplicate parent IDs, and cycles; and
- a `ResearchPromotionPacket` that must include both the current provenance manifest and its complete lineage report before `READY_FOR_DAEDALUS_REVIEW` can exist.

Provenance-ancestry verification lives in `prometheus_loop.provenance_lineage` (`ProvenanceLineageReport`, `verify_provenance_lineage`), separate from the stale-aware lineage module.

The attestation receipt is **not** a claim that PROMETHEUS performed cryptographic verification. DSSE parsing, X.509 validation, Sigstore/Rekor/Fulcio/TSA verification, key management, and trust-root rotation remain outside PROMETHEUS. The local package validates deterministic binding to a receipt produced by an identified external verifier.

The v0.4/v0.3 protections remain: normalized plugin execution evidence, contribution reports, stale/tampered manifest rejection, NEXUS v0.3 contract binding, causal/sibling normalization, negative-result reuse, and structural rejection of production authorization.

The Python package still **does not pretend to invoke ChatGPT plugins itself**. Real plugin execution occurs in the ChatGPT host; local tests use typed host execution evidence.

## Plugin rule

Each new top-level loop run must consider every visible plugin, invoke every plugin with positive marginal value for that run, and record why all others were skipped. Deep Research is mandatory when available. Internal SENTINEL microchecks do not individually call Deep Research; the containing top-level run satisfies the requirement.

This rule intentionally does **not** mean "call every installed plugin regardless of relevance." Irrelevant, redundant, unavailable, or policy-blocked plugins are retained in the audit with an explicit reason. Local Python consumes typed host execution records.

See `docs/architecture/plugin-orchestration.md`, `docs/architecture/plugin-evidence-and-promotion.md`, `docs/architecture/sibling-bindings.md`, `docs/architecture/lineage-and-diagnosis.md`, `docs/architecture/experiment-routing.md`, and the ADRs under `docs/adr/`.

## Authority boundaries

- **NEXUS:** market-data identity, causal timing, replay, source health, representations, factor/topology/OOD ingredients.
- **AION:** durable sibling evidence memory and historical atlas.
- **ARGUS:** authenticated microstructure and execution-physics evidence.
- **ATHENA:** supervisory world state, uncertainty, confidence, routing, risk and abstention.
- **DAEDALUS:** scientific validation, protected evidence and later promotion/acceptance.
- **Icarus:** production decisions, broker state and orders.
- **External verifier:** cryptographic/signature/trust-policy verification represented by a PROMETHEUS receipt.
- **PROMETHEUS:** research orchestration, experiment routing, stale-aware lineage, deterministic binding, provenance/lineage verification, comparison artifacts and local research-memory indexing.

Any `ResearchPromotionPacket` fixes `production_authorized=False` and rejects attempts to set it true. A packet means only **ready for DAEDALUS review**, not DAEDALUS acceptance.

## Run verification

```bash
PYTHONPATH=src python -m compileall -q src tests
PYTHONPATH=src pytest -q
```

## Run deterministic demos

Backward-compatible OPTIONAL fixture (also reports the experiment route):

```bash
PYTHONPATH=src python -m prometheus_loop.cli demo --memory /tmp/prometheus-demo.jsonl
```

Strict externally-attested fixture:

```bash
PYTHONPATH=src python -m prometheus_loop.cli demo-strict-attested --memory /tmp/prometheus-strict-demo.jsonl
```

Both demos use **fixture plugin execution records** for Deep Research and Exa. They prove the audit/orchestration contract; they do not make network calls or claim that those plugins were invoked by the local Python process.

The strict demo uses deterministic **fixture** attestations and fixture verification receipts. It proves structural binding and policy behavior only. The output explicitly reports `cryptographic_verification_performed_by_prometheus=false`.

## Current design and plan

- Design (overall): `docs/superpowers/specs/2026-09-24-prometheus-autonomous-systems-evolution-design.md`
- Experiment routing: `docs/architecture/experiment-routing.md` (a bounded continuation of the approved architecture; no separate Superpowers plan document was required)
- Lineage + diagnosis plan: `docs/superpowers/plans/2026-09-25-prometheus-v0.4-lineage-diagnosis.md`
- Attestation design: `docs/superpowers/specs/2026-09-25-prometheus-v0.5-external-attestation-lineage-design.md`
- Attestation plan: `docs/superpowers/plans/2026-09-25-prometheus-v0.5-external-attestation-lineage.md`
- Unified merge record: `docs/changes/2026-09-26-prometheus-v0.5-unified-merge.md`
- Validation: `docs/VALIDATION_STATUS.md`

**Stale when:** attestation receipt semantics, trusted-verifier integration, routing policy, disagreement taxonomy, sibling authority/contracts, the pinned NEXUS release identity, plugin execution semantics, lineage/provenance schema, or DAEDALUS review-ingress authority changes.
