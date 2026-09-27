"""ASCENSION Collision Detector v0.2.1.

Read-only structural + transitive collision analysis for explicit system manifests.
It never mutates input manifests or sibling-system state.
"""
from __future__ import annotations

from itertools import combinations

DEFAULT_POLICY = {
    "missing_manifest": "high",
    "dependency_cycle": "high",
}


def _severity(policy, key):
    value = policy.get(key, DEFAULT_POLICY[key])
    if value not in {"info", "low", "medium", "high", "critical"}:
        raise ValueError(f"invalid severity for {key}: {value}")
    return value


def _graph_paths(graph, origin):
    """Return first simple path to each reachable node and explicit cycle paths."""
    first_paths = {}
    cycles = []

    def dfs(node, path):
        for nxt in graph.get(node, []):
            if nxt in path:
                i = path.index(nxt)
                cycles.append(path[i:] + [nxt])
                continue
            if nxt not in first_paths:
                next_path = path + [nxt]
                first_paths[nxt] = next_path
                dfs(nxt, next_path)

    dfs(origin, [origin])
    return first_paths, cycles


def _direct_findings(a_name, a, b_name, b):
    findings = []
    for resource in sorted(set(a.get("mutation_rights", [])) & set(b.get("mutation_rights", []))):
        findings.append({"code": "MUTATION_RIGHT_COLLISION", "systems": [a_name, b_name], "resource": resource, "severity": "critical"})
    for resource in sorted(set(a.get("owned_domains", [])) & set(b.get("owned_domains", []))):
        findings.append({"code": "OWNERSHIP_COLLISION", "systems": [a_name, b_name], "resource": resource, "severity": "high"})

    ia = {x["name"]: x["version"] for x in a.get("interfaces", [])}
    ib = {x["name"]: x["version"] for x in b.get("interfaces", [])}
    for name in sorted(set(ia) & set(ib)):
        if ia[name] != ib[name]:
            findings.append({"code": "INTERFACE_VERSION_CONFLICT", "systems": [a_name, b_name], "resource": name, "versions": [ia[name], ib[name]], "severity": "high"})

    req = set(a.get("requires", [])) | set(b.get("requires", []))
    forb = set(a.get("forbids", [])) | set(b.get("forbids", []))
    for resource in sorted(req & forb):
        findings.append({"code": "INVARIANT_CONTRADICTION", "systems": [a_name, b_name], "resource": resource, "severity": "critical"})

    shared = set(a.get("shared_state", [])) & set(b.get("shared_state", []))
    coordinated = set(a.get("coordination_contracts", [])) & set(b.get("coordination_contracts", []))
    for resource in sorted(shared - coordinated):
        findings.append({"code": "UNCOORDINATED_SHARED_STATE", "systems": [a_name, b_name], "resource": resource, "severity": "high"})
    return findings


def analyze_ecosystem(manifests, dependency_graph, policy=None):
    """Analyze explicit manifests and dependency edges without writing external state."""
    policy = {**DEFAULT_POLICY, **(policy or {})}
    findings = []

    # Pairwise direct-contract analysis.
    for a_name, b_name in combinations(sorted(manifests), 2):
        findings.extend(_direct_findings(a_name, manifests[a_name], b_name, manifests[b_name]))

    # Graph analysis with path-preserving transitive evidence.
    seen_cycles = set()
    for origin in sorted(manifests):
        paths, cycles = _graph_paths(dependency_graph, origin)
        for cycle in cycles:
            # Canonicalize by rotation only enough to suppress repeated rediscovery.
            core = cycle[:-1]
            rotations = [tuple(core[i:] + core[:i]) for i in range(len(core))]
            canon = min(rotations) if rotations else tuple()
            if canon not in seen_cycles:
                seen_cycles.add(canon)
                findings.append({"code": "DEPENDENCY_CYCLE", "path": list(canon) + ([canon[0]] if canon else []), "severity": _severity(policy, "dependency_cycle")})

        origin_manifest = manifests[origin]
        for dep, path in sorted(paths.items()):
            if dep not in manifests:
                findings.append({"code": "MISSING_DEPENDENCY_MANIFEST", "origin": origin, "dependency": dep, "path": path, "severity": _severity(policy, "missing_manifest")})
                continue
            dep_manifest = manifests[dep]
            for resource in sorted(set(origin_manifest.get("mutation_rights", [])) & set(dep_manifest.get("mutation_rights", []))):
                if len(path) > 2:
                    findings.append({"code": "TRANSITIVE_MUTATION_COLLISION", "origin": origin, "dependency": dep, "path": path, "resource": resource, "severity": "critical"})
            for resource in sorted(set(origin_manifest.get("requires", [])) & set(dep_manifest.get("forbids", []))):
                if len(path) > 2:
                    findings.append({"code": "TRANSITIVE_INVARIANT_CONTRADICTION", "origin": origin, "dependency": dep, "path": path, "resource": resource, "severity": "critical"})

    # Stable deduplication.
    import json
    unique = {json.dumps(f, sort_keys=True, separators=(",", ":")): f for f in findings}
    findings = [unique[k] for k in sorted(unique)]
    critical = [f for f in findings if f["severity"] == "critical"]
    boundary_bad = {"MUTATION_RIGHT_COLLISION", "OWNERSHIP_COLLISION", "TRANSITIVE_MUTATION_COLLISION"}
    return {
        "safe": not critical,
        "collision_free": not findings,
        "boundary_gate": not any(f["code"] in boundary_bad for f in findings),
        "non_interference_gate": not critical,
        "findings": findings,
    }
