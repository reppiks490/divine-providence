# Executive Summary

We must now **complete ICARUS recovery and persist all pipeline state** into the `reppiks490/Icarus` repo.  The integration branch (`integration/icarus-capability-fabric-20260924`) contains the newly designed control-plane schemas and guides, but none of the original S1–S3 outputs were durably saved.  Our plan is to (1) **inventory** everything from S1–S3 (claims, evidence, test results) from the chat and existing files, (2) **validate** their time-alignment and provenance, (3) populate the **`icarus-control-v1` manifests** and create the canonical S1→S5 handoff artifacts, (4) run only the **essential ablation/mutation tests** to settle any unresolved claims, and (5) prepare onboarding docs for the next agents.  We schedule this in phases (Assess/Define/Pilot/Scale) similar to a standard AI/ML ops roadmap【17†L218-L224】, aiming to minimize re-work and lock in the evidence we already have.  

Key points and sources:

- **Inventory & Provenance:**  First, list all S1/S2/S3 artifacts (code, data snapshots, results, claims) and where they live.  This mirrors an “Assess” phase in standard ML ops【17†L204-L210】. Each datum must be tied to a timestamp, data source, and commit hash.  We will record every claim and evidence ID in the control manifest so nothing is unstamped.  
- **Immutability & Control Plane:**  We adopt a strict GitOps-style control plane: every pipeline artifact is a versioned, immutable manifest【17†L232-L240】【20†L268-L270】.  For example, an *evidence record* for each result must include actor, input hash, model version, output, verdict and timestamp【17†L232-L240】【20†L268-L270】, so we can always trace *why* any decision was reached.  
- **Targeted Testing:**  Only the **critical disputed claims** get re-tested.  We apply *ablation studies* (i.e. remove one component or signal at a time) and *mutation tests* (inject small faults) to verify robustness【26†L120-L124】【26†L140-L144】【15†L260-L264】.  Ablation “removes” parts to see their impact【26†L120-L124】【26†L140-L144】.  Mutation testing flips code logic or data (e.g. flip a threshold, timestamp, or sign) and ensures the test suite fails as expected【15†L260-L264】.  This shows our tests are meaningful.  
- **Onboarding & Handoff:**  We will produce a concrete `coordination/HANDOFF_PACKET_*.md` and agent guide, as already drafted, plus `state-index.schema.json` and `handoff.schema.json` files, to give incoming workers exactly what to consume.  All artifacts and decisions will be anchored by commit SHAs and stable IDs, so the handoff is self-contained.

The rest of this report lays out the detailed steps, timeline, commands, diagrams, and checklists needed to finish ICARUS recovery properly.

## 1. Inventory S1–S3 Artifacts

We must catalog **every claim, evidence, and result** from Stages 1–3.  Because none of this was persisted, we rely on the coordination docs and chat to reconstruct it.  In practice we will generate a table like Table 1 with entries:

| Stage | Artifact/Claim                  | Location                     | Status             | Gap/Next Step                           |
|-------|---------------------------------|------------------------------|--------------------|-----------------------------------------|
| S1    | Base strategy code/config       | `strategy/` (repo), agent    | present (no change)| – (ensure copied into control plane)    |
| S1    | Risk/Reward targets or claims   | *coordination docs/convo*    | **present**        | Assign permanent IDs, store in manifest |
| S2    | Vote aggregation outputs (Pulse) | *coordination docs/convo*    | **missing**        | Insert into `evidence/`; note data/commit |
| S3    | Composite performance reports   | *coordination docs/convo*    | **missing**        | Run stress/ablation; store results      |
| S3    | Specific claim XLAG-001 (etc.)  | *coordination docs/convo*    | disputed (needs test) | Targeted ablation/mutation required  |

*Table 1: Example inventory of ICARUS artifacts by stage.*  

This resembles the “Assess” phase of a standard AI workflow, where one inventories all active components and data【17†L204-L210】. We will fill this table by inspecting the new `coordination/` files (e.g. `CURRENT_FINDINGS.md`, `HANDOFF_PACKET_*.md`) and any loose notes. Each claim will get a stable `CLAIM_ID` and any evidence an `EVIDENCE_ID`.  Any missing evidence (cells “missing” above) will be marked for targeted completion.

## 2. Validate Temporal Integrity & Provenance

For each artifact, **verify its time alignment** and source:

