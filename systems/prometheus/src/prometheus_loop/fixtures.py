from __future__ import annotations

from .contracts import ObservationEnvelope
from .plugins import PluginDescriptor


def sample_observations() -> tuple[ObservationEnvelope, ...]:
    instant = "2026-09-24T15:00:00Z"
    return (
        ObservationEnvelope(
            sibling="NEXUS",
            decision_instant=instant,
            availability_state="KNOWN",
            evidence_tier="CAUSAL_FABRIC",
            dimensions=(("confidence", "0.74"), ("direction", "bullish"), ("regime", "transition")),
            source_ref="nexus:fixture:1",
        ),
        ObservationEnvelope(
            sibling="ATHENA",
            decision_instant=instant,
            availability_state="KNOWN",
            evidence_tier="SUPERVISORY",
            dimensions=(("confidence", "0.43"), ("direction", "bearish"), ("regime", "transition")),
            source_ref="athena:fixture:1",
        ),
        ObservationEnvelope(
            sibling="ARGUS",
            decision_instant=instant,
            availability_state="KNOWN",
            evidence_tier="CANDLE_PROXY_FIXTURE",
            dimensions=(("confidence", "0.58"), ("direction", "bullish")),
            source_ref="argus:fixture:1",
        ),
    )


def sample_plugins() -> tuple[PluginDescriptor, ...]:
    return (
        PluginDescriptor(
            plugin_id="deep-research",
            display_name="Deep Research",
            capabilities=("deep_research", "web_research"),
            benefit_tags=("research", "architecture", "validation"),
        ),
        PluginDescriptor(
            plugin_id="exa",
            display_name="Exa",
            capabilities=("web_research",),
            benefit_tags=("research", "sources", "architecture"),
        ),
        PluginDescriptor(
            plugin_id="gmail",
            display_name="Gmail",
            capabilities=("email",),
            benefit_tags=("email", "inbox"),
        ),
    )


def sample_candidate_profile(**overrides):
    profile = {
        "uses_future": False,
        "ablation_stable": True,
        "perturbation_stable": True,
        "missingness_safe": True,
        "replay_hashes": ("fixture-hash", "fixture-hash"),
    }
    profile.update(overrides)
    return profile
