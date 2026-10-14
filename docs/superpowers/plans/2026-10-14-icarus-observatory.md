# ICARUS Observatory implementation plan

**Architecture:** standard-library collector and reporter wrap existing validation;
a separate main-only publisher writes durable evidence and the bot incident.
**Tech stack:** Python 3.11, pytest, pinned GitHub Actions, GitHub REST Git APIs.
**Execution:** parallel independent units, then fresh code review and one fix pass.

Goal: implement the approved daily proof atlas in `reppiks490/divine-providence`.
Spec: `docs/superpowers/specs/2026-10-13-icarus-observatory-design.md`.
Workspace: `/workspace/icarus-observatory`; interpreter `/workspace/icarus-venv/bin/python`.
Global constraints: stdlib observer; Python 3.11; no subsystem modifications;
separate collection/read and publication/write jobs; main-only publication;
90 receipts plus separately retained last complete baseline; 30-day artifacts;
daily 04:17 UTC; incomplete evidence never healthy.

## Shared interfaces

All code lives in `scripts/observatory/`; tests import `scripts.observatory.*`.
Collector and publisher use module CLI (`python -m scripts.observatory.collect`).
Root owns `report.py`, `__init__.py`, report tests, workflow, plan integration.

Collector output directory holds `collection.json`, `hub.json`, optional
`validation_report.json`, bounded `hub.stdout.log`, `hub.stderr.log`,
`validation.stdout.log`, `validation.stderr.log`. Metadata in `collection.json`:
schema=`icarus.observatory.collection.v1`; run_id/run_attempt integers;
event/repository/ref/commit/run_url strings; started_at/finished_at ISO UTC;
python/platform; validator_exit_code/hub_exit_code int or null;
validator_timed_out/hub_timed_out booleans; collection_errors string list;
dependencies=[{name,version}]; inventory={systems:[names],
connections:{name:{systems:[names],contract:string}}, adversarial:[script names],
coverage:connections.coverage()}. Native report is unchanged.
hub.json={returncode:int|null,timed_out:bool,counts:dict,seconds:number|null,
stdout_tail:string,stderr_tail:string}. Passing hub requires >0 passed,
no failed/errors/deselected, exit0/no timeout.

report.py provides:
- `canonical_bytes(value: object) -> bytes` deterministic sorted JSON.
- `seal_receipt(receipt: dict) -> dict` copies, recalculates finding hashes and
  receipt_hash; hash excludes the respective hash field itself.
- `normalize(collection: dict, native: dict|None, hub: dict|None) -> dict`;
  schema=`icarus.observatory.run.v1`, copies run metadata/inventory,
  state in healthy/unhealthy/incomplete, reasons:list, findings:dict,
  dependencies:list, environment_hash:string, evidence_hashes:dict,
  previous_receipt_hash:null, authority false, live_engine=`not_observed`.
- finding={id,state:pass/fail/not_observed,counts:dict|null,seconds:number|null,
  diagnostic:string,systems:list,run_id,commit,finding_hash}.
- `compare(current:dict, previous:dict|None) -> dict`: baseline_run_id,
  first_observation, regressions/continuing_failures/recoveries/
  lost_observations/inventory_added/inventory_removed lists of finding IDs,
  measurement_changes:list. New fail is added inventory + current failure;
  only pass-to-fail is regression; missing known check is visible.
- `write_bundle(receipt:dict, out:Path, baseline:dict|None=None,
  history:list|None=None) -> None` emits run.json/comparison.json/summary.md/
  index.html/SHA256SUMS; hashes every bounded existing evidence file and
  emits canonical hashes; no code from supplied data.
- CLI `--input DIR --output DIR`, reads collection/hub/native and always
  emits incomplete receipt on bad or missing input, exit0 when bundle written;
  `--enforce` exits1 unless run state healthy (separate gate after artifact).

