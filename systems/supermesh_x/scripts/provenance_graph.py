#!/usr/bin/env python3
"""Build and query evidence lineage without duplicating identical source material."""


def _cycle(nodes):
    visiting, visited = set(), set()

    def walk(node):
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for parent in nodes.get(node, {}).get("parents", []):
            if parent in nodes and walk(parent):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(walk(node) for node in nodes)


def build_graph(records):
    nodes = {r["id"]: dict(r) for r in records}
    source_keys = set()
    for r in records:
        source_keys.add((r.get("source", "unknown"), r.get("content_hash", "")))
    return {
        "nodes": nodes,
        "source_nodes": len(source_keys),
        "evidence_nodes": len(nodes),
        "acyclic": not _cycle(nodes),
    }


def lineage_for(graph, evidence_id):
    nodes = graph.get("nodes", {})
    if evidence_id not in nodes or not graph.get("acyclic", False):
        return []
    lineage = []
    seen = set()

    def walk(node):
        if node in seen:
            return
        seen.add(node)
        for parent in nodes[node].get("parents", []):
            if parent in nodes:
                walk(parent)
        lineage.append(node)

    walk(evidence_id)
    return lineage
