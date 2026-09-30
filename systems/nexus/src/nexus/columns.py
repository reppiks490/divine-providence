from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import csv


class AmbiguousColumnError(ValueError):
    pass


@dataclass(frozen=True)
class HeaderProfile:
    columns: tuple[str, ...]
    positions: dict[str, tuple[int, ...]]

    @property
    def duplicates(self) -> dict[str, tuple[int, ...]]:
        return {k: v for k, v in self.positions.items() if len(v) > 1}


def profile_header(columns: list[str] | tuple[str, ...]) -> HeaderProfile:
    positions: dict[str, list[int]] = {}
    for i, c in enumerate(columns):
        key = str(c).strip().lower()
        positions.setdefault(key, []).append(i)
    return HeaderProfile(tuple(str(c) for c in columns), {k: tuple(v) for k, v in positions.items()})


def read_header(path: str | Path) -> HeaderProfile:
    with Path(path).open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        return profile_header(next(csv.reader(f), []))


def resolve_columns(
    header: HeaderProfile,
    *,
    required: tuple[str, ...] = ("time", "open", "high", "low", "close"),
    optional: tuple[str, ...] = ("volume",),
    explicit_positions: dict[str, int] | None = None,
) -> dict[str, int]:
    """Resolve semantic fields to exact original column positions.

    Duplicate semantic fields are never silently collapsed. A caller must choose the exact
    original position through ``explicit_positions``. Positions are zero-based.
    """
    if explicit_positions is not None and not isinstance(explicit_positions,dict):
        raise TypeError("explicit_positions must be a dict or None")
    normalized:dict[str,int]={}
    for raw_key,raw_value in (explicit_positions or {}).items():
        key=str(raw_key).strip().lower()
        if not key:
            raise ValueError("explicit column keys must be non-empty")
        if type(raw_value) is not int:
            raise TypeError(f"explicit {key} position must be an integer")
        normalized[key]=raw_value
    explicit_positions=normalized
    out: dict[str, int] = {}
    for key in (*required, *optional):
        positions = header.positions.get(key, ())
        if key in explicit_positions:
            i = explicit_positions[key]
            if i < 0 or i >= len(header.columns):
                raise ValueError(f"explicit {key} position {i} is out of range")
            actual = header.columns[i].strip().lower()
            if actual != key:
                raise ValueError(f"explicit {key} position {i} points to {actual!r}")
            out[key] = i
            continue
        if not positions:
            if key in required:
                raise ValueError(f"missing required column: {key}")
            continue
        if len(positions) > 1:
            raise AmbiguousColumnError(
                f"ambiguous {key!r} columns at positions {positions}; provide explicit_positions"
            )
        out[key] = positions[0]
    return out
