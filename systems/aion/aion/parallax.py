"""PARALLAX causal state fingerprints and historical analog retrieval.

Only information explicitly available by each decision time may enter a fingerprint.
The atlas is research-only: it retrieves earlier states and separately gated outcomes;
it does not emit orders or promote a model.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from statistics import median
from typing import Iterable


def _name(field: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{field} must be a non-empty trimmed string")
    return value


def _finite(value: float) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("axis values must be finite")
    return value


def _hash(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True)
class AxisObservation:
    axis: str
    value: float
    available_ns: int
    source_id: str
    representation_id: str
    lineage_id: str

    def __post_init__(self) -> None:
        _name("axis", self.axis)
        _finite(self.value)
        if type(self.available_ns) is not int or self.available_ns < 0:
            raise ValueError("available_ns must be non-negative")
        _name("source_id", self.source_id)
        _name("representation_id", self.representation_id)
        _name("lineage_id", self.lineage_id)


@dataclass(frozen=True)
class Fingerprint:
    decision_ns: int
    axes: tuple[AxisObservation, ...]
    fingerprint_id: str

    def __post_init__(self) -> None:
        if type(self.decision_ns) is not int or self.decision_ns < 0:
            raise ValueError("decision_ns must be non-negative")
        if not isinstance(self.axes, tuple) or not self.axes:
            raise ValueError("fingerprint requires at least one axis")
        names = [x.axis for x in self.axes]
        if names != sorted(names) or len(names) != len(set(names)):
            raise ValueError("fingerprint axes must be unique and sorted")
        if any(x.available_ns > self.decision_ns for x in self.axes):
            raise ValueError("fingerprint contains future evidence")
        expected = _fingerprint_id(self.decision_ns, self.axes)
        if self.fingerprint_id != expected:
            raise ValueError("fingerprint identity mismatch")

    @property
    def values(self) -> dict[str, float]:
        return {x.axis: float(x.value) for x in self.axes}

    @property
    def sources(self) -> dict[str, str]:
        return {x.axis: x.source_id for x in self.axes}


def _fingerprint_id(decision_ns: int, axes: tuple[AxisObservation, ...]) -> str:
    return _hash({
        "decision_ns": decision_ns,
        "axes": [
            {
                "axis": x.axis,
                "value": float(x.value),
                "available_ns": x.available_ns,
                "source_id": x.source_id,
                "representation_id": x.representation_id,
                "lineage_id": x.lineage_id,
            }
            for x in axes
        ],
    })


def build_fingerprint(decision_ns: int, observations: Iterable[AxisObservation]) -> Fingerprint:
    if type(decision_ns) is not int or decision_ns < 0:
        raise ValueError("decision_ns must be non-negative")
    latest: dict[str, AxisObservation] = {}
    for observation in observations:
        if not isinstance(observation, AxisObservation):
            raise TypeError("observations must contain AxisObservation")
        if observation.available_ns > decision_ns:
            continue
        previous = latest.get(observation.axis)
        if previous is None or (observation.available_ns, observation.lineage_id) > (
            previous.available_ns,
            previous.lineage_id,
        ):
            latest[observation.axis] = observation
    if not latest:
        raise ValueError("no observations were available by decision time")
    axes = tuple(latest[name] for name in sorted(latest))
    return Fingerprint(decision_ns, axes, _fingerprint_id(decision_ns, axes))


def observations_from_frame(frame: dict) -> tuple[AxisObservation, ...]:
    """Convert one already-gated AION replay frame into auditable normalized axes.

    A malformed frame that contains future-available data is rejected rather than
    silently clipping it, because that would hide a causality defect upstream.
    """
    if not isinstance(frame, dict):
        raise TypeError("frame must be a dict")
    decision_ns = frame.get("asof_ns")
    if type(decision_ns) is not int or decision_ns < 0:
        raise ValueError("frame requires non-negative asof_ns")
    frame_hash = _name("frame_hash", str(frame.get("frame_hash") or ""))
    out: list[AxisObservation] = []

    def add(axis, value, available_ns, source_id, representation_id, lineage_id):
        if type(available_ns) is not int or available_ns < 0:
            raise ValueError("frame observation available_ns must be non-negative")
        if available_ns > decision_ns:
            raise ValueError("AION frame contains future evidence")
        out.append(AxisObservation(
            axis=axis,
            value=value,
            available_ns=available_ns,
            source_id=source_id,
            representation_id=representation_id,
            lineage_id=lineage_id,
        ))

    for row in frame.get("prices", ()):
        if not isinstance(row, dict):
            raise TypeError("price rows must be objects")
        symbol = _name("price symbol", str(row.get("symbol") or ""))
        rep = _name("representation_id", str(row.get("representation_id") or ""))
        source = _name("source_id", str(row.get("source_id") or ""))
        lineage = _name("event_hash", str(row.get("event_hash") or ""))
        available = row.get("available_ns")
        values = [row.get(k) for k in ("open", "high", "low", "close")]
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)) for v in values):
            raise ValueError("price row requires finite OHLC")
        open_, high, low, close = map(float, values)
        if high < max(open_, close) or low > min(open_, close) or high < low:
            raise ValueError("price row OHLC is inconsistent")
        scale = max(abs(close), 1e-12)
        span = max(high - low, 1e-12)
        prefix = f"price.{symbol}.{rep}"
        add(f"{prefix}.body_pct", (close - open_) / scale, available, source, rep, lineage)
        add(f"{prefix}.range_pct", (high - low) / scale, available, source, rep, lineage)
        add(f"{prefix}.close_location", (close - low) / span, available, source, rep, lineage)

    for source, book in sorted((frame.get("books") or {}).items()):
        if not isinstance(book, dict) or book.get("status") != "true_depth":
            continue
        source = _name("book source", str(source))
        age = book.get("age_ns", 0)
        if type(age) is not int or age < 0 or age > decision_ns:
            raise ValueError("book age is invalid")
        available = decision_ns - age
        lineage = _hash({"frame_hash": frame_hash, "book_source": source, "sequence": book.get("sequence")})
        imbalance = book.get("imbalance")
        if isinstance(imbalance, (int, float)) and not isinstance(imbalance, bool) and math.isfinite(float(imbalance)):
            add(f"book.{source}.imbalance", float(imbalance), available, source, "true_depth", lineage)
        spread, bid, ask = book.get("spread"), book.get("best_bid"), book.get("best_ask")
        if all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v)) for v in (spread, bid, ask)):
            mid = (float(bid) + float(ask)) / 2.0
            if abs(mid) > 1e-12:
                add(f"book.{source}.spread_pct", float(spread) / mid, available, source, "true_depth", lineage)

    for row in frame.get("macro", ()):
        if not isinstance(row, dict):
            raise TypeError("macro rows must be objects")
        source = _name("macro source", str(row.get("source_id") or ""))
        available = row.get("available_ns")
        values = row.get("values") or {}
        if not isinstance(values, dict):
            raise TypeError("macro values must be an object")
        series = _name("macro series", str(values.get("series") or ""))
        lineage = _hash({
            "frame_hash": frame_hash,
            "source": source,
            "series": series,
            "period": values.get("period"),
            "revision": row.get("revision"),
            "available_ns": available,
        })
        for key, value in sorted(values.items()):
            if key in ("series", "period") or isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            number = float(value)
            if math.isfinite(number):
                add(f"macro.{source}.{series}.{key}", number, available, source, "macro", lineage)

    return tuple(sorted(out, key=lambda x: (x.axis, x.available_ns, x.lineage_id)))


def fingerprint_from_frame(frame: dict) -> Fingerprint:
    """Create a PARALLAX fingerprint directly from an AION replay frame."""
    decision_ns = frame.get("asof_ns") if isinstance(frame, dict) else None
    if type(decision_ns) is not int:
        raise ValueError("frame requires asof_ns")
    return build_fingerprint(decision_ns, observations_from_frame(frame))


def mask_fingerprint(
    fingerprint: Fingerprint,
    *,
    exclude_sources: Iterable[str] = (),
    exclude_axes: Iterable[str] = (),
) -> Fingerprint:
    sources = set(exclude_sources)
    axes_to_drop = set(exclude_axes)
    axes = tuple(
        x for x in fingerprint.axes
        if x.source_id not in sources and x.axis not in axes_to_drop
    )
    if not axes:
        raise ValueError("mask removes every fingerprint axis")
    return Fingerprint(fingerprint.decision_ns, axes, _fingerprint_id(fingerprint.decision_ns, axes))


@dataclass(frozen=True)
class Settlement:
    fingerprint_id: str
    outcome: float
    available_ns: int
    source_id: str
    verified: bool

    def __post_init__(self) -> None:
        _name("fingerprint_id", self.fingerprint_id)
        _finite(self.outcome)
        if type(self.available_ns) is not int or self.available_ns < 0:
            raise ValueError("available_ns must be non-negative")
        _name("source_id", self.source_id)
        if type(self.verified) is not bool:
            raise TypeError("verified must be bool")


class AnalogAtlas:
    def __init__(self) -> None:
        self._frames: dict[str, Fingerprint] = {}
        self._settlements: dict[str, Settlement] = {}

    def add(self, fingerprint: Fingerprint) -> bool:
        if not isinstance(fingerprint, Fingerprint):
            raise TypeError("fingerprint must be Fingerprint")
        existing = self._frames.get(fingerprint.fingerprint_id)
        if existing is not None:
            if existing != fingerprint:
                raise ValueError("fingerprint identity collision")
            return False
        self._frames[fingerprint.fingerprint_id] = fingerprint
        return True

    def settle(
        self,
        fingerprint_id: str,
        *,
        outcome: float,
        available_ns: int,
        source_id: str,
        verified: bool,
    ) -> Settlement:
        frame = self._frames.get(fingerprint_id)
        if frame is None:
            raise KeyError("unknown fingerprint")
        settlement = Settlement(fingerprint_id, outcome, available_ns, source_id, verified)
        if settlement.available_ns <= frame.decision_ns:
            raise ValueError("outcome cannot be available at or before the decision")
        existing = self._settlements.get(fingerprint_id)
        if existing is not None and existing != settlement:
            raise ValueError("settlement is immutable")
        self._settlements[fingerprint_id] = settlement
        return settlement

    @staticmethod
    def _scales(candidates: list[Fingerprint], axes: set[str]) -> dict[str, float]:
        scales: dict[str, float] = {}
        for axis in sorted(axes):
            values = [x.values[axis] for x in candidates if axis in x.values]
            if len(values) < 2:
                scales[axis] = 1.0
                continue
            center = median(values)
            deviations = [abs(x - center) for x in values]
            scale = median(deviations)
            if not math.isfinite(scale) or scale <= 1e-12:
                spread = max(values) - min(values)
                scale = spread if spread > 1e-12 else 1.0
            scales[axis] = scale
        return scales

    def neighbors(
        self,
        query: Fingerprint,
        *,
        k: int = 5,
        min_shared_axes: int = 2,
        exclude_sources: Iterable[str] = (),
        exclude_axes: Iterable[str] = (),
    ) -> dict:
        if type(k) is not int or k < 1:
            raise ValueError("k must be positive")
        if type(min_shared_axes) is not int or min_shared_axes < 1:
            raise ValueError("min_shared_axes must be positive")
        masked = mask_fingerprint(
            query,
            exclude_sources=exclude_sources,
            exclude_axes=exclude_axes,
        ) if tuple(exclude_sources) or tuple(exclude_axes) else query

        candidates = [
            frame for frame in self._frames.values()
            if frame.decision_ns < query.decision_ns and frame.fingerprint_id != query.fingerprint_id
        ]
        query_axes = set(masked.values)
        scales = self._scales(candidates, query_axes)
        rows = []
        for candidate in candidates:
            shared = sorted(query_axes & set(candidate.values))
            if len(shared) < min_shared_axes:
                continue
            # Balance by source/representation family so one very wide sensor cannot
            # dominate the neighborhood solely because it contributes more columns.
            grouped: dict[str, list[float]] = {}
            for axis in shared:
                z = (masked.values[axis] - candidate.values[axis]) / scales[axis]
                grouped.setdefault(masked.sources[axis], []).append(z * z)
            source_distances = {
                source: math.sqrt(sum(values) / len(values))
                for source, values in grouped.items()
            }
            base_distance = math.sqrt(
                sum(value * value for value in source_distances.values()) / len(source_distances)
            )
            coverage = len(shared) / len(query_axes)
            distance = base_distance / math.sqrt(max(coverage, 1e-12))
            rows.append({
                "fingerprint_id": candidate.fingerprint_id,
                "decision_ns": candidate.decision_ns,
                "distance": distance,
                "coverage": coverage,
                "shared_axes": shared,
                "source_distances": dict(sorted(source_distances.items())),
            })
        rows.sort(key=lambda x: (x["distance"], -x["coverage"], x["decision_ns"], x["fingerprint_id"]))
        selected = rows[:k]
        return {
            "query_fingerprint_id": query.fingerprint_id,
            "neighbors": selected,
            "novelty": selected[0]["distance"] if selected else None,
            "candidate_count": len(rows),
            "query_axes": sorted(query_axes),
            "execution_authorized": False,
            "causal_only": True,
        }

    def outcome_summary(self, neighbor_result: dict, *, asof_ns: int) -> dict:
        if type(asof_ns) is not int or asof_ns < 0:
            raise ValueError("asof_ns must be non-negative")
        values = []
        hidden = 0
        for row in neighbor_result.get("neighbors", []):
            settlement = self._settlements.get(row["fingerprint_id"])
            if settlement is None:
                continue
            if settlement.available_ns > asof_ns:
                hidden += 1
                continue
            if not settlement.verified:
                continue
            values.append(float(settlement.outcome))
        return {
            "verified_samples": len(values),
            "hidden_future_outcomes": hidden,
            "mean": sum(values) / len(values) if values else None,
            "minimum": min(values) if values else None,
            "maximum": max(values) if values else None,
            "production_authorized": False,
        }

    def ablation(
        self,
        query: Fingerprint,
        *,
        source_id: str,
        k: int = 5,
        min_shared_axes: int = 2,
    ) -> dict:
        full = self.neighbors(query, k=k, min_shared_axes=min_shared_axes)
        masked = self.neighbors(
            query,
            k=k,
            min_shared_axes=min_shared_axes,
            exclude_sources=(source_id,),
        )
        left = {x["fingerprint_id"] for x in full["neighbors"]}
        right = {x["fingerprint_id"] for x in masked["neighbors"]}
        union = left | right
        overlap = len(left & right) / len(union) if union else 1.0
        return {
            "source_id": source_id,
            "neighbor_overlap": overlap,
            "full": full,
            "masked": masked,
            "fragile": overlap < 0.5,
            "execution_authorized": False,
        }