- **Temporal integrity:**  Ensure no data used was from the future relative to a decision.  Every price or indicator must have an `observed_at` and `available_at` timestamp, and those must precede the `decision_at`.  This avoids the classic “future-leakage” pitfall in time-series modeling.  We will inspect data timestamps and programmatic roll logic.  If any lookahead is detected, the data is considered invalid.  
- **Provenance:**  Link each artifact to a commit SHA or raw data hash.  For example, “backtest X” should cite the engine commit it used, and “train/test splits” should cite raw CSV hashes. This mirrors MLflow’s advice to include *Model ID, version, artifact hash, lineage* for reproducibility【17†L232-L240】.  We will update the `state.json` (or better, the new `control/manifest.json` index) so each evidence record includes `[commit, source, tag, timestamp]`.

Practically, we will extend the `state-index.schema.json` manifest to index all known artifacts by stage, with fields like `timestamp`, `source_id`, `commit_hash`, and link to any parent evidence.  No artifact moves forward without such provenance. This enforces the control-plane rule that *“uncertainty can never increase authority”*【20†L268-L270】 — in other words, if anything is unknown or stale, a claim is demoted, not advanced.

## 3. Populate Control-Plane Manifests and Handoff Packets

Using the above inventory, we will fill in the **`icarus-control-v1` manifests** and the final handoff JSON.  Key steps:

- Create `control/manifest.json` (or `state.json`) with pinned `repository` SHA, policy epoch, and lists of claims/evidence for S1–S3. For example:
  
  ```json
  {
    "pipeline_version": "icarus-pipeline-v1",
    "revision": "007e70189945b8e112904cf92b2b1a12e43792d6",
    "claims": [
       {"claim_id": "S1-BASESTRAT", "status": "APPROVED", "evidence": ["EVID-xxx"]},
       {"claim_id": "S2-VOTEWEIGHT", "status": "PENDING_TEST", "evidence": []},
       ...
    ],
    "dependencies": [ ... ],
    "control_flags": {
      "DATA_SUFFICIENCY_STATUS": "UNKNOWN",
      "ESTIMATOR_VALIDITY_STATUS": "UNKNOWN",
      "ABLATION_READINESS_STATUS": "UNKNOWN",
      "REDUNDANCY_STATUS": "UNKNOWN"
    }
  }
  ```

- Fill `control/claims/` and `control/evidence/` subfolders with immutable YAML/JSON manifests for each claim and evidence item. Each manifest includes lineage (parent IDs), source info, and status.  (These schemas are defined by `handoff.schema.json` in the branch.)

- Assemble the S1→S5 **handoff packet**: essentially a finalized `handoff.json` that ties all the above together, including explicit instructions for S4 (e.g. "REP AVOID", "DEFECT_REPAIR", or "RECLASSIFY"). The `coordination/HANDOFF_PACKET_*.md` file should be turned into a machine-readable JSON according to `handoff.schema.json`.

All of this makes the pipeline truly *immutable and auditable*.  We are essentially following the GitOps best practice of storing all pipeline state as code so it’s reproducible【17†L232-L240】【20†L268-L270】. Once this is done, S4 (repair) will no longer be “waiting for S3”; it will have a concrete blob to consume.

## 4. Run Targeted Ablation & Mutation Tests

With the manifest in place, only **the unresolved S3 claims** get new work.  We do not redo broad research — only decisive tests that can alter a claim’s status. Steps:

- **Identify disputed claims:**  For each claim marked PENDING or BLOCKED, check what evidence is missing. Common gaps include lack of out-of-sample stress tests or uncertainty bounds.  
- **Design ablation tests:**  For each missing piece, disable that component in code and re-run the relevant analysis. For example, if *XGBoost5* composite was questionable, run the backtest with XGBoost5 votes zeroed out. This directly uses the ablation concept: remove components in a controlled setting to see effect【26†L140-L144】. If the performance drops or a signal flips sign, we gain confidence (or discover an issue).  
- **Apply mutation testing:**  Introduce small faults to ensure our tests catch them【15†L260-L264】. For example, flip a comparison in a threshold test, or nudge a time index by one bar. A robust test suite should *fail* on these mutations. Document each mutation and its expected failure as negative controls.  
- **Record results:** Every test run is a `control/runs/` entry with a unique ID. Its outcome either *kills* a mutant (successful test) or identifies an unaddressed weakness. Only if tests pass on the correct code and fail on mutants do we mark the claim as resolved.

This approach is grounded in best practices: **ablation studies** help isolate each factor’s impact【26†L120-L124】【26†L140-L144】, while **mutation tests** verify that our test oracles are sound【15†L260-L264】. Together, they provide strong independent verification that the existing strategy (or its fixes) are valid. 

## 5. Onboarding Manifests & Agent Guides

Finally, we prepare the deliverables for the next phase (S4/S5 agents):

