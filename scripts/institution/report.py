"""Evidence graph, reusable data manifests, briefs and interactive research view."""
from __future__ import annotations

import argparse
import hashlib
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import sys

from . import common


def projections(run, memory, root):
    sys.path.insert(0, str(root / "systems/oracle/src"))
    from oracle.graph import Edge, ResearchGraph
    from oracle.hypothesis_factory import Trigger, from_anomaly
    graph = ResearchGraph()
    hypotheses, models, datasets = [], [], {}
    for source in run.get("catalogue", []):
        source_id = "source:" + source["sha256"]
        datasets[source_id] = source
        graph.add_node(source_id, "dataset", label=source["label"], sha256=source["sha256"],
                       identity_status=source["identity_status"], price_basis=source["price_basis"])
    for key, record in memory["experiments"].items():
        source = record["source"]
        source_id = "source:" + source["sha256"]
        # Byte identity is immutable; source revision is kept on the experiment.
        if source_id not in graph.nodes:
            graph.add_node(source_id, "dataset", label=source["label"], sha256=source["sha256"],
                           identity_status=source["identity_status"], price_basis=source["price_basis"])
        datasets[source_id] = source
        experiment_node = "experiment:" + key
        graph.add_node(experiment_node, "experiment", label=record["outcome"],
                       outcome=record["outcome"], reasons=record["reasons"],
                       context_hash=record["context_hash"], observed_at=record["observed_at"],
                       run_id=record["run_id"], run_attempt=record["run_attempt"], **common.AUTHORITY)
        stamp = int(datetime.fromisoformat(record["observed_at"].replace("Z", "+00:00")).timestamp() * 1e9)
        graph.add_edge(Edge(source_id, experiment_node, "tested_on_development_only", stamp))
        choice = record.get("agenda_choice")
        if choice:
            planned = choice["hypothesis"]
            node = planned["hypothesis_id"]
            hypotheses.append({**planned, "stage": "preregistered_development_question", "experiment_id": key})
            graph.add_node(node, "hypothesis", label=planned["statement"], stage="preregistered_development_question")
            graph.add_edge(Edge(source_id, node, "raises_registered_question", planned["created_ns"]))
            graph.add_edge(Edge(node, experiment_node, "tested_by_registered_development_protocol", stamp))
        for hypothesis in record["hypotheses"]:
            hypothesis = {**hypothesis, "experiment_id": key, "source_hash": source["sha256"],
                          "experiment_outcome": record["outcome"]}
            hypotheses.append(hypothesis)
            node = hypothesis["hypothesis_id"]
            graph.add_node(node, "hypothesis", label=hypothesis["statement"], stage=hypothesis["stage"])
            graph.add_edge(Edge(source_id, node, "generated_exploratory_association", stamp))
            graph.add_edge(Edge(node, experiment_node, "challenged_by_family_tournament", stamp))
        for model in record["models"]:
            model = {**model, "experiment_id": key, "source_label": source["label"],
                     "source_hash": source["sha256"], "context_hash": record["context_hash"],
                     "outcome": record["outcome"], "selected_in_development": model["model"] == record["champion"],
                     "stage": common.PROTOCOL["stage"], **common.AUTHORITY}
            models.append(model)
            node = key + ":" + model["model"]
            graph.add_node(node, "model", label=model["model"], auc=model["metrics"]["auc"],
                           selected_in_development=model["selected_in_development"])
            graph.add_edge(Edge(experiment_node, node, "competed_in_purged_development", stamp))
    for connection in memory["connections"].values():
        node = "connection:" + connection["id"]
        graph.add_node(node, "cross_market", label=connection.get("state", "interrupted"), **connection)
        for side in ("left", "right"):
            source_id = "source:" + connection[side]
            if source_id in graph.nodes:
                graph.add_edge(Edge(source_id, node, "assessed_development_alignment", 0))
    for event in memory["events"].values():
        node = "event:" + event["id"]
        graph.add_node(node, "announcement", label=event["title"], **event)
        stamp = int(datetime.fromisoformat(event["first_observed_at"].replace("Z", "+00:00")).timestamp() * 1e9)
        hypothesis = from_anomaly(Trigger("official_announcement", stamp, event["source"], 0.0, 0.0, {},
                                         (event["id"],)), horizon="future evidence after observation")
        value = {**asdict(hypothesis), "stage": "untested_event_question", "event_id": event["id"],
                 "interpretation": "No aligned contemporaneous prices collected; no effect claim"}
        hypotheses.append(value)
        graph.add_node(hypothesis.hypothesis_id, "hypothesis", label=hypothesis.statement, stage=value["stage"])
        graph.add_edge(Edge(node, hypothesis.hypothesis_id, "raises_untested_question", stamp))
    envelope = {**common.AUTHORITY, "generated_at": common.now(), "memory_hash": memory["content_hash"]}
    models.sort(key=lambda m: (m["context_hash"] != (run.get("context") or {}).get("context_hash"),
                               -m["metrics"]["auc"], m["experiment_id"], m["model"]))
    return {
        "graph.json": common.seal({"schema": "icarus.institution.graph.v1", **envelope,
                                    "nodes": graph.nodes, "edges": [asdict(e) for e in graph.edges]}),
        "hypotheses.json": common.seal({"schema": "icarus.institution.hypotheses.v1", **envelope, "hypotheses": hypotheses}),
        "leaderboard.json": common.seal({"schema": "icarus.institution.leaderboard.v1", **envelope,
            "interpretation": "Within-source development comparisons; different sources are not comparable live PnL",
            "models": models}),
        "datasets.json": common.seal({"schema": "icarus.institution.datasets.v1", **envelope,
            "datasets": list(datasets.values()), "source_receipts": run["source_receipts"],
            "feed_receipts": run["feed_receipts"]}),
    }


