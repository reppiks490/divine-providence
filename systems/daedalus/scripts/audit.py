from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
issues: list[str] = []
files = sorted(SRC.rglob("*.py"))

# Broad exception capture is acceptable only at orchestration/file-boundary layers where
# the exception is converted into an explicit error record or wrapped with context.
BROAD_EXCEPTION_ALLOWED = {
    "batch.py",
    "catalog.py",
    "corpus.py",
}


def source_segment(text: str, node: ast.AST) -> str:
    return ast.get_source_segment(text, node) or ""


for path in files:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        issues.append(f"SYNTAX {path}:{exc.lineno}: {exc.msg}")
        continue

    # Duplicate definitions in the same lexical scope silently overwrite earlier code.
    def check_duplicate_defs(body, scope: str) -> None:
        seen: dict[str, int] = {}
        for item in body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = item.name
                if name in seen:
                    issues.append(
                        f"DUPLICATE_DEFINITION {path}:{item.lineno}: {scope}.{name} "
                        f"(first declared line {seen[name]})"
                    )
                else:
                    seen[name] = item.lineno
            if isinstance(item, ast.ClassDef):
                check_duplicate_defs(item.body, f"{scope}.{item.name}")

    check_duplicate_defs(tree.body, "module")

    # Duplicate annotated fields inside a class silently overwrite earlier values.
    for node in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
        seen: dict[str, int] = {}
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                name = item.target.id
                if name in seen:
                    issues.append(
                        f"DUPLICATE_CLASS_FIELD {path}:{item.lineno}: {node.name}.{name} "
                        f"(first declared line {seen[name]})"
                    )
                else:
                    seen[name] = item.lineno

    # Bare/swallowed exception handlers hide research-protocol failures.
    for node in (n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)):
        if node.type is None:
            issues.append(f"BARE_EXCEPT {path}:{node.lineno}")
        elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
            if path.name not in BROAD_EXCEPTION_ALLOWED:
                issues.append(f"BROAD_EXCEPTION {path}:{node.lineno}: narrow or document this handler")
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            issues.append(f"SWALLOWED_EXCEPTION {path}:{node.lineno}")

    # Mutable default function arguments are a source of cross-experiment state leakage.
    for node in (n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))):
        for default in list(node.args.defaults) + [d for d in node.args.kw_defaults if d is not None]:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                issues.append(f"MUTABLE_DEFAULT {path}:{node.lineno}: {node.name}")

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        # Future target construction is allowed; predictor features must never use negative shift.
        if re.search(r"\.shift\(\s*-\d+", line) and "future_log_return" not in line:
            issues.append(f"POSSIBLE_LOOKAHEAD {path}:{lineno}: {stripped}")
        if re.search(r"rolling\([^)]*center\s*=\s*True", line):
            issues.append(f"CENTERED_ROLLING_LOOKAHEAD {path}:{lineno}: {stripped}")
        if re.search(r"\.(bfill|backfill)\s*\(", line) or re.search(r"method\s*=\s*['\"]bfill['\"]", line):
            issues.append(f"BACKFILL_LOOKAHEAD_RISK {path}:{lineno}: {stripped}")
        if re.search(r"direction\s*=\s*['\"](forward|nearest)['\"]", line):
            issues.append(f"NONCAUSAL_ASOF {path}:{lineno}: {stripped}")
        if "drop_duplicates" in line and re.search(r"time|timestamp", line, flags=re.I):
            issues.append(f"TIMESTAMP_DEDUP_RISK {path}:{lineno}: {stripped}")
        if "production_authorized\": True" in line or "production_authorized': True" in line:
            issues.append(f"PRODUCTION_WRITE_FLAG {path}:{lineno}")
        if re.search(r"\beval\s*\(|\bexec\s*\(", line):
            issues.append(f"DYNAMIC_EXECUTION {path}:{lineno}")
        if re.search(r"\bos\.system\s*\(|subprocess\..*shell\s*=\s*True", line):
            issues.append(f"SHELL_EXECUTION {path}:{lineno}")
        if re.search(r"pickle\.(loads?|load)\s*\(", line):
            issues.append(f"UNSAFE_PICKLE_LOAD {path}:{lineno}")
        if re.search(r"\b(TODO|FIXME|XXX)\b", line):
            issues.append(f"UNRESOLVED_MARKER {path}:{lineno}: {stripped}")

    # merge_asof must be explicitly backward and must reject exact-time predictor matches.
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "merge_asof":
            kwargs = {kw.arg: kw.value for kw in node.keywords if kw.arg}
            direction = kwargs.get("direction")
            exact = kwargs.get("allow_exact_matches")
            if not (isinstance(direction, ast.Constant) and direction.value == "backward"):
                issues.append(f"ASOF_DIRECTION {path}:{node.lineno}: merge_asof must use backward direction")
            if not (isinstance(exact, ast.Constant) and exact.value is False):
                issues.append(f"ASOF_EXACT_MATCH {path}:{node.lineno}: exact matches must be disabled")

scanned_lines = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in files)
print(f"Audited {len(files)} source files / {scanned_lines} source lines")
if issues:
    print("\n".join(issues))
    raise SystemExit(1)
print(
    "Audit passed: syntax/AST, duplicate definitions/fields, exception handling, mutable defaults, "
    "look-ahead/backfill/as-of patterns, timestamp dedup risk, dynamic/shell execution, unsafe pickle, "
    "unresolved markers, and production authorization flags are clean."
)
