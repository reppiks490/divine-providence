import pytest

from prometheus_loop.provenance import build_research_provenance_manifest


def _build(**overrides):
    values = dict(
        loop_run_id="loop:1",
        experiment_id="experiment:1",
        candidate_id="candidate:1",
        selected_plugin_descriptor_ids=("plugin:z", "plugin:a"),
        plugin_evidence_ids=("plugin-evidence:z", "plugin-evidence:a"),
        plugin_contribution_ids=("plugin-contribution:z", "plugin-contribution:a"),
        observation_ids=("observation:2", "observation:1"),
        source_contract_ids=("nexus-contract:2", "nexus-contract:1"),
        parent_manifest_ids=("research-provenance:2", "research-provenance:1"),
    )
    values.update(overrides)
    return build_research_provenance_manifest(**values)


def test_manifest_canonicalizes_identifier_order_and_is_deterministic():
    first = _build()
    second = _build(
        selected_plugin_descriptor_ids=("plugin:a", "plugin:z"),
        plugin_evidence_ids=("plugin-evidence:a", "plugin-evidence:z"),
        plugin_contribution_ids=("plugin-contribution:a", "plugin-contribution:z"),
        observation_ids=("observation:1", "observation:2"),
        source_contract_ids=("nexus-contract:1", "nexus-contract:2"),
        parent_manifest_ids=("research-provenance:1", "research-provenance:2"),
    )

    assert first == second
    assert first.artifact_id == second.artifact_id
    assert first.selected_plugin_descriptor_ids == ("plugin:a", "plugin:z")
    assert first.plugin_evidence_ids == ("plugin-evidence:a", "plugin-evidence:z")
    assert first.observation_ids == ("observation:1", "observation:2")
    assert first.artifact_id.startswith("research-provenance:")


@pytest.mark.parametrize(
    "field,value",
    [
        ("selected_plugin_descriptor_ids", ("plugin:a", "plugin:a")),
        ("plugin_evidence_ids", ("plugin-evidence:a", "plugin-evidence:a")),
        ("plugin_contribution_ids", ("plugin-contribution:a", "plugin-contribution:a")),
        ("observation_ids", ("observation:1", "observation:1")),
        ("source_contract_ids", ("nexus-contract:1", "nexus-contract:1")),
        ("parent_manifest_ids", ("research-provenance:1", "research-provenance:1")),
    ],
)
def test_manifest_rejects_duplicate_identifier_collections(field, value):
    with pytest.raises(ValueError, match="duplicate"):
        _build(**{field: value})


@pytest.mark.parametrize("field", ["loop_run_id", "experiment_id", "candidate_id"])
def test_manifest_rejects_empty_required_scalar_identity(field):
    with pytest.raises(ValueError, match=field):
        _build(**{field: ""})


def test_manifest_requires_observation_evidence():
    with pytest.raises(ValueError, match="observation"):
        _build(observation_ids=())


def test_manifest_rejects_plugin_evidence_cardinality_drift():
    with pytest.raises(ValueError, match="plugin provenance cardinality"):
        _build(plugin_evidence_ids=("plugin-evidence:a",))


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("loop_run_id", "candidate:not-a-loop", "loop_run_id"),
        ("experiment_id", "candidate:not-an-experiment", "experiment_id"),
        ("candidate_id", "experiment:not-a-candidate", "candidate_id"),
        ("selected_plugin_descriptor_ids", ("plugin-evidence:not-a-descriptor", "plugin:z"), "selected_plugin_descriptor_ids"),
        ("plugin_evidence_ids", ("plugin:not-evidence", "plugin-evidence:z"), "plugin_evidence_ids"),
        ("plugin_contribution_ids", ("plugin-evidence:not-contribution", "plugin-contribution:z"), "plugin_contribution_ids"),
        ("observation_ids", ("candidate:not-observation", "observation:2"), "observation_ids"),
        ("parent_manifest_ids", ("candidate:not-parent", "research-provenance:2"), "parent_manifest_ids"),
    ],
)
def test_manifest_rejects_wrong_identifier_namespaces(field, value, error):
    with pytest.raises(ValueError, match=error):
        _build(**{field: value})

from prometheus_loop.attestation import PluginAttestationPolicy


def test_manifest_binds_attestation_policy_and_canonical_external_evidence_ids():
    manifest = _build(
        parent_manifest_ids=(),
        external_attestation_ids=("external-attestation:z", "external-attestation:a"),
        attestation_verification_ids=("attestation-verification:z", "attestation-verification:a"),
        plugin_attestation_policy=PluginAttestationPolicy.OPTIONAL,
    )
    assert manifest.external_attestation_ids == ("external-attestation:a", "external-attestation:z")
    assert manifest.attestation_verification_ids == (
        "attestation-verification:a",
        "attestation-verification:z",
    )
    assert manifest.plugin_attestation_policy is PluginAttestationPolicy.OPTIONAL
    assert manifest.artifact_id != _build(parent_manifest_ids=()).artifact_id


def test_manifest_strict_policy_requires_attestation_coverage_for_every_selected_plugin():
    with pytest.raises(ValueError, match="strict attestation cardinality"):
        _build(
            parent_manifest_ids=(),
            external_attestation_ids=("external-attestation:a",),
            attestation_verification_ids=("attestation-verification:a",),
            plugin_attestation_policy=PluginAttestationPolicy.REQUIRE_VERIFIED,
        )


def test_manifest_optional_policy_rejects_attestation_receipt_count_drift_or_overcoverage():
    with pytest.raises(ValueError, match="attestation.*receipt cardinality"):
        _build(
            parent_manifest_ids=(),
            external_attestation_ids=("external-attestation:a",),
            attestation_verification_ids=(),
        )
    with pytest.raises(ValueError, match="attestation coverage exceeds"):
        _build(
            parent_manifest_ids=(),
            external_attestation_ids=("external-attestation:a", "external-attestation:b", "external-attestation:c"),
            attestation_verification_ids=("attestation-verification:a", "attestation-verification:b", "attestation-verification:c"),
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("external_attestation_ids", ("plugin-evidence:not-attestation",)),
        ("attestation_verification_ids", ("external-attestation:not-verification",)),
    ],
)
def test_manifest_rejects_wrong_attestation_identifier_namespaces(field, value):
    kwargs = {
        "parent_manifest_ids": (),
        "external_attestation_ids": ("external-attestation:a",),
        "attestation_verification_ids": ("attestation-verification:a",),
    }
    kwargs[field] = value
    with pytest.raises(ValueError, match=field):
        _build(**kwargs)
