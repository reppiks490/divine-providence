
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence

@dataclass(frozen=True)
class ComponentContext:
    corpus_ids: Sequence[str]
    timestamps: Sequence[int]
    series: Mapping[str, Sequence[float]]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def prefix(self, end_exclusive: int) -> "ComponentContext":
        sliced_meta = {}
        n = len(self.timestamps)
        def slice_aligned(value):
            if isinstance(value, (list, tuple)) and len(value) == n:
                return value[:end_exclusive]
            if isinstance(value, dict):
                return {kk: slice_aligned(vv) for kk, vv in value.items()}
            return value
        for k, v in self.metadata.items():
            sliced_meta[k] = slice_aligned(v)
        return ComponentContext(
            corpus_ids=self.corpus_ids,
            timestamps=self.timestamps[:end_exclusive],
            series={k: v[:end_exclusive] for k, v in self.series.items()},
            metadata=sliced_meta,
        )

@dataclass
class ComponentResult:
    component_id: str
    component_version: str
    timestamps: List[int]
    values: List[Any]
    provenance: Dict[str, Any]
    available_at: List[int] | None = None

class BaseComponentAdapter:
    component_id = "UNSET"
    component_version = "0.0.0"
    role = "unknown"
    causal_output_delay_bars = 0

    def validate_context(self, ctx: ComponentContext) -> None:
        n = len(ctx.timestamps)
        if not ctx.corpus_ids:
            raise ValueError("At least one corpus_id is required")
        for name, values in ctx.series.items():
            if len(values) != n:
                raise ValueError(f"Series length mismatch for {name}")
        if any(ctx.timestamps[i] >= ctx.timestamps[i+1] for i in range(n-1)):
            raise ValueError("timestamps must be strictly increasing")

    def run(self, ctx: ComponentContext) -> ComponentResult:
        raise NotImplementedError
