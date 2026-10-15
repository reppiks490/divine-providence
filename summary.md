# ICARUS Observatory

**HEALTHY** · [Actions run](https://github.com/reppiks490/divine-providence/actions/runs/38737538074)

Source: `bcd35a480716035d5ffd65835d9b1e9c86cc8dd4` · Finished: 2026-10-15T12:50:42&#43;00:00

Engineering fixtures only. Live engine: not observed. Execution and production authority: false.

Receipt: `8954153236ca928ddb244833aac56d513b1f11d824e482df90d1d56637279bbb`

## Changes since last complete run

- Installed environment changed; comparisons are descriptive.

### Measurement changes

Count and duration changes are descriptive, not proof of regression.

- hub/tests seconds: 22.272 → 22.726
- suite/aegis seconds: 1.32 → 1.3
- suite/argus seconds: 2.62 → 2.58
- suite/ascension seconds: 0.7 → 0.72
- suite/athena seconds: 0.35 → 0.34
- suite/daedalus seconds: 22.23 → 22.51
- suite/infrastructure seconds: 2.83 → 2.82
- suite/janus seconds: 20.57 → 20.36
- suite/nexus seconds: 11.04 → 11.19
- suite/oracle seconds: 1.49 → 1.51
- suite/prometheus seconds: 0.94 → 0.95
- suite/supermesh_x seconds: 2.73 → 2.66

## Evidence

| Check | State | Passed tests | Seconds |
|---|---|---:|---:|
| adversarial/failure_injection_v0_1.py | pass | not recorded | not recorded |
| adversarial/failure_injection_v0_4.py | pass | not recorded | not recorded |
| adversarial/hostile_test_v0_8.py | pass | not recorded | not recorded |
| adversarial/property_test_v0_7.py | pass | not recorded | not recorded |
| adversarial/property_test_v0_8.py | pass | not recorded | not recorded |
| compile/aegis | pass | not recorded | not recorded |
| compile/aion | pass | not recorded | not recorded |
| compile/argus | pass | not recorded | not recorded |
| compile/ascension | pass | not recorded | not recorded |
| compile/athena | pass | not recorded | not recorded |
| compile/daedalus | pass | not recorded | not recorded |
| compile/infrastructure | pass | not recorded | not recorded |
| compile/janus | pass | not recorded | not recorded |
| compile/nexus | pass | not recorded | not recorded |
| compile/oracle | pass | not recorded | not recorded |
| compile/prometheus | pass | not recorded | not recorded |
| compile/supermesh_x | pass | not recorded | not recorded |
| connection/argus-athena-research | pass | not recorded | not recorded |
| connection/argus-bootstrap-athena-research | pass | not recorded | not recorded |
| connection/argus-impact-athena-research | pass | not recorded | not recorded |
| connection/intelligence-fabric | pass | not recorded | not recorded |
| connection/nexus-contract-drift | pass | not recorded | not recorded |
| connection/nexus-oracle | pass | not recorded | not recorded |
| connection/nexus-prometheus | pass | not recorded | not recorded |
| connection/nexus-siblings | pass | not recorded | not recorded |
| connection/prometheus-ascension | pass | not recorded | not recorded |
| connection/supermesh-witness | pass | not recorded | not recorded |
| hub/tests | pass | 165 | 22.726 |
| suite/aegis | pass | 36 | 1.3 |
| suite/aion | pass | 37 | 1.55 |
| suite/argus | pass | 447 | 2.58 |
| suite/ascension | pass | 160 | 0.72 |
| suite/athena | pass | 18 | 0.34 |
| suite/daedalus | pass | 64 | 22.51 |
| suite/infrastructure | pass | 345 | 2.82 |
| suite/janus | pass | 144 | 20.36 |
| suite/nexus | pass | 366 | 11.19 |
| suite/oracle | pass | 39 | 1.51 |
| suite/prometheus | pass | 171 | 0.95 |
| suite/supermesh_x | pass | 352 | 2.66 |

## Findings


**adversarial/failure_injection_v0_1.py**

&#123;&#34;ok&#34;: true&#44; &#34;output&#34;: &#34;&#123;&#39;structural_deletions_rejected&#39;: 1000&#44; &#39;adapter_deletions_not_ready&#39;: 1000&#44; &#39;digest_corruptions_rejected&#39;: 750&#44; &#39;identity_substitutions_rejected&#39;: 750&#44; &#39;backend_substitutions_not_ready&#39;: 500&#44; &#39;receipt_attacks_rejected&#39;: 500&#44; &#39;secret_injections_rejected&#39;: 300&#44; &#39;malformed_fail_closed&#39;: 500&#44; &#39;backend_digest_substitutions_not_ready&#39;: 500&#44; &#39;policy_digest_substitutions_not_ready&#39;: 500&#44; &#39;attestation_shape_corruptions_not_ready&#39;: 500&#125;&#92;nTOTAL_ATTACK_CASES 6800&#34;&#125;

**adversarial/failure_injection_v0_4.py**

&#123;&#34;ok&#34;: true&#44; &#34;output&#34;: &#34;BACKEND_SUBSTITUTIONS_REJECTED&#61;500/500&#92;nPINNED_POLICY_SUBSTITUTIONS_REJECTED&#61;500/500&#92;nSTRICT_INCLUSION_NODE_MUTATIONS_REJECTED&#61;500/500&#92;nFALSE_INDEX_RELABELS_REJECTED&#61;500/500&#92;nWITNESS_MUTATIONS_REJECTED&#61;400/400&#92;nMALFORMED_INPUTS_FAIL_CLOSED_SAFE_FOR_SIBLINGS&#61;300/300&#92;nDEPENDENCY_DIGEST_CONTRACT_SUBSTITUTIONS_REJECTED&#61;500/500&#92;nPROVENANCE_DELETIONS_DETECTED&#61;26/26&#92;nTOTAL_ATTACKS&#61;3226&#34;&#125;

**adversarial/hostile_test_v0_8.py**

&#123;&#34;ok&#34;: true&#44; &#34;output&#34;: &#34;ORDER_ATTACKS_REJECTED&#61;500&#92;nBAD_NODE_LENGTHS_REJECTED&#61;500&#92;nMALFORMED_TOP_LEVEL_FAIL_CLOSED&#61;500&#34;&#125;

**adversarial/property_test_v0_7.py**

&#123;&#34;ok&#34;: true&#44; &#34;output&#34;: &#34;&#123;&#39;valid_transitions&#39;: 2016&#44; &#39;max_proof_nodes&#39;: 7&#44; &#39;mutated_proofs_rejected&#39;: 1000&#125;&#34;&#125;

**adversarial/property_test_v0_8.py**

&#123;&#34;ok&#34;: true&#44; &#34;output&#34;: &#34;VALID_INCLUSIONS&#61;8256&#92;nMAX_PROOF_NODES&#61;7&#92;nMUTATED_NODES_REJECTED&#61;1500&#92;nGEOMETRY_ATTACKS_REJECTED&#61;1000&#92;nBINDING_ATTACKS_REJECTED&#61;1000&#92;nV06_FALSE_INDEX_RELABELS_ACCEPTED&#61;42&#92;nV08_FALSE_INDEX_RELABELS_REJECTED&#61;42&#34;&#125;

**compile/aegis**

&#123;&#34;errors&#34;: &#34;&#92;n&#34;&#44; &#34;ok&#34;: true&#44; &#34;stderr_tail&#34;: &#34;&#34;&#125;

**compile/aion**

&#123;&#34;errors&#34;: &#34;&#92;n&#34;&#44; &#34;ok&#34;: true&#44; &#34;stderr_tail&#34;: &#34;&#34;&#125;

**compile/argus**

&#123;&#34;errors&#34;: &#34;&#92;n&#34;&#44; &#34;ok&#34;: true&#44; &#34;stderr_tail&#34;: &#34;&#34;&#125;

**compile/ascension**

&#123;&#34;errors&#34;: &#34;&#92;n&#34;&#44; &#34;ok&#34;: true&#44; &#34;stderr_tail&#34;: &#34;&#34;&#125;

**compile/athena**

&#123;&#34;errors&#34;: &#34;&#92;n&#34;&#44; &#34;ok&#34;: true&#44; &#34;stderr_tail&#34;: &#34;&#34;&#125;

**compile/daedalus**

&#123;&#34;errors&#34;: &#34;&#92;n&#34;&#44; &#34;ok&#34;: true&#44; &#34;stderr_tail&#34;: &#34;&#34;&#125;

**compile/infrastructure**

&#123;&#34;errors&#34;: &#34;&#92;n&#34;&#44; &#34;ok&#34;: true&#44; &#34;stderr_tail&#34;: &#34;&#34;&#125;

**compile/janus**

&#123;&#34;errors&#34;: &#34;&#92;n&#34;&#44; &#34;ok&#34;: true&#44; &#34;stderr_tail&#34;: &#34;&#34;&#125;

**compile/nexus**

&#123;&#34;errors&#34;: &#34;&#92;n&#34;&#44; &#34;ok&#34;: true&#44; &#34;stderr_tail&#34;: &#34;&#34;&#125;

**compile/oracle**

&#123;&#34;errors&#34;: &#34;&#92;n&#34;&#44; &#34;ok&#34;: true&#44; &#34;stderr_tail&#34;: &#34;&#34;&#125;

**compile/prometheus**

&#123;&#34;errors&#34;: &#34;&#92;n&#34;&#44; &#34;ok&#34;: true&#44; &#34;stderr_tail&#34;: &#34;&#34;&#125;

**compile/supermesh_x**

&#123;&#34;errors&#34;: &#34;&#92;n&#34;&#44; &#34;ok&#34;: true&#44; &#34;stderr_tail&#34;: &#34;&#34;&#125;

**connection/argus-athena-research**

&#123;&#34;administrative_censored&#34;: 1&#44; &#34;argus&#34;: &#123;&#34;advisory_only&#34;: true&#44; &#34;available_ns&#34;: 310&#44; &#34;event_time_ns&#34;: 300&#44; &#34;input_evidence_tiers&#34;: &#91;&#34;TRUE_DEPTH&#34;&#93;&#125;&#44; &#34;athena&#34;: &#123;&#34;abstain_required&#34;: false&#44; &#34;admitted_events&#34;: 1&#44; &#34;event_id&#34;: &#34;4e36aebb769bcd69e1c589e83163d9fd1c3d007be09ba06f073ed3f224a41bb8&#34;&#44; &#34;frame_id&#34;: &#34;ea3c6d74adbe42b5f60737adede48d0904019ff02b110aafaea2faf6c0097b83&#34;&#44; &#34;ingestion_time_ns&#34;: 320&#44; &#34;receipt_time_gated&#34;: true&#125;&#44; &#34;censored&#34;: 2&#44; &#34;cohort_id&#34;: &#34;order-block-cohort:87759ca898fd09166ab9f1a0a0ab82e773254526b60284eb2dec11746f10f59b&#34;&#44; &#34;confidence_alpha&#34;: 0.05&#44; &#34;confidence_level&#34;: 0.95&#44; &#34;connection&#34;: &#34;argus-&#62;athena-research&#34;&#44; &#34;contract&#34;: &#34;ARGUS argus-orderblock-study-v2 registered survival uncertainty -&#62; ATHENA receipt-time research advisory&#34;&#44; &#34;contract_version&#34;: &#34;argus-athena-research-v1&#34;&#44; &#34;execution_authorized&#34;: false&#44; &#34;invalidations&#34;: 1&#44; &#34;lineage_id&#34;: &#34;argus-research:60076109dbc70b48c4dee2ed503dde1bb86182516b6040371124fe429b5885a6&#34;&#44; &#34;manifest_id&#34;: &#34;order-block-study:fb5d522fe5199571077fc5645ca8809f4d6e2e781322048401db7e3eb2dccbfb&#34;&#44; &#34;name&#34;: &#34;argus-athena-research&#34;&#44; &#34;ok&#34;: true&#44; &#34;production_authorized&#34;: false&#44; &#34;production_decision_authorized&#34;: false&#44; &#34;records&#34;: 3&#44; &#34;study_schema_version&#34;: &#34;argus-orderblock-study-v2&#34;&#125;

**connection/argus-bootstrap-athena-research**

&#123;&#34;argus&#34;: &#123;&#34;available_ns&#34;: 270&#44; &#34;bootstrap_replicates&#34;: 200&#44; &#34;broker_confirmed_observations&#34;: 0&#44; &#34;confidence_level&#34;: 0.95&#44; &#34;event_time_ns&#34;: 250&#44; &#34;hypothesis_test&#34;: false&#44; &#34;multiplicity_adjusted&#34;: false&#44; &#34;paper_emulator_observations&#34;: 2&#44; &#34;paper_only_fixture&#34;: true&#44; &#34;simultaneous_coverage&#34;: false&#44; &#34;study_lock_time_ns&#34;: 260&#125;&#44; &#34;athena&#34;: &#123;&#34;abstain_required&#34;: false&#44; &#34;admitted_events&#34;: 1&#44; &#34;event_id&#34;: &#34;cebfb8a20aae858aef77869bac5fdcbe27f6c89602a740673baf267e6c473c64&#34;&#44; &#34;frame_id&#34;: &#34;4c0b23066e21693178d1f68f683e8d49b1f63240c3bdcd75473d038e4f388418&#34;&#44; &#34;ingestion_time_ns&#34;: 280&#44; &#34;receipt_time_gated&#34;: true&#125;&#44; &#34;bootstrap_plan_id&#34;: &#34;impact-calibration-bootstrap-plan:04a5cc1943810d05ab372604037fc324fda50188bbb337e928f43f988dbf9a7b&#34;&#44; &#34;bootstrap_plan_schema_version&#34;: &#34;argus-impact-calibration-bootstrap-plan-v1&#34;&#44; &#34;cohort_id&#34;: &#34;impact-calibration-cohort:cf25177600ef72c19eac6c6a7e71500f67d58af844ea8a165708772e8a473093&#34;&#44; &#34;connection&#34;: &#34;argus-bootstrap-athena-research&#34;&#44; &#34;contract&#34;: &#34;ARGUS argus-impact-calibration-bootstrap-plan-v1 registered descriptive uncertainty -&#62; ATHENA receipt-time research advisory&#34;&#44; &#34;contract_version&#34;: &#34;argus-impact-calibration-uncertainty-research-v1&#34;&#44; &#34;execution_authorized&#34;: false&#44; &#34;lineage_id&#34;: &#34;argus-impact-uncertainty-research:a1fdc447914a4232ea924f908338d7d3754f66c10503fb2f69ac2a63f654bc5b&#34;&#44; &#34;manifest_id&#34;: &#34;impact-calibration-study:6aa15d3bcee6ff95bb07b74fc8ea22bf3dcde7d32e6e356721c1e209968b713b&#34;&#44; &#34;name&#34;: &#34;argus-bootstrap-athena-research&#34;&#44; &#34;ok&#34;: true&#44; &#34;production_authorized&#34;: false&#44; &#34;production_decision_authorized&#34;: false&#44; &#34;study_schema_version&#34;: &#34;argus-impact-calibration-study-v1&#34;&#125;

**connection/argus-impact-athena-research**

&#123;&#34;argus&#34;: &#123;&#34;available_ns&#34;: 270&#44; &#34;broker_confirmed_observations&#34;: 0&#44; &#34;event_time_ns&#34;: 250&#44; &#34;paper_emulator_observations&#34;: 1&#44; &#34;paper_only_fixture&#34;: true&#44; &#34;study_lock_time_ns&#34;: 260&#125;&#44; &#34;athena&#34;: &#123;&#34;abstain_required&#34;: false&#44; &#34;admitted_events&#34;: 1&#44; &#34;event_id&#34;: &#34;8d35b333f518d505fde6725d1673926672adb3ef9e9346ebe999071ca4796664&#34;&#44; &#34;frame_id&#34;: &#34;76923f7dfebb2351a0f7567fa9c4956bb81969860f35000bfc30135cd216e152&#34;&#44; &#34;ingestion_time_ns&#34;: 280&#44; &#34;receipt_time_gated&#34;: true&#125;&#44; &#34;calibration_revision&#34;: &#34;argus-impact-calibration-v1&#34;&#44; &#34;cohort_id&#34;: &#34;impact-calibration-cohort:373e26b9471a562aee85d839635b7919a1e841450c80acf743618617e25450cf&#34;&#44; &#34;connection&#34;: &#34;argus-impact-athena-research&#34;&#44; &#34;contract&#34;: &#34;ARGUS argus-impact-calibration-study-v1 registered evidence-stratified calibration -&#62; ATHENA receipt-time research advisory&#34;&#44; &#34;contract_version&#34;: &#34;argus-impact-calibration-research-v1&#34;&#44; &#34;execution_authorized&#34;: false&#44; &#34;impact_model_revision&#34;: &#34;argus-depth-impact-v1&#34;&#44; &#34;lineage_id&#34;: &#34;argus-impact-research:bab62423f880751b0fc1c42e7f051dca1efa91e26848023bc20275ae8ab11404&#34;&#44; &#34;manifest_id&#34;: &#34;impact-calibration-study:fbbf7d3b732e9873e510c12b00a4560441c3662efc3a92a3c79eec894db0edaf&#34;&#44; &#34;name&#34;: &#34;argus-impact-athena-research&#34;&#44; &#34;ok&#34;: true&#44; &#34;production_authorized&#34;: false&#44; &#34;production_decision_authorized&#34;: false&#44; &#34;study_schema_version&#34;: &#34;argus-impact-calibration-study-v1&#34;&#125;

**connection/intelligence-fabric**

&#123;&#34;aion&#34;: &#123;&#34;chain_verified&#34;: true&#44; &#34;events&#34;: 3&#44; &#34;frame_hash&#34;: &#34;53261c1d07d13a85a03a74b5c52a5e06383d4ba54451747fc9c61255f5327435&#34;&#125;&#44; &#34;argus&#34;: &#123;&#34;features&#34;: 1&#44; &#34;proxy_only&#34;: true&#125;&#44; &#34;athena&#34;: &#123;&#34;abstain_required&#34;: false&#44; &#34;events&#34;: 1&#44; &#34;frame_id&#34;: &#34;febf847d6a2263998f2afa4e264328f2094919a0437307a3c887bd43913d64fe&#34;&#44; &#34;receipt_time_gated&#34;: true&#125;&#44; &#34;bundle_hash&#34;: &#34;738ca0867d14aa1e48c6d8753a9c4e6f9b5d7876a263c35fc1a310db33c76344&#34;&#44; &#34;connection&#34;: &#34;nexus-&#62;aion/parallax-&#62;argus/athena&#34;&#44; &#34;contract&#34;: &#34;NEXUS SiblingInstantBundle -&#62; AION EventStore/PARALLAX fingerprint -&#62; ARGUS evidence firewall &#43; ATHENA receipt-time journal&#34;&#44; &#34;decision_ns&#34;: 160&#44; &#34;execution_authorized&#34;: false&#44; &#34;name&#34;: &#34;intelligence-fabric&#34;&#44; &#34;ok&#34;: true&#44; &#34;parallax&#34;: &#123;&#34;axes&#34;: 3&#44; &#34;fingerprint_id&#34;: &#34;4c2992028ddca84d545757607c40dc6a707c41e00847b6faff0cdca39ee76b73&#34;&#44; &#34;future_axes&#34;: 0&#125;&#44; &#34;production_authorized&#34;: false&#125;

**connection/nexus-contract-drift**

&#123;&#34;baseline_snapshot_hash&#34;: &#34;65cba148bc5df86bd4b660ba15b14e6c58c113fa00fecdf3e22ea745a13ffe9a&#34;&#44; &#34;connection&#34;: &#34;nexus-contract-drift&#34;&#44; &#34;contract&#34;: &#34;nexus.contract-drift-snapshot.v1 vs pinned path-independent v1.16 baseline 65cba148... &#40;v1.15 and v0.3 retained historically&#41;&#34;&#44; &#34;current_snapshot_hash&#34;: &#34;65cba148bc5df86bd4b660ba15b14e6c58c113fa00fecdf3e22ea745a13ffe9a&#34;&#44; &#34;items&#34;: &#91;&#123;&#34;role&#34;: &#34;contracts&#34;&#44; &#34;sibling&#34;: &#34;AION&#34;&#44; &#34;status&#34;: &#34;unchanged&#34;&#125;&#44; &#123;&#34;role&#34;: &#34;store&#34;&#44; &#34;sibling&#34;: &#34;AION&#34;&#44; &#34;status&#34;: &#34;unchanged&#34;&#125;&#44; &#123;&#34;role&#34;: &#34;contracts&#34;&#44; &#34;sibling&#34;: &#34;ARGUS&#34;&#44; &#34;status&#34;: &#34;unchanged&#34;&#125;&#44; &#123;&#34;role&#34;: &#34;contracts&#34;&#44; &#34;sibling&#34;: &#34;ATHENA&#34;&#44; &#34;status&#34;: &#34;unchanged&#34;&#125;&#44; &#123;&#34;role&#34;: &#34;bridge&#34;&#44; &#34;sibling&#34;: &#34;DAEDALUS&#34;&#44; &#34;status&#34;: &#34;unchanged&#34;&#125;&#93;&#44; &#34;name&#34;: &#34;nexus-contract-drift&#34;&#44; &#34;ok&#34;: true&#44; &#34;raw_drift&#34;: false&#44; &#34;semantic_drift&#34;: false&#44; &#34;vs_v03_release&#34;: &#123;&#34;baseline_snapshot_hash&#34;: &#34;1119ef3d9b561dc89668a9768893a2b1ab09cd542ffd1d7a02dd73f5a81388a2&#34;&#44; &#34;items&#34;: &#91;&#123;&#34;role&#34;: &#34;contracts&#34;&#44; &#34;sibling&#34;: &#34;AION&#34;&#44; &#34;status&#34;: &#34;semantic_change&#34;&#125;&#44; &#123;&#34;role&#34;: &#34;store&#34;&#44; &#34;sibling&#34;: &#34;AION&#34;&#44; &#34;status&#34;: &#34;semantic_change&#34;&#125;&#44; &#123;&#34;role&#34;: &#34;contracts&#34;&#44; &#34;sibling&#34;: &#34;ARGUS&#34;&#44; &#34;status&#34;: &#34;unchanged&#34;&#125;&#44; &#123;&#34;role&#34;: &#34;contracts&#34;&#44; &#34;sibling&#34;: &#34;ATHENA&#34;&#44; &#34;status&#34;: &#34;unchanged&#34;&#125;&#44; &#123;&#34;role&#34;: &#34;bridge&#34;&#44; &#34;sibling&#34;: &#34;DAEDALUS&#34;&#44; &#34;status&#34;: &#34;semantic_change&#34;&#125;&#93;&#125;&#44; &#34;vs_v115&#34;: &#123;&#34;baseline_snapshot_hash&#34;: &#34;b394df6cf80ddbac014f4024222469b169178fadd7c26f4a597aed58671b5bb3&#34;&#44; &#34;items&#34;: &#91;&#123;&#34;role&#34;: &#34;contracts&#34;&#44; &#34;sibling&#34;: &#34;AION&#34;&#44; &#34;status&#34;: &#34;semantic_change&#34;&#125;&#44; &#123;&#34;role&#34;: &#34;store&#34;&#44; &#34;sibling&#34;: &#34;AION&#34;&#44; &#34;status&#34;: &#34;semantic_change&#34;&#125;&#44; &#123;&#34;role&#34;: &#34;contracts&#34;&#44; &#34;sibling&#34;: &#34;ARGUS&#34;&#44; &#34;status&#34;: &#34;unchanged&#34;&#125;&#44; &#123;&#34;role&#34;: &#34;contracts&#34;&#44; &#34;sibling&#34;: &#34;ATHENA&#34;&#44; &#34;status&#34;: &#34;unchanged&#34;&#125;&#44; &#123;&#34;role&#34;: &#34;bridge&#34;&#44; &#34;sibling&#34;: &#34;DAEDALUS&#34;&#44; &#34;status&#34;: &#34;unchanged&#34;&#125;&#93;&#125;&#125;

**connection/nexus-oracle**

&#123;&#34;connection&#34;: &#34;nexus-&#62;oracle&#34;&#44; &#34;contract&#34;: &#34;nexus.market-state.v2 -&#62; oracle.nexus_ingest MetricObservation -&#62; FinancialState&#34;&#44; &#34;expected_features&#34;: &#123;&#34;factors.market_state&#34;: 0.25&#44; &#34;ood.novelty&#34;: 0.1&#44; &#34;quality.coverage&#34;: 1.0&#44; &#34;topology.entropy&#34;: 0.5&#125;&#44; &#34;financial_state_features&#34;: &#123;&#34;factors.market_state&#34;: 0.25&#44; &#34;ood.novelty&#34;: 0.1&#44; &#34;quality.coverage&#34;: 1.0&#44; &#34;topology.entropy&#34;: 0.5&#125;&#44; &#34;name&#34;: &#34;nexus-oracle&#34;&#44; &#34;observations&#34;: 4&#44; &#34;ok&#34;: true&#44; &#34;packet_contract&#34;: &#34;nexus.market-state.v2&#34;&#125;

**connection/nexus-prometheus**

&#123;&#34;accepted&#34;: true&#44; &#34;bundle_hash&#34;: &#34;738ca0867d14aa1e48c6d8753a9c4e6f9b5d7876a263c35fc1a310db33c76344&#34;&#44; &#34;connection&#34;: &#34;nexus-&#62;prometheus&#34;&#44; &#34;contract&#34;: &#34;SiblingInstantBundle -&#62; prometheus_loop.adapters.nexus -&#62; normalize_nexus_bundle &#40;pinned NEXUS contract identity&#41;&#34;&#44; &#34;contract_identity&#34;: &#34;65cba148bc5df86bd4b660ba15b14e6c58c113fa00fecdf3e22ea745a13ffe9a&#34;&#44; &#34;decision_ns&#34;: 160&#44; &#34;drifted_boundaries&#34;: &#91;&#93;&#44; &#34;identity_pinned_by_prometheus&#34;: true&#44; &#34;link_state&#34;: &#34;LINKED&#34;&#44; &#34;name&#34;: &#34;nexus-prometheus&#34;&#44; &#34;observations&#34;: &#91;&#123;&#34;evidence_tier&#34;: &#34;NEXUS_MARKET_STATE&#34;&#44; &#34;sibling&#34;: &#34;NEXUS&#34;&#125;&#44; &#123;&#34;evidence_tier&#34;: &#34;CANDLE_PROXY&#34;&#44; &#34;sibling&#34;: &#34;ARGUS&#34;&#125;&#44; &#123;&#34;evidence_tier&#34;: &#34;ATHENA_STATE_INPUT&#34;&#44; &#34;sibling&#34;: &#34;ATHENA&#34;&#125;&#44; &#123;&#34;evidence_tier&#34;: &#34;RESEARCH_CANDIDATE_ONLY&#34;&#44; &#34;sibling&#34;: &#34;DAEDALUS&#34;&#125;&#93;&#44; &#34;ok&#34;: true&#44; &#34;semantic_drift_vs_current_baseline&#34;: false&#125;

**connection/nexus-siblings**

&#123;&#34;connection&#34;: &#34;nexus-&#62;siblings&#34;&#44; &#34;contract&#34;: &#34;NEXUS SiblingInstantRouter -&#62; AION EventStore / ARGUS MicrostructureFeature / ATHENA Provenance / DAEDALUS bridge&#34;&#44; &#34;name&#34;: &#34;nexus-siblings&#34;&#44; &#34;ok&#34;: true&#44; &#34;result&#34;: &#123;&#34;aion&#34;: true&#44; &#34;argus&#34;: true&#44; &#34;athena&#34;: true&#44; &#34;daedalus&#34;: true&#44; &#34;details&#34;: &#123;&#34;aion&#34;: &#34;same-instant bar &#43; derivation &#43; source-health schemas passed&#59; EventStore append/asof/hash-chain persisted genealogy&#34;&#44; &#34;argus&#34;: &#34;same-instant MicrostructureFeature CANDLE_PROXY routing passed&#34;&#44; &#34;athena&#34;: &#34;same-instant Provenance &#43; source-health routing passed without WorldState ownership&#34;&#44; &#34;daedalus&#34;: &#34;same-instant research-candidate bridge exact-shape passed&#34;&#125;&#44; &#34;passed&#34;: true&#125;&#125;

**connection/prometheus-ascension**

&#123;&#34;artifact_sha256&#34;: &#34;abd572e4c36b0b7df4613f40a31810b0c7d51db2c79df9516604014d53caaba2&#34;&#44; &#34;ascension_status&#34;: &#34;STRUCTURALLY_CONFORMANT&#34;&#44; &#34;authenticated&#34;: false&#44; &#34;conformant&#34;: true&#44; &#34;connection&#34;: &#34;prometheus-&#62;ascension&#34;&#44; &#34;contract&#34;: &#34;PROMETHEUS strict runtime ResearchProvenanceManifest -&#62; exact byte-bound handoff -&#62; ASCENSION Sibling Manifest Conformance Kit v0.1&#34;&#44; &#34;execution_authorized&#34;: false&#44; &#34;name&#34;: &#34;prometheus-ascension&#34;&#44; &#34;ok&#34;: true&#44; &#34;plugin_evidence_id&#34;: &#34;plugin-evidence:bdf38fd4cee3831d7f7456c5f32d5bc6a4c0f9087ad933009a961f90b87e7f44&#34;&#44; &#34;production_decision_authorized&#34;: false&#44; &#34;provenance_manifest_id&#34;: &#34;research-provenance:abd572e4c36b0b7df4613f40a31810b0c7d51db2c79df9516604014d53caaba2&#34;&#44; &#34;ready_for_adapter_v0_4&#34;: false&#44; &#34;reasons&#34;: &#91;&#93;&#44; &#34;runtime_export_generated&#34;: true&#44; &#34;runtime_fixture_kind&#34;: &#34;deterministic_internal_contract_fixture&#34;&#44; &#34;transfer&#34;: &#34;BLOCKED: exact PROMETHEUS runtime bytes now cross the structural handoff&#44; but ASCENSION-authorized trust policy&#44; cryptographic verification material&#44; collision verdict&#44; strict inclusion proof&#44; and independent witness/transition evidence are still required&#34;&#44; &#34;warnings&#34;: &#91;&#34;cryptographic_authenticity_not_established&#34;&#44; &#34;transfer_not_verified&#34;&#93;&#125;

**connection/supermesh-witness**

&#123;&#34;authority&#34;: &#34;witness receipts authenticate checkpoint evidence only&#59; no execution/write/trading authority&#34;&#44; &#34;connection&#34;: &#34;nexus-&#62;supermesh-witness&#34;&#44; &#34;contract&#34;: &#34;NEXUS SiblingInstantBundle &#43; pinned contract baseline -&#62; SuperMesh-X RFC9162WitnessedCheckpointLedger -&#62; GossipReceiptStore&#34;&#44; &#34;gossip_verified&#34;: true&#44; &#34;log_id&#34;: &#34;divine-providence/nexus-artifacts&#34;&#44; &#34;name&#34;: &#34;supermesh-witness&#34;&#44; &#34;negative_controls&#34;: &#123;&#34;history_rewrite_rejected&#34;: &#34;RFC9162 consistency verification failed&#34;&#44; &#34;rollback_rejected&#34;: &#34;rollback&#34;&#125;&#44; &#34;nexus_bundle_hash&#34;: &#34;738ca0867d14aa1e48c6d8753a9c4e6f9b5d7876a263c35fc1a310db33c76344&#34;&#44; &#34;ok&#34;: true&#44; &#34;root&#34;: &#34;4ac13acc1441f4cf2920799c2e333afbdfb33ccd731a63ab454290c115471986&#34;&#44; &#34;tree_size&#34;: 2&#44; &#34;witness_quorum&#34;: 2&#125;

**hub/tests**

&#123;&#34;counts&#34;: &#123;&#34;passed&#34;: 165&#125;&#44; &#34;passed&#34;: true&#44; &#34;returncode&#34;: 0&#44; &#34;seconds&#34;: 22.726&#44; &#34;stderr_tail&#34;: &#34;&#34;&#44; &#34;stdout_tail&#34;: &#34;........................................................................ &#91; 43&#37;&#93;&#92;n........................................................................ &#91; 87&#37;&#93;&#92;n.....................                                                    &#91;100&#37;&#93;&#92;n165 passed in 21.82s&#92;n&#34;&#44; &#34;timed_out&#34;: false&#125;

**suite/aegis**

&#123;&#34;counts&#34;: &#123;&#34;passed&#34;: 36&#125;&#44; &#34;passed&#34;: true&#44; &#34;seconds&#34;: 1.3&#44; &#34;tail&#34;: &#34;&#34;&#44; &#34;timed_out&#34;: false&#125;

**suite/aion**

&#123;&#34;counts&#34;: &#123;&#34;passed&#34;: 37&#125;&#44; &#34;passed&#34;: true&#44; &#34;seconds&#34;: 1.55&#44; &#34;tail&#34;: &#34;&#34;&#44; &#34;timed_out&#34;: false&#125;

**suite/argus**

&#123;&#34;counts&#34;: &#123;&#34;passed&#34;: 447&#125;&#44; &#34;passed&#34;: true&#44; &#34;seconds&#34;: 2.58&#44; &#34;tail&#34;: &#34;&#34;&#44; &#34;timed_out&#34;: false&#125;

**suite/ascension**

&#123;&#34;counts&#34;: &#123;&#34;passed&#34;: 160&#125;&#44; &#34;passed&#34;: true&#44; &#34;seconds&#34;: 0.72&#44; &#34;tail&#34;: &#34;&#34;&#44; &#34;timed_out&#34;: false&#125;

**suite/athena**

&#123;&#34;counts&#34;: &#123;&#34;passed&#34;: 18&#125;&#44; &#34;passed&#34;: true&#44; &#34;seconds&#34;: 0.34&#44; &#34;tail&#34;: &#34;&#34;&#44; &#34;timed_out&#34;: false&#125;

**suite/daedalus**

&#123;&#34;counts&#34;: &#123;&#34;passed&#34;: 64&#125;&#44; &#34;passed&#34;: true&#44; &#34;seconds&#34;: 22.51&#44; &#34;tail&#34;: &#34;&#34;&#44; &#34;timed_out&#34;: false&#125;

**suite/infrastructure**

&#123;&#34;counts&#34;: &#123;&#34;passed&#34;: 345&#125;&#44; &#34;passed&#34;: true&#44; &#34;seconds&#34;: 2.82&#44; &#34;tail&#34;: &#34;&#34;&#44; &#34;timed_out&#34;: false&#125;

**suite/janus**

&#123;&#34;counts&#34;: &#123;&#34;passed&#34;: 144&#125;&#44; &#34;passed&#34;: true&#44; &#34;seconds&#34;: 20.36&#44; &#34;tail&#34;: &#34;&#34;&#44; &#34;timed_out&#34;: false&#125;

**suite/nexus**

&#123;&#34;counts&#34;: &#123;&#34;passed&#34;: 366&#125;&#44; &#34;passed&#34;: true&#44; &#34;seconds&#34;: 11.19&#44; &#34;tail&#34;: &#34;&#34;&#44; &#34;timed_out&#34;: false&#125;

**suite/oracle**

&#123;&#34;counts&#34;: &#123;&#34;passed&#34;: 39&#125;&#44; &#34;passed&#34;: true&#44; &#34;seconds&#34;: 1.51&#44; &#34;tail&#34;: &#34;&#34;&#44; &#34;timed_out&#34;: false&#125;

**suite/prometheus**

&#123;&#34;counts&#34;: &#123;&#34;passed&#34;: 171&#125;&#44; &#34;passed&#34;: true&#44; &#34;seconds&#34;: 0.95&#44; &#34;tail&#34;: &#34;&#34;&#44; &#34;timed_out&#34;: false&#125;

**suite/supermesh_x**

&#123;&#34;counts&#34;: &#123;&#34;passed&#34;: 352&#125;&#44; &#34;passed&#34;: true&#44; &#34;seconds&#34;: 2.66&#44; &#34;tail&#34;: &#34;&#34;&#44; &#34;timed_out&#34;: false&#125;