Publisher uses `write_bundle`, `seal_receipt`, `compare`; supplies baseline.
It updates current receipt previous_receipt_hash before sealing. Verify input
schema/hashes/run identity; match environment repository, SHA, ref, run/attempt.
Data Git branch `observatory-history`: index.json, latest.json,
last_complete.json, runs/<run_id>-<attempt>.json, index.html, summary.md.
No package install and no execute from history. API uses GITHUB_TOKEN only
at publication CLI step; not passed to collector. Main/allowed-event guard
inside publisher as well as workflow. Use GitHub REST git blob/tree/commit/ref
APIs for branch updates with lease/no force; allowed data paths and size bounds.
Issue exact marker `<!-- icarus-observatory:incident:v1 -->` and bot author;
create on failure, update/reopen same issue, close after healthy, no comments.
Publishing failure nonzero; never mark collection healthy to bypass it.
CLI `--input DIR --output DIR` supports fallback if artifact absent using
trusted env/run metadata; no publication from PR/non-main. Root tests + actual
validator data prove report normalization.

## Tasks and verification

1. Collector: write behavioral tests for stale-output removal, setup receipt,
   timeout logs, inventory and root-test failures; observe RED; implement
   `collect.py`; observe GREEN. Own `tests/test_observatory_collect.py`.
2. Reporter: write tests for complete success/failure/missing data, strict bool,
   zero counts, inventories, conflicting flags, rendering/hashes/comparisons;
   observe RED; implement report.py; observe GREEN. Root owns this task.
3. Publisher: tests against a fake transport for lifecycle, ordering/retention,
   identity/bot guards, invalid hashes and API errors; RED then GREEN. Own
   `publish.py` and `tests/test_observatory_publish.py`.
4. Workflow/operator docs: fixtures/schema/pins/privilege and failure checks;
   run all hub tests and full twelve-system validation, fresh whole-code review;
   address findings with regression tests; update PR50 to final implementation.
5. Activation: merge only after passing checks and review within owner's
   instruction to install continuously-running repo Actions. Confirm main
   initial run, history branch, dashboard/evidence and recurring trigger.

Review focus: install failure before validator starts; workflow cancellation;
malformed history and authenticated publication data; source inventory changes;
manual dispatch on non-main and token exposure. Keep receipts on incomplete
runs and last complete baseline independent of retention. No new paid service.

Ruling: owner twice said Continue after written spec review request; execute
the reviewed design through activation, without another design permission loop.
Ruling: parallel work on collector/report/publisher, one fresh whole-code review;
all changes remain on isolated feature checkout until verified.

## Execution ledger

- [x] Collector:21 behavioral tests, including RED/GREEN zero-test rejection and
  refreshing the interpreter identity after setup. No subsystem source changed.
- [x] Reporter and workflow: strict native-report normalization, ambiguous JSON
  rejection, safe incomplete inventories, descriptive measurement/environment
  deltas, artifact-versus-history dashboard links. Review regression tests were
  observed failing before the corresponding fixes.
- [x] Publisher: fake-REST tests verify identity, evidence hashes, history
  ordering/retention/retries, bot issue lifecycle, permissions, malformed data,
  and complete test findings requiring counts and duration.
- [x] Integrated local validation:145 hub/Observatory tests,2168 subsystem tests,
  all ten connections, twelve compile gates and five adversarial scripts passed.
  Native validator and generated Observatory health gate both exited zero.
- [x] Actionlint1.7.7 and git whitespace checks passed. Action tag SHAs were
  verified against upstream Git references; runtime dependencies remain the
  existing hub manifest and are fingerprinted for each receipt.
- [ ] Browser checks of the generated dashboard and GitHub Actions activation.

Ruling: use a300-second hub timeout in Actions so the45-minute validator still
leaves setup/finalizer/artifact time within the60-minute collection job.
Ruling: independent reviewer reported material metadata, inventory, measurement,
and durable-link findings; fixes were verified with RED/GREEN tests. The reviewer
later hit the account usage limit before delivering a final review report; root
completed the remaining source review and integrated verification.
Ruling: repository branch-protection read returned403 from the integration;
available rulesets were empty. No policies were changed; normal PR merge will
enforce any server-side restrictions.
