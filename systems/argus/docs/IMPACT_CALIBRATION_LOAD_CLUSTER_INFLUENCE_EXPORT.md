# ARGUS load-cluster influence research export

The load-cluster influence audit has a transport-ready research envelope:

`argus-impact-calibration-load-cluster-influence-research-v1`.

The implementation lives in
`argus.impact_calibration_load_cluster_influence_research_export`.

## Export validation

Before publication, the exporter recomputes the registered influence audit.

That transitively revalidates:

- prospective study manifest and locked cohort;
- execution-evidence receipts;
- receipt-plus-calibration lineage;
- exact source revisions;
- load-cluster transfer plan;
- load bands, metrics and cluster minimums;
- influence-plan identity;
- leave-one-cluster shift tolerances;
- minimum clusters remaining after deletion;
- authority flags.

Publication cannot precede the locked cohort, and downstream local visibility
must still wait for ingestion time.

## Preserved lineage

The packet preserves:

- manifest ID;
- cohort ID;
- load-cluster transfer plan ID;
- influence-plan ID and schema;
- fixed cluster field `source_run_id`;
- load-band definitions;
- metric set;
- parent transfer plan's `min_clusters_per_kind_per_band`;
- influence plan's minimum remaining-cluster requirement, which cannot relax
  that parent cluster floor;
- parent transfer plan's `min_metric_observations_per_kind_per_band`, which
  every leave-one-run remainder must still satisfy;
- per-band/per-metric shift tolerances;
- exact model/calibration/source revisions;
- every influence result, including the worst evidence kind and source run;
- aggregate stability outcome.

The export lineage also binds source ID, representation ID, observation cutoff
and publication boundary.

## Explicit statistical boundary

The envelope states:

- `formal_influence_theorem=false`;
- `jackknife_confidence_interval=false`;
- `hypothesis_test=false`;
- `multiplicity_adjusted=false`;
- `causal_effect_estimate=false`;
- `paper_evidence_promoted=false`;
- `broker_substitution_authorized=false`.

The leave-one-run result is a deterministic fragility diagnostic, not a
confidence interval or proof of distributional equivalence.

## ATHENA integration status

The export is transport-ready, but the deterministic hub still lacks genuine
broker-confirmed execution evidence with externally valid lineage.

No ATHENA happy-path driver fabricates broker-confirmed runs merely to make the
integration appear complete.

Synthetic broker-confirmed records are confined to isolated contract tests and
are not emitted as empirical ATHENA evidence.

## Authority

`execution_authorized=false`

`production_authorized=false`

`production_decision_authorized=false`
