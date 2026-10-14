# ICARUS Observatory operator guide

The Observatory runs bounded engineering verification in GitHub Actions without
depending on this chat. It observes the checked-out source and local deterministic
fixtures. It does not observe the owner's localhost paper engine or live external
providers: `live_engine=not_observed`, `execution_authorized=false`, and
`production_authorized=false`. A healthy receipt does not establish live-system
health, trading edge, promotion readiness, or execution authority.

## Open a run and its evidence

- [Live dashboard](https://icarus-observatory-live-490.cloudyrook1.chatgpt.site)
  loads the latest verified report and checks for updates every minute. It is
  hosted as an owner-private Site. Normal viewing needs no download, setup,
  manual refresh, or extra API key. GitHub Actions continues collecting and
  publishing evidence while the page is closed.
- [ICARUS Observatory Actions](https://github.com/reppiks490/divine-providence/actions/workflows/icarus-observatory.yml)
  lists scheduled, push, and manual runs. Open a run to inspect its collection and
  publication jobs, logs, commit, and artifacts.
- [Workflow source](../.github/workflows/icarus-observatory.yml) defines triggers,
  path filters, permissions, time limits, and artifact retention.
- [History branch](https://github.com/reppiks490/divine-providence/tree/observatory-history)
  holds published data. Open `latest.json` for the latest receipt,
  `last_complete.json` for the comparison baseline, and `index.json` for retained
  receipt navigation.
- [Latest dashboard file](https://github.com/reppiks490/divine-providence/blob/observatory-history/index.html)
  remains available as source and optional offline evidence. Use the live
  dashboard above for automatic viewing; GitHub's file viewer shows HTML source.
- [Incident search](https://github.com/reppiks490/divine-providence/issues?q=is%3Aissue+%22ICARUS+Observatory%3A+current+incident%22)
  finds the persistent bot-owned incident. Its body links to the relevant run and
  evidence. A matching title alone does not establish that the issue is managed.

Artifacts are optional for offline inspection or verifying hashes. Normal use
requires no artifact download. Artifact access follows the repository's normal
GitHub access rules.

The hosted viewer reads public `observatory-history/latest.json` and its matching
HTML without sending credentials. The report is sandboxed from the private
Site's origin. Temporary source failures retain the previous displayed report,
show a retry status, and recover automatically. The existing Actions publisher
remains the unattended data writer; observations need no Site republish. Hosting
identity is recorded in [observatory-dashboard.json](observatory-dashboard.json).

| Artifact | Purpose |
|---|---|
| `icarus-observatory-<run_id>-<attempt>` | Collection evidence and the initial report, available even when later publication fails. |
| `icarus-observatory-published-<run_id>-<attempt>` | Report rendered by the publisher with durable history, baseline comparisons, and GitHub evidence links. |

Both artifacts have a 30-day retention period. Publication can fail before the
published artifact exists; inspect the collection artifact and job logs in that
case. A missing artifact is missing evidence, not a successful observation.

Bundles include `run.json`, `comparison.json`, `summary.md`, `index.html`, and
`SHA256SUMS`, together with available native validation output, collection/hub
metadata, and bounded stdout/stderr logs. `SHA256SUMS` records retained evidence
hashes. Receipt and finding hashes support inspection of changes; they are not
signatures or protection against a maintainer rewriting all history.

## What is checked

The source inventories are authoritative: [registry.SYSTEMS](../src/divine_providence/registry.py),
[connections.CONNECTIONS and coverage()](../src/divine_providence/connections.py),
and [ASCENSION_SCRIPTS](../src/divine_providence/validate.py). The current inventory
contains 12 subsystem suites, 12 compile gates, five ASCENSION adversarial scripts,
10 local cross-system contract checks, and a separate hub-test finding.

Collection runs `python -m pytest -q tests` and
`python -m divine_providence.validate --workers 2` on Ubuntu with Python 3.11.
The Observatory preserves their separate exit codes and records installed
dependency versions and an environment fingerprint. Report generation and
publication use the Python standard library.

The connection map names the participating subsystems. It does not prove which
subsystem caused a failure. AEGIS, JANUS, and Infrastructure remain standalone
with the reasons supplied by `connections.coverage()`. Contract-drift quarantine
can demonstrate a successful safety refusal while the connection still fails;
the Observatory never accepts a replacement contract baseline automatically.

| Receipt state | Meaning |
|---|---|
| `healthy` | Fresh, complete, consistent evidence; hub tests and every expected finding pass, with validator exit zero. |
| `unhealthy` | Complete, structurally valid evidence contains a failing check. |
| `incomplete` | Evidence is missing, malformed, contradictory, interrupted, or otherwise insufficient to establish a complete result. |

Findings use `pass`, `fail`, or `not_observed`. Missing measurements are `null`
with an explanation; they are not invented zeros. Skips and expected failures
remain visible. Zero-test suites, deselected tests, timeouts, missing inventory
members, and inconsistent success flags cannot establish a healthy result.

## Cadence, history, and freshness

The workflow runs daily at **04:17 UTC** (`17 4 * * *`), on relevant pushes to
`main`, and through **Run workflow**. The workflow's path filters define relevant
pushes. Pull requests run the collection, including hub and subsystem checks,
and retain evidence artifacts; they do not publish history or incidents. Publication is allowed only for
`schedule`, `push`, or `workflow_dispatch` events on `refs/heads/main`.

Collection has a 60-minute job limit and a 45-minute validator limit. Publication
is serialized with cancellation of an in-progress publication disabled. A run is
a bounded verification job, not an always-running service. GitHub may delay or
skip scheduled invocations and may disable schedules in public repositories
after inactivity.

The `observatory-history` branch retains the latest **90 normalized receipts**,
not 90 days of full logs. Its data paths are `index.json`, `latest.json`,
`last_complete.json`, `runs/<run_id>-<attempt>.json`, `index.html`, and `summary.md`.
Full Actions evidence has the separate 30-day retention limit. Reports are never
committed to `main`.

Comparison uses the preceding complete published receipt, which may itself be
unhealthy. The last complete receipt is retained separately even when it ages
out of the 90-receipt window; incomplete runs do not replace it. The immediately
preceding receipt remains visible separately, including incomplete observations.
The dashboard distinguishes first observations, regressions, continuing failures,
recoveries, lost observations, inventory additions/removals, and descriptive
count/duration changes. A regression is a previously passing finding that now
fails. Older run/attempt publication is rejected; retries of the same identity
are idempotent.

When opened, the dashboard calculates observation age and flags evidence older
than **48 hours** as stale. Check the latest Actions run as well as the latest
published receipt: a publication failure can leave the dashboard behind the
collection evidence. The stale indicator reveals age to a viewer; it cannot
guarantee an alert if GitHub has stopped executing the workflow.

## Respond to failures and incomplete runs

1. Open the incident's Actions link, confirm the source commit, and inspect the
   receipt state and reasons before reading individual findings.
2. Inspect the collection artifact and bounded logs. Distinguish completed test
   failures from setup failures, timeouts, and missing or contradictory evidence.
3. If collection succeeded but publication failed, inspect the publisher log and
   existing history. Permission/API errors make the Actions run fail; they do
   not change collection into a healthy result.
4. Fix the underlying source or operational issue through the repository's normal
   process. Run the workflow on `main` again after the fix, then confirm the new
   receipt, history, and incident state.

The publisher maintains one issue titled **ICARUS Observatory: current incident**,
identified by the exact body marker `<!-- icarus-observatory:incident:v1 -->` and
its bot author. It creates the issue for an unhealthy or incomplete receipt,
updates its body on subsequent runs, closes it after a healthy run, and reopens
the same issue on recurrence. It adds no daily comments and does not edit
unrelated issues. Closing the issue manually does not repair failing evidence.

Ordinary failures use finalizers to preserve a receipt. If collection leaves no
artifact and the trusted publisher can still run, it emits an incomplete receipt
from Actions run metadata. Entire-workflow cancellation, runner loss, or a GitHub
outage can prevent that fallback and incident publication. The old report is
never substituted as current evidence. After an interruption, use the Actions
run status and a new main-branch run to establish a fresh observation.

## Stop, resume, or run now

To stop recurring execution, open the
[workflow's Actions page](https://github.com/reppiks490/divine-providence/actions/workflows/icarus-observatory.yml),
open its **…** menu, and select **Disable workflow**. Disabling future execution
does not erase retained evidence or guarantee cancellation of an active run.
To stop an active run, open that run and choose **Cancel workflow**; cancellation
can prevent final artifacts or publication, as described above.

To resume, open the disabled workflow and select **Enable workflow**. If GitHub
disabled it for inactivity, re-enable it through the same Actions UI. Then choose
**Run workflow**, select **main**, and submit a run to obtain immediate evidence.
Confirm its publication job and new history receipt. An initial successful run
does not prove that a future scheduled invocation has occurred; inspect the next
scheduled run when due.

For a transient failure, open the failed run and use GitHub's re-run control, or
dispatch a fresh run on `main`. A newer attempt receives its own receipt identity.
A dispatch from another branch cannot publish history or incidents. Re-running
an older source revision cannot overwrite a newer published observation.

## Permissions and change boundaries

The workflow needs no broker credentials, AI subscription, paid service, external
API key, or extra service account. Collection uses `contents: read`; the separate
trusted publisher uses the automatically supplied repository `GITHUB_TOKEN`
with `contents: write`, `issues: write`, and `actions: read`. The publisher checks
main/event/run identity and evidence hashes and uses the exact validated main
commit as trusted source. The write token is not passed to the collector. Pull
requests and forks do not receive publication permissions.

Authorized writes are limited to generated reporting data on
`observatory-history`, Actions artifacts, and the marked bot-owned incident issue.
History is read as bounded data, never executed as code. The observer does not
change subsystem code, test selections, contract baselines, authority policies,
repository settings, branch protections, or billing.

Activation requires the workflow to land on `main` and existing repository policy
to permit publication. If branch rules or token policy deny writes, retain the
failure evidence and resolve it with the repository owner; the Observatory does
not relax those settings automatically.