def brief(run, memory):
    counts = {s: sum(e["outcome"] == s for e in memory["experiments"].values())
              for s in ("rejected", "watch", "interrupted", "source_rejected")}
    queue = run.get("queue") or {}
    lines = ["# ICARUS research brief", "", f"Latest cycle: **{run['state']}** at {run['finished_at'] or run['started_at']}", "",
             f"Memory holds {len(memory['experiments'])} source/protocol experiments: "
             f"{counts['rejected']} rejected, {counts['watch']} development watch, "
             f"{counts['source_rejected']} unsuitable sources, {counts['interrupted']} interrupted computations.", "",
             f"This cycle tested {queue.get('tested', 0)} sources; {queue.get('pending_after', 'unknown')} remain queued. "
             f"{queue.get('already_remembered', 0)} exact-context sources were remembered.", "",
             f"{len(memory['events'])} official announcements retained with first-observation times. "
             "Their market effects remain untested.", "",
             f"{len(memory['connections'])} cross-source alignment diagnostics retained. "
             "Only exact shared unique timestamps and past row lags are allowed; missing alignment is recorded.", "",
             "## Challenges and competing explanations", "",
             "Lagged bar features compete against training prevalence and four existing model families. "
             "A circular-shift control challenges alignment; moving-block uncertainty challenges sampling luck; "
             "higher costs challenge friction assumptions; time slices challenge stability; fixed feature "
             "ablation challenges dependence on the return family. All reuse development evidence.", ""]
    for experiment in run["experiments"]:
        lines += [f"- **{experiment['source']['label']}** — {experiment['outcome']}; "
                  f"selected development model: {experiment['champion'] or 'none'}. "
                  f"Reasons: {', '.join(experiment['reasons']) or 'registered development challenges passed'}. "
                  f"Source SHA256 `{experiment['source']['sha256']}`."]
    if run["reasons"]:
        lines += ["", "Incomplete evidence: " + ", ".join(run["reasons"]) + "."]
    if queue.get("pending_after") == 0:
        lines += ["", "The current context queue is exhausted. The next cycle watches for changed corpus bytes and new announcements."]
    lines += ["", "## Authority and limits", "",
              "Historical development paper proxy only. Filename symbol identity is unverified; chart prices "
              "are not execution fills. The protected tail is reserved, with no validation, promotion or "
              "broker orders. No event-price causality or live engine state is observed. A watch entry is "
              "a research lead, not a confirmed edge.", "",
              f"[Cycle evidence](https://github.com/{common.REPOSITORY}/actions/runs/{run['run_id']})", ""]
    return "\n".join(lines)


def html(run, memory, api):
    # All source strings go through JSON escaping and DOM textContent.
    data = common.canonical({"run": run, "memory": memory, "graph": api["graph.json"],
                             "models": api["leaderboard.json"]["models"]}).decode().replace("<", "\\u003c").replace("&", "\\u0026")
    return TEMPLATE.replace("__DATA__", data)


