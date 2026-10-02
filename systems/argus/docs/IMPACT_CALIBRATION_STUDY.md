# ARGUS prospective impact-calibration studies

ARGUS now has a prospective study contract for its realized-fill impact
calibration layer.

The implementation lives in `argus.impact_calibration_study`.

## Purpose

The raw calibration layer can measure how a static `TRUE_DEPTH` displayed-book
impact baseline differed from later realized execution evidence.

The study layer answers a different question:

> Which executions, model revisions, evidence classes, timing limits and
> analysis were committed before the sample began?

That distinction is required to prevent retrospective filtering from being
mistaken for prospective validation.

## Manifest

`argus-impact-calibration-study-v1` content-addresses:

- study name;
- manifest creation time;
- cohort decision-time start and end;
- observation cutoff;
- impact-model revision;
- calibration-code revision;
- symbols;
- allowed execution-evidence classes;
- exact execution-source repository/commit revisions;
- minimum observations required in every declared evidence stratum;
- maximum impact-snapshot age, when configured;
- maximum completion latency, when configured;
- predeclared analysis plan.

The manifest must be created at or before the cohort starts.

Execution source commits are exact 40-character Git SHAs. This prevents a study
from silently mixing fills produced by a source adapter revision selected after
results are visible.

## Time semantics

Three times remain distinct:

1. **Decision time** determines whether an execution belongs to the cohort.
2. **Observed time** determines whether the completed execution evidence was
   available by the predeclared observation cutoff.
3. **Lock time** is when the cohort is frozen for analysis.

A cohort cannot be locked before the observation cutoff.

This prevents an early partial sample from being frozen simply because its
interim results look favorable.

## Subjects

Each study subject binds:

- one content-addressed execution-evidence receipt;
- one content-addressed impact-calibration lineage record;
- the exact impact-model revision;
- the exact calibration revision.

The underlying execution receipt still preserves the distinction between:

- `BROKER_CONFIRMED`;
- `ICARUS_PAPER_EMULATOR`.

The safe study path never promotes paper-emulator evidence into broker evidence.

## Inclusion and exclusions

A subject is included only when all predeclared conditions match.

Deterministic exclusion reasons include:

- impact-model revision mismatch;
- calibration revision mismatch;
- symbol outside the manifest;
- execution-evidence class outside the manifest;
- execution-source repository/commit mismatch;
- decision before the cohort;
- decision at/after the cohort end;
- execution evidence observed after cutoff;
- impact snapshot older than the predeclared maximum;
- completion latency above the predeclared maximum.

Exclusion lineage IDs and reasons are included in the content-addressed cohort
identity.

Duplicate calibration lineage IDs fail closed.

More importantly, the same execution receipt cannot be counted twice against
two different impact curves in one study. Duplicate execution receipts also
fail closed.

The cohort additionally requires upstream source-execution identity to be
unique. Broker-confirmed evidence uses broker name + broker order ID + broker
fill ID + symbol, while ICARUS paper evidence uses source system + source run ID
+ source execution ID + symbol. Adapter repository/commit remain mandatory
provenance pinned by the study manifest, but they do not manufacture a second
execution identity. Two distinct content-addressed receipts that claim the same
upstream execution therefore fail closed instead of being counted twice.

## Minimum evidence per stratum

Every evidence class declared in the manifest must meet the predeclared minimum
observation count before the cohort can lock.

For example, a study declaring both broker-confirmed and paper-emulator strata
cannot complete with only paper observations.

This avoids presenting a missing comparison group as though the prospective
design had been satisfied.

## Registered analysis

The first registered analysis is:

- `evidence_stratified_summary`

It delegates to the existing safe execution-evidence aggregation path, which
keeps broker-confirmed and paper-emulator calibration summaries separate.

The study does not pool those evidence classes.

## Tamper resistance

The manifest and cohort are content-addressed.

The cohort identity includes:

- manifest ID;
- lock time;
- included calibration lineage IDs;
- included impact/calibration revisions;
- deterministic exclusion records;
- broker-confirmed count;
- paper-emulator count.

Before registered analysis, ARGUS revalidates:

- manifest identity;
- cohort identity;
- execution-receipt identity;
- receipt-plus-calibration lineage identity;
- model/calibration revisions;
- source repository/commit provenance;
- upstream source-execution uniqueness independent of adapter revision;
- symbol/evidence class;
- cohort timing;
- observation cutoff;
- latency/snapshot limits;
- stratum minimums;
- authority flags.

## Interpretation boundary

A completed prospective calibration study is stronger evidence than a
retrospective convenience sample, but it is still calibration evidence.

It does not by itself establish:

- profitable trading;
- causal alpha;
- future fill quality;
- adequate sample size for every statistical claim;
- queue-position realism;
- hidden-liquidity realism;
- smart-order-routing quality;
- production execution safety.

Those require separate prospective protocols and, where appropriate,
broker-confirmed evidence.

## Authority

`execution_authorized=false`

`production_decision_authorized=false`

Neither a successful study nor broker-confirmed historical evidence authorizes a
new order.
