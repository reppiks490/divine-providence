# ICARUS research institution

Open the [live ICARUS dashboard](https://icarus-observatory-live-490.cloudyrook1.chatgpt.site)
and choose Research. Daily operation needs no chat, download, API key, paid model,
or manual setup. GitHub schedules can run late; the dashboard shows actual cycle
timestamps and incomplete evidence explicitly.

The workflow `.github/workflows/icarus-institution.yml` runs at **06:17 UTC daily**,
on relevant main changes, and on manual dispatch. It discovers the current Git
revisions of the two owned public CSV repositories, inventories full archive
members, and tests two unseen byte/protocol contexts per cycle. Sources outside
the registered 1,200–60,000-row/12MB member budget are deferred. Whole files stay
intact; no tail sampling, reordering, or chart-to-execution conversion occurs.

DAEDALUS builds lagged predictors and reserves its existing protected tail. Its
four model families compete on five purged walk-forward development folds.
The registered challenges include circular-shift controls (199), moving-block
bootstrap (199), costs at 1×/2×/5× the 1.5bps proxy assumption, three time slices,
and a fixed logistic return-family ablation. The winner is selected on the same
development evidence used by these diagnostics. Selection, serial dependence,
and cross-source multiplicity prevent interpreting a pass as confirmed alpha.
The five folds cover the existing validator's early expanding development
windows, not the entire historical stream. All exact fold positions are recorded.

ORACLE generates typed hypotheses with explicit falsification criteria and
builds the evidence graph. Cross-source diagnostics use development prefixes,
unique exact shared timestamps, and past row lags 0–3; they record insufficient
alignment instead of coercing chart timestamps. Their Spearman/BH associations
are exploratory, not causal or execution evidence. Announcement questions use official Fed, ECB, and SEC
RSS receipts. Source publication time and first observation time remain separate.
Announcement effects stay **untested** until contemporaneously available price
evidence and an appropriate event-study protocol exist. The coordinator does not
claim actual ChatGPT plugin calls from Python or GitHub Actions.

Memory stores negative results, watch entries, source-quality rejections, and
interrupted attempts. Identical source bytes plus scientific code/configuration,
dependency versions, and Python minor version identify a context. Resolved
contexts are skipped; interruption retries stop after three attempts. The memory
capacity is 4,096 contexts and fails closed instead of discarding failures.
After the queue is exhausted, the loop watches changed source bytes and new
announcements and reports its idle state. Historical watch entries remain
historical; the loop does not claim live paper executions or live degradation
tracking without current price data.

The other ICARUS departments keep their existing owners and contracts. The
Observatory continues to verify all twelve systems. The institution currently
exercises DAEDALUS and ORACLE scientific contracts; it does not represent every
department's engineering check as research participation. Protected acceptance,
production promotion, execution authorization, broker access, and live engine
state remain outside this coordinator's authority.

## Intelligence APIs

The repository is public, so these evidence APIs are public data. The hosted
dashboard retains its existing private audience. No source CSVs or credentials
are republished. Source manifests identify reusable data by repo revision,
archive member, and SHA256; download/access remains governed by the source repo.

Base URL: `https://raw.githubusercontent.com/reppiks490/divine-providence/research-history/`

| Path | Evidence |
| --- | --- |
| `latest.json` | Current run, registered context, full development diagnostics |
| `last_complete.json` | Last complete cycle, preserved across incomplete runs |
| `memory.json` | Durable source/protocol outcomes and observed announcements |
| `graph.json` | ORACLE nodes and provenance relationships |
| `hypotheses.json` | Exploratory associations and untested event questions |
| `leaderboard.json` | Model-family metrics, source/context identity and outcome |
| `datasets.json` | Tested source manifests and corpus/feed receipts |
| `view.json` | Current HTML byte hash and run binding for the hosted viewer |
| `brief.md` | Evidence-backed daily research brief |
| `runs/<run-id>-<attempt>.json` | Last 90 cycle receipts |

JSON envelopes have versioned schemas, SHA256 content hashes, and explicit false
execution/production/holdout authority. Publication regenerates views from sealed
data and verifies the Actions run via GitHub. The read-only collector never gets
the publication token. The trusted-main writer uses allowed data paths and a
non-force reference update, checks the prior memory identity, and preserves
memory after a lost artifact. History is parsed as JSON, never executed.

Local developer verification: `python -m pytest tests/test_institution.py`.
The protocol is recorded in `scripts/institution/common.py`; changing it creates
a new scientific context. The first two official corpus revisions inspected for
this build were `a482e7d1801fa7fa5aec093960097c0051c0403c` and
`ce82124352762c14eb33836a5c894bc3a2a71dfe`; 408 unique byte sources met the row and
member budgets. This is a budgeted subset, not a claim that the rest is invalid.