def build(output, root=Path.cwd()):
    run = common.validate(common.read_json((output / "run.json").read_bytes()), "icarus.institution.run.v1")
    memory_path = output / "memory.json"
    memory = common.validate(common.read_json(memory_path.read_bytes()), "icarus.institution.memory.v1") if memory_path.exists() else common.empty_memory()
    api = projections(run, memory, root)
    for name, value in api.items():
        common.write_json(output / name, value)
    (output / "brief.md").write_text(brief(run, memory))
    content = html(run, memory, api).encode()
    (output / "index.html").write_bytes(content)
    common.write_json(output / "view.json", common.seal({"schema": "icarus.institution.view.v1",
        **common.AUTHORITY, "run_hash": run["content_hash"], "html_sha256": hashlib.sha256(content).hexdigest(),
        "run_id": run["run_id"], "run_attempt": run["run_attempt"]}))
    return run


TEMPLATE = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ICARUS Research Institution</title><style>
:root{color-scheme:dark;--bg:#08111c;--panel:#101e2d;--border:#243b50;--muted:#9ab1c8;--accent:#75e0bb}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#ecf5ff;font:15px/1.6 system-ui}main{max-width:1260px;margin:auto;padding:32px 24px}h1{font-size:clamp(28px,5vw,48px);line-height:1.1;margin:10px 0}h2{font-size:20px}p{color:var(--muted)}small{color:var(--muted)}a{color:var(--accent)}.eyebrow{color:var(--accent);letter-spacing:.15em;font-size:12px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:24px 0}.stat,.panel{background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:20px}.stat strong{display:block;font-size:30px}.toolbar{display:flex;gap:12px;margin:18px 0;flex-wrap:wrap}input,select,button{font:inherit;color:inherit;background:var(--panel);border:1px solid var(--border);padding:10px;border-radius:8px}input{flex:1;min-width:180px}.layout{display:grid;grid-template-columns:1.2fr 1fr;gap:16px}.scroll{max-height:470px;overflow:auto}.panel{min-width:0}.item{overflow-wrap:anywhere;display:block;width:100%;text-align:left;margin:7px 0;cursor:pointer}.item:hover{border-color:var(--accent)}.tag{font-size:12px;color:var(--accent)}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.6 ui-monospace;color:#bed0e3}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:10px;border-bottom:1px solid var(--border)}.table-wrap{overflow:auto}.warning{border-left:3px solid #f6cb78;padding-left:16px}svg{width:100%;min-height:240px}svg text{fill:#d9e9f7;font-size:12px}svg line{stroke:#44647e;stroke-width:2}svg circle{fill:#75e0bb}button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid var(--accent)}@media(max-width:760px){main{padding:20px 14px}.stats{grid-template-columns:repeat(2,1fr)}.layout{grid-template-columns:1fr}.panel{padding:14px}}
</style></head><body><main><div class="eyebrow">ICARUS / AUTONOMOUS RESEARCH</div><h1>Ideas must earn their evidence.</h1><p>Daily discovery, competing explanations, a development tournament, and a memory that keeps failures.</p><p id="cycle"></p><div class="stats" id="stats"></div><p class="warning">Development paper proxy. Protected holdouts remain reserved. No production promotion or live orders. Official announcement effects remain untested.</p>
<div class="toolbar"><input id="search" aria-label="Search evidence" placeholder="Search a source, model, announcement, or failure"><select id="kind" aria-label="Evidence type"><option value="">All evidence</option><option value="experiment" selected>Experiments</option><option value="announcement">Announcements</option><option value="hypothesis">Hypotheses</option><option value="dataset">Datasets</option><option value="model">Models</option></select></div>
<div class="layout"><section class="panel"><h2>Evidence graph</h2><p>Choose a record to inspect its source, question, challenge, and result.</p><div id="records" class="scroll"></div></section><section class="panel"><h2 id="detail-title">Trace the evidence</h2><svg id="trace" viewBox="0 0 500 250" role="img" aria-label="Selected evidence relationships"></svg><pre id="detail">Select a record.</pre></section></div>
<section class="panel" style="margin-top:16px"><h2>Model tournament</h2><p>Exploratory AUC and chart-price return diagnostics with unverified instrument identities. Compare families within the same source and protocol. Span describes the source-row range, not additional independent observations.</p><div class="table-wrap"><table><thead><tr><th>Source</th><th>Family</th><th>AUC</th><th>Folds</th><th>Sampled rows / span</th><th>Chart return</th><th>Source outcome</th></tr></thead><tbody id="models"></tbody></table></div></section>
<p><a href="brief.md">Research brief</a> · <a href="latest.json">Run API</a> · <a href="graph.json">Graph API</a> · <a href="hypotheses.json">Hypotheses API</a> · <a href="leaderboard.json">Tournament API</a> · <a href="datasets.json">Dataset manifests</a> · <a href="memory.json">Durable memory</a></p></main>
<script>const data=__DATA__;const $=id=>document.getElementById(id);const nodes=data.graph.nodes,edges=data.graph.edges;const counts={};Object.values(data.memory.experiments).forEach(e=>counts[e.outcome]=(counts[e.outcome]||0)+1);$('cycle').textContent=`Latest cycle: ${data.run.state} · ${data.run.finished_at||data.run.started_at} · ${(data.run.queue||{}).pending_after??'unknown'} sources queued`;
for(const [label,value] of [['Experiments',Object.keys(data.memory.experiments).length],['Failed ideas remembered',(counts.rejected||0)+(counts.source_rejected||0)],['Development watch',counts.watch||0],['Announcements',Object.keys(data.memory.events).length]]){const box=document.createElement('div');box.className='stat';const n=document.createElement('strong');n.textContent=value;box.append(n,document.createTextNode(label));$('stats').append(box)}
function show(id){const node=nodes[id];$('detail-title').textContent=node.kind+' / evidence';const linked=edges.filter(e=>e.source===id||e.target===id);$('detail').textContent=JSON.stringify({id,...node,relationships:linked},null,2);const svg=$('trace');svg.replaceChildren();const ns='http://www.w3.org/2000/svg';const points=[{id,x:250,y:45},...linked.slice(0,5).map((e,i)=>({id:e.source===id?e.target:e.source,x:50+i*100,y:180,relation:e.relation}))];for(const point of points.slice(1)){const line=document.createElementNS(ns,'line');line.setAttribute('x1',250);line.setAttribute('y1',45);line.setAttribute('x2',point.x);line.setAttribute('y2',point.y);svg.append(line)}for(const point of points){const g=document.createElementNS(ns,'g'),c=document.createElementNS(ns,'circle'),t=document.createElementNS(ns,'text');c.setAttribute('cx',point.x);c.setAttribute('cy',point.y);c.setAttribute('r',8);t.setAttribute('x',point.x);t.setAttribute('y',point.y+25);t.setAttribute('text-anchor','middle');t.textContent=nodes[point.id].label.slice(0,12);const title=document.createElementNS(ns,'title');title.textContent=point.relation||nodes[point.id].label;g.append(c,t,title);g.style.cursor='pointer';g.addEventListener('click',()=>show(point.id));svg.append(g)}}
function render(){const query=$('search').value.toLowerCase(),kind=$('kind').value;const selected=Object.entries(nodes).filter(([id,n])=>(!kind||n.kind===kind)&&JSON.stringify(n).toLowerCase().includes(query));$('records').replaceChildren();for(const [id,n] of selected.slice(0,150)){const b=document.createElement('button');b.className='item';const tag=document.createElement('div');tag.className='tag';tag.textContent=n.kind;b.append(tag,document.createTextNode(n.label));b.addEventListener('click',()=>show(id));$('records').append(b)}if(!selected.length)$('records').textContent='No matching evidence.'}
for(const m of data.models.slice(0,120)){const tr=document.createElement('tr');for(const value of [m.source_label,m.model,m.metrics.auc.toFixed(3),m.folds,m.coverage?m.coverage.sampled_rows+' / '+m.coverage.source_row_span:'legacy',(m.metrics.cumulative_return*100).toFixed(2)+'%',m.outcome]){const td=document.createElement('td');td.textContent=value;tr.append(td)}$('models').append(tr)}$('search').addEventListener('input',render);$('kind').addEventListener('change',render);render();const first=Object.keys(nodes).find(k=>nodes[k].kind==='experiment');if(first)show(first);
</script></body></html>'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("_institution"))
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()
    run = build(args.output)
    if args.enforce and run["state"] != "complete":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
