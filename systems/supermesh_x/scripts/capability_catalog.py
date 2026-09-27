#!/usr/bin/env python3
"""Provider discovery metadata and capability matching for SuperMesh-X."""

TRUST_CLASSES = {"public", "sandbox", "enterprise", "regulated", "unknown"}


def normalize_descriptor(provider):
    row = dict(provider)
    row["name"] = str(row["name"])
    row["capabilities"] = sorted(set(row.get("capabilities", [])))
    row["runtime_targets"] = sorted(set(row.get("runtime_targets", ["chatgpt", "codex", "claude"])))
    row["transports"] = list(dict.fromkeys(row.get("transports", [])))
    row["auth_modes"] = list(dict.fromkeys(row.get("auth_modes", ["none"])))
    row["dynamic"] = bool(row.get("dynamic", False))
    trust = row.get("trust_class", "unknown")
    row["trust_class"] = trust if trust in TRUST_CLASSES else "unknown"
    return row


def discover_candidates(required_capabilities, catalog, runtime=None):
    required = set(required_capabilities)
    rows = []
    for raw in catalog:
        row = normalize_descriptor(raw)
        if not required.issubset(set(row["capabilities"])):
            continue
        if runtime and runtime not in row["runtime_targets"]:
            continue
        rows.append(row)
    rows.sort(key=lambda r: (-len(r["capabilities"]), r["name"]))
    return rows
