from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from .catalog import build_catalog


@dataclass(frozen=True)
class SourceIdentity:
    relative_path: str
    canonical_symbol: str
    chart_type: str
    representation_role: str
    execution_safe: bool
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def load_identity_manifest(path: Path) -> dict[str, SourceIdentity]:
    if not path.exists():
        return {}
    df = pd.read_csv(path, dtype=str).fillna("")
    required = {"relative_path", "canonical_symbol", "chart_type", "representation_role", "execution_safe", "notes"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Identity manifest {path} missing columns: {sorted(missing)}")
    out: dict[str, SourceIdentity] = {}
    for row in df.to_dict(orient="records"):
        key = str(row["relative_path"]).replace("\\", "/").lstrip("./")
        out[key] = SourceIdentity(
            relative_path=key,
            canonical_symbol=str(row["canonical_symbol"]).strip(),
            chart_type=str(row["chart_type"]).strip() or "UNLABELED",
            representation_role=str(row["representation_role"]).strip() or "representation",
            execution_safe=_truthy(row["execution_safe"]),
            notes=str(row["notes"]).strip(),
        )
    return out


def resolve_identity(path: Path, data_root: Path, manifest: dict[str, SourceIdentity], symbol_hint: str) -> SourceIdentity:
    try:
        rel = path.resolve().relative_to(data_root.resolve()).as_posix()
    except ValueError:
        rel = path.name
    if rel in manifest:
        return manifest[rel]
    return SourceIdentity(
        relative_path=rel,
        canonical_symbol=symbol_hint,
        chart_type="UNLABELED",
        representation_role="representation",
        execution_safe=False,
        notes="Auto-default: chart construction not explicitly mapped; research-only.",
    )


def scaffold_identity_manifest(data_root: Path, output: Path) -> Path:
    catalog = build_catalog(data_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["relative_path", "canonical_symbol", "chart_type", "representation_role", "execution_safe", "notes"]
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in catalog.itertuples(index=False):
            p = Path(row.path)
            try:
                rel = p.resolve().relative_to(data_root.resolve()).as_posix()
            except ValueError:
                rel = p.name
            writer.writerow({
                "relative_path": rel,
                "canonical_symbol": row.symbol_hint,
                "chart_type": "UNLABELED",
                "representation_role": "representation",
                "execution_safe": "false",
                "notes": "Fill chart type explicitly. Set execution_safe=true only for a price representation suitable for execution PnL.",
            })
    return output
