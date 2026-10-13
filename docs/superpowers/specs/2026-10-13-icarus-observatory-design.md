# ICARUS Observatory design

Date: 2026-10-13  
Status: proposed; requires written design review before implementation  
Repository: `reppiks490/divine-providence`  
Inspected source: `a4110b43ed61860fe1c46ba91bdfd99ed530d776`

## Intent and success

The owner requested something unique for the ICARUS system, implemented in
repository Actions, that runs continuously without requiring this chat. The
previously presented approach was a daily Observatory: twelve-system validation,
connection checks, regression history, a dashboard, evidence bundles, and one
persistent incident issue. The owner subsequently said "Try now."

Success means a recurring, bounded workflow produces a fresh, inspectable account
of engineering health and changes. Anyone can open the repository to understand
what passed, what failed, what was not checked, and what changed since the preceding
run. Each finding links to its source revision and Actions run. The workflow does
not depend on an AI subscription, this session, a broker, or external credentials.

The proposed differentiator is a **proof atlas**: a map of twelve subsystem suites,
compile gates, adversarial checks, and ten cross-system contracts, with histories
and per-finding receipts. It separates newly broken checks, continuing failures,
recoveries, inventory changes, and missing evidence. It reports which subsystems
participate in a failed connection; that is a dependency map, not a claim that one
subsystem caused another to fail.

## Evidence from the repository

- `registry.SYSTEMS` declares twelve subsystems and isolated import roots.
- `connections.CONNECTIONS` currently declares ten connections. The README's
  older count of six is not the inventory authority.
- `connections.coverage()` explicitly explains the standalone status of AEGIS,
  JANUS, and Infrastructure; the Observatory must preserve those distinctions.
- `python -m divine_providence.validate --workers 2` already runs every suite,
  compile checks, five ASCENSION adversarial scripts, and all connections.
- Root hub tests are separate: collection must also run
  `python -m pytest -q tests` and retain that exit code and test summary.
- `validate.main()` exits zero only when suites, compilation, adversarial checks,
  and connections pass. It writes `provenance/validation_report.json` after the
  phases finish. An exception before that point can leave no report.
- The existing `subsystem-evolution-tests.yml` uploads the report for fourteen
  days, warns if it is missing, and has no schedule. None of the four workflows
  inspected has a schedule.