- **Agent connection guide:**  Refine `coordination/AGENT_CONNECTION_GUIDE.md` to list exactly which files the next agents may read/write, and which branches they should target.  Include the branch name (`integration/icarus-capability-fabric-20260924`) and the base commit (`007e7018…`).  
- **Handoff packet:**  Ensure `coordination/HANDOFF_PACKET_2026-09-24.md` (and its JSON version) clearly states the *one-line request* for each surviving claim (e.g. `DEFECT_REPAIR` for bugs, `APPROVED_IMPLEMENTATION` for ready claims). This is the baton for S4.  
- **Onboarding manifest:** Possibly a `coordination/ONBOARDING_INSTRUCTION.md` summarizing how to apply these guides, updating agents to treat `state.json` as an index and to never modify history.  

By writing these docs into the repo, any new agent or human collaborator can pick up exactly where S3 left off, with no hidden context needed. This follows MLflow’s principle that a shared “context endpoint” and metadata schema let teams onboard quickly【19†L1-L4】【20†L235-L242】.

## 6. Actionable Steps (with Git commands)

Here are the **next 10 concrete steps**, each with exact git commands and file actions. We assume you (the user) run these:

1. **Fetch latest `main` and create recovery branch:**  
   ```bash
   git fetch origin main
   git checkout -b icarus-recovery-2026-09 origin/main
   ```  
   (Start a fresh branch named `icarus-recovery-2026-09` from commit `007e7018…`.)  

2. **Add control/manifest and state index:**  
   ```bash
   mkdir -p control
   touch control/manifest.json
   ```  
   Populate `control/manifest.json` with the pipeline version, base commit `007e7018…`, and empty arrays for claims and evidence (following `state-index.schema.json`).  
   *Commit:* `git add control/manifest.json` & `git commit -m "Initialize control manifest and state index"`.

3. **Document S1–S3 inventory:**  
   Create `control/claims_inventory.md` summarizing each claim from S1-S3 (copied from `CURRENT_FINDINGS.md`). For each, note its current evidence links or gaps.  
   *Commit:* `git add control/claims_inventory.md` & `git commit -m "Document inventory of S1–S3 claims and evidence"`.

4. **Create empty evidence entries:**  
   For each missing evidence item, touch a stub:  
   ```bash
   mkdir -p control/evidence
   touch control/evidence/EVID-S2-000.json  # etc.
   ```  
   Edit each with placeholder fields (to be filled after tests).  
   *Commit:* `git add control/evidence/*` & `git commit -m "Add stubs for missing evidence records"`.

5. **Populate handoff schema:**  
   Use the `handoff.schema.json` to format the S1–S3 handoff. For example, create `control/handoff_S3.json` with stage info.  
   *Commit:* `git add control/handoff_S3.json` & `git commit -m "Draft S3→S4 handoff packet (unfinalized)"`.

6. **Implement ablation tests:**  
   In the code tests directory, write minimal tests that remove each disputed component. For example, in `tests/test_ablation.py`, simulate leaving out Pulse votes.  
   *Commit:* `git add tests/test_ablation.py` & `git commit -m "Add ablation tests for disputed S3 claims"`.

7. **Implement mutation tests:**  
   Similarly, create `tests/test_mutation.py` with simple modified versions (e.g. invert a condition) and assert that the baseline output changes.  
   *Commit:* `git add tests/test_mutation.py` & `git commit -m "Add mutation tests to ensure test suite catches injected faults"`.

8. **Run CI suite locally:**  
   Execute `pytest` (or your CI script) to verify these tests fail correctly on mutated code and pass on original code. Fix any issues so all CI tests pass.  
   *Commit:* If any fixes are needed, commit with message like `Fix deterministic replay for consistent test output` and update `commit-msg: unit-tests` as needed.

9. **Finalize control manifest:**  
   After tests, update `control/manifest.json` statuses: mark any claims now *APPROVED* or *BLOCKED*. Ensure all dependencies and commit SHAs are filled in.  
   *Commit:* `git add control/manifest.json` & `git commit -m "Finalize control-plane manifest with evidence and claim statuses"`.

10. **Push and open PR:**  
    ```bash
    git push -u origin icarus-recovery-2026-09
    ```  
    Then, create a PR from `icarus-recovery-2026-09` into `main` (e.g. via GitHub UI) with title “S1–S3 recovery and handoff integration.” Include the PR checklist below in the description.  

Each commit should avoid mixing changes; for example, one commit for inventory, one for tests, one for manifest changes, etc. Use `[skip ci]` tags if needed during the recovery (but be careful not to skip important tests in the final run).

## 7. Timeline (Gantt Chart)

