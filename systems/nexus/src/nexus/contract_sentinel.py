from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _ast_sha256(path: Path) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    # ``include_attributes=False`` intentionally ignores line/column churn while
    # preserving names, defaults, annotations, control flow, constants and bodies.
    normalized = ast.dump(tree, annotate_fields=True, include_attributes=False)
    return _sha256(normalized.encode("utf-8"))


@dataclass(frozen=True, slots=True)
class BoundaryFileFingerprint:
    sibling: str
    role: str
    path: str
    raw_sha256: str
    ast_sha256: str
    size_bytes: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ContractDriftSnapshot:
    schema: str
    files: tuple[BoundaryFileFingerprint, ...]
    snapshot_hash: str

    @classmethod
    def capture(cls, boundaries: Mapping[tuple[str, str], str | Path], *,
                relative_to: str | Path | None = None) -> "ContractDriftSnapshot":
        """``relative_to`` records POSIX paths relative to that root, so the snapshot
        carries no machine-specific absolute paths (a path-independent baseline)."""
        root = Path(relative_to).resolve() if relative_to is not None else None
        rows: list[BoundaryFileFingerprint] = []
        for (sibling, role), raw_path in sorted(boundaries.items()):
            path = Path(raw_path)
            if not path.is_file():
                raise FileNotFoundError(path)
            payload = path.read_bytes()
            rows.append(
                BoundaryFileFingerprint(
                    sibling=str(sibling),
                    role=str(role),
                    path=str(path.resolve()) if root is None else path.resolve().relative_to(root).as_posix(),
                    raw_sha256=_sha256(payload),
                    ast_sha256=_ast_sha256(path),
                    size_bytes=len(payload),
                )
            )
        body = {
            "schema": "nexus.contract-drift-snapshot.v1",
            "files": [r.to_dict() for r in rows],
        }
        snapshot_hash = _sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode())
        return cls(body["schema"], tuple(rows), snapshot_hash)

    def verify(self) -> bool:
        body = {"schema": self.schema, "files": [r.to_dict() for r in self.files]}
        return self.snapshot_hash == _sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode())

    def to_dict(self) -> dict:
        return {
            "schema": self.schema,
            "files": [r.to_dict() for r in self.files],
            "snapshot_hash": self.snapshot_hash,
        }

    def save(self, path: str | Path) -> None:
        # newline="\n": a baseline is committed and compared across platforms, so its bytes must not vary.
        Path(path).write_text(json.dumps(self.to_dict(), sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")

    @classmethod
    def load(cls, path: str | Path) -> "ContractDriftSnapshot":
        body = json.loads(Path(path).read_text(encoding="utf-8"))
        obj = cls(
            schema=body["schema"],
            files=tuple(BoundaryFileFingerprint(**row) for row in body["files"]),
            snapshot_hash=body["snapshot_hash"],
        )
        if obj.schema != "nexus.contract-drift-snapshot.v1" or not obj.verify():
            raise ValueError("invalid contract-drift snapshot")
        return obj


@dataclass(frozen=True, slots=True)
class ContractDriftItem:
    sibling: str
    role: str
    status: str
    raw_changed: bool
    semantic_changed: bool
    old_ast_sha256: str | None
    new_ast_sha256: str | None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ContractDriftReport:
    schema: str
    baseline_hash: str
    current_hash: str
    items: tuple[ContractDriftItem, ...]
    semantic_drift: bool
    raw_drift: bool

    def to_dict(self) -> dict:
        return {
            "schema": self.schema,
            "baseline_hash": self.baseline_hash,
            "current_hash": self.current_hash,
            "items": [x.to_dict() for x in self.items],
            "semantic_drift": self.semantic_drift,
            "raw_drift": self.raw_drift,
        }


def compare_contract_snapshots(baseline: ContractDriftSnapshot, current: ContractDriftSnapshot) -> ContractDriftReport:
    if not baseline.verify() or not current.verify():
        raise ValueError("snapshot hash verification failed")
    old = {(x.sibling, x.role): x for x in baseline.files}
    new = {(x.sibling, x.role): x for x in current.files}
    items: list[ContractDriftItem] = []
    for key in sorted(set(old) | set(new)):
        a = old.get(key); b = new.get(key)
        if a is None:
            items.append(ContractDriftItem(key[0], key[1], "added", True, True, None, b.ast_sha256 if b else None))
            continue
        if b is None:
            items.append(ContractDriftItem(key[0], key[1], "removed", True, True, a.ast_sha256, None))
            continue
        raw_changed = a.raw_sha256 != b.raw_sha256
        # ``ast.dump`` output differs between Python versions, so AST fingerprints
        # are only comparable when the bytes differ; identical bytes are identical code.
        semantic_changed = raw_changed and a.ast_sha256 != b.ast_sha256
        status = "semantic_change" if semantic_changed else ("nonsemantic_change" if raw_changed else "unchanged")
        items.append(ContractDriftItem(key[0], key[1], status, raw_changed, semantic_changed, a.ast_sha256, b.ast_sha256))
    return ContractDriftReport(
        schema="nexus.contract-drift-report.v1",
        baseline_hash=baseline.snapshot_hash,
        current_hash=current.snapshot_hash,
        items=tuple(items),
        semantic_drift=any(x.semantic_changed for x in items),
        raw_drift=any(x.raw_changed for x in items),
    )