- The latest main run inspected, [37239279246](https://github.com/reppiks490/divine-providence/actions/runs/37239279246),
  succeeded on 2026-10-04. Independent read-only review observed a full-validation
  step of approximately 47 seconds. This is an observed example, not a runtime
  guarantee. No new validation suite was run in this design-only change.

## Approaches considered

1. Add only a cron trigger to the existing validation. Smallest change, but it
   does not provide durable comparisons, explicit incomplete-run receipts, or an
   explanation of what changed.
2. Add an Observatory around existing validation. Recommended: preserve test
   authority while adding durable reporting, comparisons, and a proof atlas.
3. Add an autonomous AI code-changing agent. Deferred: that would introduce
   credentials, recurring inference costs, and a separate policy for changes to
   research and authority boundaries. It is unnecessary for this Observatory.

## Architecture and files

The Observatory is an observer around the current validator. Subsystem source,
test selections, contract baselines, and promotion policies remain owned by their
existing modules.

| Proposed path | Responsibility |
|---|---|
| `.github/workflows/icarus-observatory.yml` | Daily/main/manual collection and separate trusted publication jobs. |
| `scripts/observatory/collect.py` | Fresh run receipt, inventory capture, validator subprocess, timeout and log recording. |
| `scripts/observatory/report.py` | Strict report normalization, comparison, JSON/Markdown/HTML proof atlas and hashes. |
| `scripts/observatory/publish.py` | Publish validated reporting data to the history branch and update the single incident issue. |
| `tests/test_observatory.py` | Failure semantics, comparison, rendering, history, and mocked publication tests. |
| `docs/ICARUS_OBSERVATORY.md` | Operator guide, artifacts, scheduling limits, pause/recovery commands and incident ownership. |
| `README.md` | Link to the workflow and operator guide; describe the observed inventory accurately. |

Report generation and publication use the Python standard library. Collection
uses the hub's existing dependency set. No new runtime package is required.

### Collection

- Run daily at `17 4 * * *` (04:17 UTC), on relevant pushes to `main`, and by
  `workflow_dispatch`. GitHub may delay or skip scheduled runs; this is recurring
  verification, not an always-running server.
- Pull requests run Observatory tests and report generation against fixtures;
  they never publish history or issues. Full validation on the feature branch is
  required before activation. Existing validation workflows continue to operate.
- Use Ubuntu and Python 3.11, matching the current full-system validation job.
  Pin reusable action versions to verified commit SHAs during implementation.
  Record sorted installed package names/versions through package metadata, plus
  their fingerprint, to make dependency changes visible without retaining
  authenticated installation URLs.
- Use `contents: read` for collection, a sixty-minute job limit, a forty-five-minute
  validator limit, and two validator workers. Serialize scheduled/main/manual
  publication under one concurrency group with `cancel-in-progress: false`.
- Capture the expected system, connection, and ASCENSION-script inventories from
  the checked-out source. Capture connection coverage separately from pass/fail.
- Remove any old output before starting validation. Create a receipt before
  setup/validation and use an `always()` finalizer for ordinary failures.
- Run root hub tests and invoke the existing validator as subprocesses, preserve
  their separate exit codes, and
  save bounded stdout/stderr logs. Do not reinterpret nonzero exit as success.
- A trusted publication job runs with `always()` after collection. If no artifact
  survives an install failure, hard cancellation, or runner loss, it emits a
  workflow-level incomplete receipt from Actions job metadata if publication
  can run. Entire-workflow cancellation or a GitHub outage can prevent even
  this publisher from executing. It must never
  copy the previous run's report as the current result.
- Cloud Actions does not try to connect to the owner's localhost paper engine.
  Any live-engine state is explicitly `not_observed`.
- Contract drivers are local deterministic fixtures, not checks of live external
  providers. Preserve correct drift quarantine as failed connectivity with a
  visible successful safety refusal; never accept a new baseline automatically.

### Receipt and proof atlas

`icarus.observatory.run.v1` contains:

- `run_id`, `run_attempt`, `event`, source repository/ref/commit, canonical Actions
  URL, UTC start/finish timestamps, runner/Python identity, and validator exit code;
- expected inventory, normalized findings keyed by `suite/<system>`,
  `compile/<system>`, `adversarial/<script>`, and `connection/<name>`;
- a separate `hub/tests` finding and environment/dependency fingerprint;
- per-finding state `pass`, `fail`, or `not_observed`, counts, elapsed seconds,
  bounded diagnostic text, and affected subsystem names where declared;
- overall state `healthy`, `unhealthy`, or `incomplete`, and explicit reasons;
- `execution_authorized=false` and `production_authorized=false`;
- hashes for retained validation output, logs, and normalized findings.

Accept the validator's current native report shape: it has no schema discriminator.
Version only the Observatory envelope. Native compile, adversarial, and connection
records generally do not include test counts or elapsed time; use `null` and an
explicit `not_recorded` explanation for absent measurements rather than inventing
zeros. A workflow-level incomplete receipt similarly uses `null` for an unobserved
validator exit code. Keep native-report compatibility checks separate from strict
Observatory-envelope schema validation.

`healthy` requires passing root hub tests, a fresh parseable validation report,
validator exit zero,
exact expected inventories, strict boolean pass fields, matching aggregate
flags, and no failed or unobserved finding. Missing fields, contradictory flags,
invalid JSON, missing inventory members, and unrecognized schema are incomplete
evidence. A completed, structurally valid failing check is an unhealthy result.
Suite findings marked passing must have at least one passed test, no failed,
error, or deselected tests, and `timed_out=false`, matching `run_system_tests()`.
Skipped and expected-failure counts remain visible and are not converted to passes.
Timed-out checks remain visibly failed/timed-out; they are never counted as a
completed successful test. Passing engineering checks confer no trading edge
or execution authority.

Emit `run.json`, the original report when available, bounded logs, `summary.md`,
`index.html`, and `SHA256SUMS`. The self-contained HTML works when downloaded;
it needs no web service or external script. HTML and Markdown renderers escape
diagnostics, paths, and labels. Public output contains engineering metadata and
synthetic-test diagnostics only, not market-data exports or credentials.

Each finding includes its run/commit identity and the hash of its normalized
record. An aggregate content hash and the preceding receipt hash make edits and
gaps inspectable. These are integrity checks, not signatures, trusted-time
attestations, or protection against a maintainer rewriting the entire history.

### Durable comparisons

Persist generated data in a dedicated `observatory-history` branch. Never commit
reports to `main`. Retain the latest ninety normalized receipts, a compact index,
and the latest dashboard; retain full Actions evidence bundles for thirty days.
Retain the most recent complete receipt separately as `last_complete.json`, even
if it ages out of the ninety-receipt window. This preserves an actual comparison
baseline after a prolonged series of incomplete runs, not just its identity.

Compare findings with the preceding complete published run. Show the immediately
preceding receipt separately, including incomplete runs and gaps. Distinguish:

- first observation: no prior baseline;
- regression: previously passing finding now fails;
- continuing failure: previously failing finding still fails;
- recovery: previously failing finding now passes;
- lost observation: a previously observed finding is missing or unobserved;
- inventory addition/removal: source inventory changed, shown explicitly;
- count/duration change: descriptive diagnostic, never a pass criterion itself.

A renamed or removed check cannot silently disappear from the comparison.
An incomplete run never overwrites the last complete baseline identity. Show
both the latest run and latest complete run in the dashboard.

Reject out-of-order publication from older Actions runs/attempts; allow idempotent
retry of the same run and attempt. Preserve predecessor metadata when pruning
retained receipts. Read history as data only, validate schema/size/path limits,
and never execute scripts from the history branch.

### Publication and incidents

The publisher is a separate job with only `contents: write` and `issues: write`,
using GitHub's repository token and `actions: read` for run metadata/artifacts.
The write-permission publisher is explicitly gated to
`github.ref == 'refs/heads/main'` and an event in `schedule`, `push`, or
`workflow_dispatch`. It checks out the exact validated main commit SHA as trusted
workflow source, not a selected non-main dispatch branch or PR head code.
Publication happens only for those trusted main runs.
PRs and forks cannot receive write permissions through this workflow.

Maintain one issue titled `ICARUS Observatory: current incident`, identified by
an exact marker in its body and its bot author. Create it on the first unhealthy
or incomplete run, update its body for subsequent runs, and close it after a
healthy run. Reopen that same bot-owned issue on recurrence. Do not edit an
unrelated issue, duplicate it each day, or add daily comments.

The issue links to the latest evidence, distinguishes new failures from ongoing
ones, and records whether publication itself succeeded. Publication failures
make the Actions run fail while leaving collection artifacts accessible. Write
permissions being disabled is an operational failure, not a healthy observation.

The initial activation requires landing the workflow on `main`. Confirm branch
rules and write-token permissions then; do not silently change repository
settings, protections, or billing. Disabling the workflow stops recurring runs.
For public repositories GitHub can disable schedules after inactivity; the guide
must describe re-enabling through the Actions UI and show last-observation age.
The HTML calculates last-observation age when opened and flags observations
older than forty-eight hours as stale. This reveals stale evidence to a viewer;
the Observatory cannot guarantee an alert when GitHub itself has stopped running.

## Validation and rollout criteria

1. Prove fresh-run handling with valid passing and failing validator reports,
   malformed/missing/truncated reports, stale files, contradictory booleans,
   missing inventory, subprocess timeout, and setup failure.
2. Prove comparison for initial baseline, regression, recovery, missing checks,
   source inventory changes, incomplete runs, and zero-test reports.
3. Prove safe rendering using HTML-like diagnostic text, Unicode, long logs,
   and unsafe paths; verify recorded hashes against emitted evidence.
4. Mock GitHub API publication to prove bot-owned issue selection, update/reopen/
   close behavior, retry idempotency, history ordering, retention, malformed
   history rejection, and denied permissions.
5. Check workflow syntax, event boundaries, minimum permissions, action pins,
   timeout/concurrency settings, artifact delivery after failure, and the absence
   of write-token exposure in PR jobs.
6. Run hub tests and the existing full validator on the feature branch. Review
   the first real evidence artifact before landing the change.
7. After activation, verify the initial main run, published history, incident
   behavior, and the next scheduled-run configuration. Activation alone cannot
   prove a future scheduled invocation occurred.

## Scope and review record

This document adds no implementation or scheduled execution. It records a
concrete design against the current repository and incorporates independent
read-only review of report shape, runtime, and failure semantics.

Assumptions selected for review: daily UTC cadence, ninety retained receipts,
thirty-day full artifacts, repository-based dashboard, and a single incident
issue. No inference budget or paid external service is assumed.

Following design approval, write an implementation plan against these exact
interfaces and review it before implementation. If repository structure,
validation schema, Actions token permissions, or authority boundaries change,
recheck the corresponding sections rather than treating this design as current.