The work spans roughly 4 weeks, in phases. Below is a simplified Gantt chart outline:

```mermaid
gantt
    dateFormat  YYYY-MM-DD
    title ICARUS Recovery & Persistence Plan
    section Assess (Inventory)
    Inventory S1–S3 artifacts        :active, des1, 2026-09-25, 2026-10-01
    Validate timestamps/provenance   :des2, after des1, 3d
    section Define (Control Plane)
    Write control manifests & schemas:crit, des3, 2026-10-04, 5d
    Draft handoff packet             :des4, after des3, 3d
    section Pilot (Testing)
    Implement ablation/mutation tests: des5, 2026-10-13, 5d
    Execute tests and fix issues     :des6, after des5, 4d
    section Final (Merge Prep)
    Finalize state.json and README   :des7, 2026-10-21, 3d
    PR review & S5 checklist        :active, des8, after des7, 2026-10-24, 2d
```

*(Dates and durations are illustrative; adjust to team velocity. This schedule echoes the four-phase roadmap of MLflow’s standards guide【17†L218-L224】.)*

## 8. Pipeline Flow (Mermaid Diagram)

Below is a flowchart of the S1→S5 pipeline.  We show **durable handoff artifacts** between stages, not live data.  

```mermaid
flowchart LR
    S1["Stage 1: Base Strategy"]
    S2["Stage 2: Weighted Votes"]
    S3["Stage 3: Composite Strategy"]
    S4["Stage 4: Repair/Integration"]
    S5["Stage 5: Verification"]

    S1 -->|handoff (claims JSON)| S2
    S2 -->|handoff (tests & evidence)| S3
    S3 -->|handoff (immutable control packet)| S4
    S4 -->|repair results artifact| S5
    S5 -->|final approval| End

    subgraph "Control Plane"
        A[Manifest & evidence records]
    end
    A -.-> S1
    A -.-> S2
    A -.-> S3
    A -.-> S4
    A -.-> S5
```

This diagram emphasizes that **each arrow is a *persistent, versioned* artifact** (not an in-memory value).  The control plane (bottom) underpins all stages with a single source of truth.

## 9. PR Review / S5 Verification Checklist

When the PR for `icarus-recovery-2026-09` is reviewed and S5 performs independent verification, use the following checklist:

- **Provenance audit:** Every entry in the control manifests (`state.json`, handoff packet, claim/evidence files) has a clear timestamp, source ID, and commit SHA【17†L232-L240】【20†L268-L270】. If any is missing, reject.
- **Behavioral parity:** With all test mutations applied, the **final outputs** (e.g. signals, P&L) must match the original reported values.  The PR should not change default strategy behavior (non-research modes) at all. 
- **Test oracle integrity:** Confirm that the ablation/mutation tests added **fail** on the injected faults. Document that equivalence mutants are considered. (This ensures our test suite is not vacuously passing.)  
- **Authority gates:** Check that any uncertain or missing evidence in the manifest does **not** move a claim to APPROVED.  Only claims with full required tests are advanced.  
- **No synthetic data confounds:** Ensure no fake market bars or future data were introduced as “evidence.” All analysis must use real historical data sources.  
- **Immutable logging:** Verify that audit records (in `control/evidence/`) would satisfy an audit: each contains actor, input hash, model versions, outputs, verdicts and timestamps (as in ISO 42001 guidance)【20†L268-L270】.  
- **Failure handling:** Confirm that any test failure or missing data is clearly flagged; the PR should not gloss over a missing piece.  
- **Documentation completeness:** The `coordination/README.md` and agent guides should clearly list the new files, branches, and their intended use. 

Once these pass, merging the PR will enact the recovery: future S4/S5 stages can safely build on this persistent foundation.

## References

- Standardize AI workflows: MLflow describes an **Assess/Define/Pilot/Scale** roadmap and metadata contracts (context endpoint, model registry, audit records) for reliable pipelines【17†L218-L224】【20†L235-L242】.  
- Ablation studies: Remove components to measure impact on performance, ensuring “graceful degradation”【26†L120-L124】【26†L140-L144】.  
- Mutation testing: Introduce small code/data changes to ensure tests catch faults; a mutant is “killed” if tests fail【15†L260-L264】.  
- Immutable evidence: Audit logs and evidence records should capture actor, input, model version, output, verdict, and timestamp【17†L232-L240】【20†L268-L270】. This is key to reproducibility and compliance.  

(Additional sources: organizational best practices like ISO/IEC 42001 for AI audit readiness【20†L268-L270】, and MLflow’s production patterns【20†L268-L270】【20†L235-L242】.)