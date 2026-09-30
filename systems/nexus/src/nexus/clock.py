from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping
from .contracts import StreamManifest
from .ingest import BarClockPolicy


class ClockPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class RepresentationClockRule:
    representation_class: str
    timestamp_semantics: str  # open | close | event | unknown
    cadence_mode: str = "manifest"  # manifest | variable | explicit
    explicit_cadence_ns: int | None = None
    availability_delay_ns: int = 0
    reviewed: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        if (
            not isinstance(self.representation_class,str)
            or not self.representation_class.strip()
            or self.representation_class != self.representation_class.strip()
        ):
            raise ClockPolicyError("representation_class must be a non-empty trimmed string")
        if type(self.reviewed) is not bool:
            raise ClockPolicyError("reviewed must be bool")
        if not isinstance(self.notes,str):
            raise ClockPolicyError("notes must be a string")
        if self.timestamp_semantics not in {"open", "close", "event", "unknown"}:
            raise ClockPolicyError(f"unknown timestamp_semantics: {self.timestamp_semantics}")
        if self.cadence_mode not in {"manifest", "variable", "explicit"}:
            raise ClockPolicyError(f"unknown cadence_mode: {self.cadence_mode}")
        if type(self.availability_delay_ns) is not int or self.availability_delay_ns < 0:
            raise ClockPolicyError("availability_delay_ns must be a non-negative integer")
        if self.explicit_cadence_ns is not None and (
            type(self.explicit_cadence_ns) is not int or self.explicit_cadence_ns <= 0
        ):
            raise ClockPolicyError("explicit_cadence_ns must be a positive integer or None")
        if self.cadence_mode == "explicit" and self.explicit_cadence_ns is None:
            raise ClockPolicyError("explicit cadence_mode requires explicit_cadence_ns")
        if self.timestamp_semantics == "open" and self.cadence_mode == "variable":
            raise ClockPolicyError("open-stamped bars cannot use variable cadence")

    def visible_ns(self, source_timestamp_ns: int, manifest: StreamManifest) -> int:
        """Return the earliest reviewed visibility instant for a source timestamp.

        Event-driven representations use their event-completion timestamp directly;
        open-stamped fixed bars are delayed by the reviewed cadence.
        """
        if not self.reviewed:
            raise ClockPolicyError(
                f"representation {self.representation_class!r} is not reviewed; refusing to invent availability"
            )
        if type(source_timestamp_ns) is not int or source_timestamp_ns < 0:
            raise ClockPolicyError("source_timestamp_ns must be a non-negative integer")
        if not isinstance(manifest,StreamManifest):
            raise TypeError("manifest must be StreamManifest")
        t = source_timestamp_ns
        delay = self.availability_delay_ns
        if self.timestamp_semantics == "open":
            if self.cadence_mode == "manifest":
                cadence = manifest.observed_cadence_ns
            elif self.cadence_mode == "explicit":
                cadence = self.explicit_cadence_ns
            else:
                cadence = None
            if cadence is None or cadence <= 0:
                raise ClockPolicyError("open-stamped time bars require reviewed positive cadence")
            return t + cadence + delay
        if self.timestamp_semantics in {"close", "event"}:
            return t + delay
        raise ClockPolicyError(
            f"representation {self.representation_class!r} has unknown timestamp semantics"
        )

    def to_bar_policy(self, manifest: StreamManifest) -> BarClockPolicy:
        if not self.reviewed:
            raise ClockPolicyError(
                f"representation {self.representation_class!r} is not reviewed; refusing to invent availability"
            )
        if self.timestamp_semantics not in {"open", "close"}:
            raise ClockPolicyError(
                f"representation {self.representation_class!r} is not a fixed OHLC bar clock"
            )
        if self.cadence_mode == "manifest":
            cadence = manifest.observed_cadence_ns
        elif self.cadence_mode == "explicit":
            cadence = self.explicit_cadence_ns
        elif self.cadence_mode == "variable":
            cadence = None
        else:
            raise ClockPolicyError(f"unknown cadence_mode: {self.cadence_mode}")
        if self.timestamp_semantics == "open" and (cadence is None or cadence <= 0):
            raise ClockPolicyError("open-stamped fixed bars require reviewed positive cadence")
        return BarClockPolicy(
            source_stamp=self.timestamp_semantics,
            cadence_ns=cadence,
            availability_delay_ns=self.availability_delay_ns,
            basis="verified_bar_close",
        )


class ClockPolicyRegistry:
    """Reviewed clock semantics keyed by representation class.

    The registry is intentionally conservative. Variable-cadence charts, tick/volume bars,
    macro releases and authenticated event feeds require their own event/availability logic;
    they are not coerced into a fixed bar cadence.
    """

    def __init__(self):
        self._rules: dict[str, RepresentationClockRule] = {}

    def register(self, rule: RepresentationClockRule) -> None:
        if not isinstance(rule,RepresentationClockRule):
            raise TypeError("rule must be RepresentationClockRule")
        old = self._rules.get(rule.representation_class)
        if old is not None and old != rule:
            raise ClockPolicyError(
                f"immutable clock-policy conflict for {rule.representation_class}; version the representation instead"
            )
        self._rules[rule.representation_class] = rule

    def get(self, representation_class: str) -> RepresentationClockRule | None:
        return self._rules.get(representation_class)

    def bar_policy(self, representation_class: str, manifest: StreamManifest) -> BarClockPolicy:
        rule = self.get(representation_class)
        if rule is None:
            raise ClockPolicyError(f"no reviewed clock policy for {representation_class}")
        return rule.to_bar_policy(manifest)

    def snapshot(self) -> Mapping[str, RepresentationClockRule]:
        return dict(self._rules)
