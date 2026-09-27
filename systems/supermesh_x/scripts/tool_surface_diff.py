#!/usr/bin/env python3
"""Stable tool-surface fingerprints and compatibility-aware diffs."""
import hashlib
import json


def _canonical(value):
    if isinstance(value, dict):
        return {k: _canonical(value[k]) for k in sorted(value)}
    if isinstance(value, list):
        return [_canonical(v) for v in value]
    return value


def _schema(tool):
    return tool.get("inputSchema") or tool.get("input_schema") or {"type": "object", "properties": {}}


def fingerprint_tool(tool):
    payload = {
        "name": str(tool.get("name", "")),
        "inputSchema": _canonical(_schema(tool)),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _change_classification(before, after):
    b = _schema(before)
    a = _schema(after)
    bp = b.get("properties", {}) or {}
    ap = a.get("properties", {}) or {}
    br = set(b.get("required", []) or [])
    ar = set(a.get("required", []) or [])

    removed_props = sorted(set(bp) - set(ap))
    new_required = sorted(ar - br)
    type_changes = []
    for key in set(bp).intersection(ap):
        if bp.get(key, {}).get("type") != ap.get(key, {}).get("type"):
            type_changes.append(key)

    if removed_props or new_required or type_changes:
        return "breaking", {
            "removed_properties": removed_props,
            "new_required": new_required,
            "type_changes": sorted(type_changes),
        }
    return "compatible", {
        "added_optional": sorted((set(ap) - set(bp)) - ar),
        "new_required": [],
        "removed_properties": [],
        "type_changes": [],
    }


def diff_tool_surfaces(before_tools, after_tools):
    before = {t.get("name"): t for t in before_tools}
    after = {t.get("name"): t for t in after_tools}
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = []
    for name in sorted(set(before).intersection(after)):
        if fingerprint_tool(before[name]) == fingerprint_tool(after[name]):
            continue
        classification, details = _change_classification(before[name], after[name])
        changed.append({
            "name": name,
            "classification": classification,
            "before_fingerprint": fingerprint_tool(before[name]),
            "after_fingerprint": fingerprint_tool(after[name]),
            "details": details,
        })
    breaking = bool(removed) or any(x["classification"] == "breaking" for x in changed)
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "breaking": breaking,
    }
