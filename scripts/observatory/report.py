"""Normalize existing engineering evidence into a self-contained proof atlas.

Only the Observatory envelope is versioned; the native validator is unchanged.
Incomplete observations never confer success or execution authority.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import re
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCHEMA = 'icarus.observatory.run.v1'
MAX_FILE = 2_000_000
EVIDENCE_FILES = ('collection.json', 'hub.json', 'validation_report.json',
                  'hub.stdout.log', 'hub.stderr.log', 'validation.stdout.log', 'validation.stderr.log')


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('utf-8')


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def seal_receipt(receipt: dict) -> dict:
    out = deepcopy(receipt)
    for finding in out.get('findings', {}).values():
        finding.pop('finding_hash', None)
        finding['finding_hash'] = digest(finding)
    out.pop('receipt_hash', None)
    out['receipt_hash'] = digest(out)
    return out


def instant(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError('timestamp missing')
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('timestamp needs timezone')
    return dt.astimezone(timezone.utc)


def valid_counts(value: object) -> bool:
    return (isinstance(value, dict) and
            all(k in {'passed', 'failed', 'errors', 'skipped', 'xfailed', 'xpassed', 'deselected'}
                and type(v) is int and v >= 0 for k, v in value.items()))


def successful_counts(counts: dict) -> bool:
    return counts.get('passed', 0) > 0 and not any(counts.get(k, 0) for k in ('failed', 'errors', 'deselected'))


def normalize(collection: dict, native: dict | None, hub: dict | None) -> dict:
    """Fail closed when current evidence is absent, stale, or contradictory."""
    meta = collection if isinstance(collection, dict) else {}
    keys = ('run_id', 'run_attempt', 'event', 'repository', 'ref', 'commit', 'run_url',
            'started_at', 'finished_at', 'python', 'platform', 'validator_exit_code', 'hub_exit_code')
    out = {k: meta.get(k) for k in keys}
    inventory = meta.get('inventory', {})
    if not isinstance(inventory, dict):
        inventory = {}
    out.update(schema=SCHEMA, inventory=deepcopy(inventory), dependencies=meta.get('dependencies', []),
               findings={}, reasons=[], evidence_hashes={}, previous_receipt_hash=None,
               execution_authorized=False, production_authorized=False, live_engine='not_observed')
    incomplete = out['reasons']
    if meta.get('schema') != 'icarus.observatory.collection.v1':
        incomplete.append('Collection envelope missing or unsupported.')
    errors = meta.get('collection_errors', [])
    if not isinstance(errors, list) or any(not isinstance(e, str) for e in errors):
        incomplete.append('Invalid collection errors.')
    else:
        incomplete.extend(e[:4000] for e in errors)
    for k in ('validator_exit_code', 'hub_exit_code'):
        if type(meta.get(k)) is not int:
            incomplete.append(f'{k} not observed.')
    for k in ('validator_timed_out', 'hub_timed_out'):
        if type(meta.get(k)) is not bool or meta[k]:
            incomplete.append(f'{k}: interrupted or unobserved.')
    try:
        started, finished = instant(meta.get('started_at')), instant(meta.get('finished_at'))
        if finished < started:
            raise ValueError('finish before start')
    except ValueError:
        started = finished = None
        incomplete.append('Invalid collection clock.')
    names = inventory.get('systems', [])
    scripts = inventory.get('adversarial', [])
    links = inventory.get('connections', {})
    safe_name = re.compile(r'[a-zA-Z0-9_.-]{1,120}\Z')
    def names_ok(items):
        return (isinstance(items, list) and bool(items) and
                all(isinstance(n, str) and safe_name.fullmatch(n) for n in items) and
                len(set(items)) == len(items))
    if not names_ok(names):
        incomplete.append('System inventory missing or invalid.')
        names = [n for n in names if isinstance(n, str) and safe_name.fullmatch(n)] if isinstance(names, list) else []
    if not names_ok(scripts):
        incomplete.append('Adversarial inventory missing or invalid.')
        scripts = [n for n in scripts if isinstance(n, str) and safe_name.fullmatch(n)] if isinstance(scripts, list) else []
    if not isinstance(links, dict) or not links or any(not isinstance(n, str) or not safe_name.fullmatch(n) for n in links):
        incomplete.append('Connection inventory missing or invalid.')
        links = {}
    names, scripts = sorted(set(names)), sorted(set(scripts))
    links = deepcopy(links)
    for name, link in links.items():
        if (not isinstance(link, dict) or not isinstance(link.get('systems'), list) or
                any(n not in names for n in link.get('systems', [])) or
                not isinstance(link.get('contract'), str)):
            incomplete.append(f'Invalid connection declaration: {name}.')
            links[name] = {'systems': [], 'contract': 'Invalid declaration; not observed.'}
    coverage = deepcopy(inventory.get('coverage', {}))
    if not isinstance(coverage, dict) or set(coverage) != set(names):
        incomplete.append('System coverage inventory incomplete.')
    observed_coverage = coverage if isinstance(coverage, dict) else {}
    coverage = {}
    for name in names:
        entry = observed_coverage.get(name)
        valid = isinstance(entry, dict)
        if valid and entry.get('status') == 'connected':
            valid = (isinstance(entry.get('connections'), list) and bool(entry['connections']) and
                     all(isinstance(n, str) and n in links for n in entry['connections']))
        elif valid and entry.get('status') == 'standalone':
            valid = isinstance(entry.get('reason'), str) and bool(entry['reason'])
        else:
            valid = False
        if not valid:
            incomplete.append(f'{name}: coverage declaration invalid.')
            entry = {'status': 'not_observed', 'reason': 'Coverage declaration invalid.'}
        coverage[name] = entry
    out['inventory'] = dict(systems=names, adversarial=scripts, connections=links, coverage=coverage)

    report = native if isinstance(native, dict) else {}
    if not report:
        incomplete.append('Fresh validator report not observed.')
    else:
        try:
            generated = instant(report.get('generated_at'))
            if started is None or generated < started - timedelta(seconds=2) or generated > finished + timedelta(seconds=2):
                raise ValueError('stale')
        except ValueError:
            incomplete.append('Native report timestamp is stale or invalid.')
    groups = {
        'suite': (names, report.get('systems', {}), 'passed'),
        'compile': (names, report.get('compile', {}), 'ok'),
        'adversarial': (scripts, report.get('ascension_adversarial', {}), 'ok'),
        'connection': (list(links), report.get('connections', {}).get('connections', {})
                       if isinstance(report.get('connections'), dict) else {}, 'ok'),
    }

    def finding(key, rec, flag, systems, suite=False):
        state, counts, seconds, diagnostic = 'not_observed', None, None, ''
        if isinstance(rec, dict) and type(rec.get(flag)) is bool:
            state = 'pass' if rec[flag] else 'fail'
            diagnostic = json.dumps(rec, sort_keys=True, ensure_ascii=True)[:4000]
            if suite:
                counts = rec.get('counts')
                seconds = rec.get('seconds')
                if (not valid_counts(counts) or type(rec.get('timed_out')) is not bool or
                        type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0):
                    state, counts, seconds = 'not_observed', None, None
                    incomplete.append(f'{key}: invalid suite measurements.')
                elif state == 'pass' and (not successful_counts(counts) or rec['timed_out']):
                    state = 'not_observed'
                    incomplete.append(f'{key}: passing claim contradicts test counts or timeout.')
        else:
            incomplete.append(f'{key}: boolean result not observed.')
        out['findings'][key] = dict(id=key, state=state, counts=counts, seconds=seconds,
                                    diagnostic=diagnostic, systems=systems,
                                    run_id=out['run_id'], commit=out['commit'])

    for kind, (expected, actual, flag) in groups.items():
        if not isinstance(actual, dict):
            actual = {}
        if set(actual) != set(expected):
            incomplete.append(f'{kind}: observed inventory does not match source inventory.')
        for name in sorted(expected):
            systems = [name] if kind in ('suite', 'compile') else (
                links.get(name, {}).get('systems', []) if isinstance(links.get(name), dict) else [])
            finding(f'{kind}/{name}', actual.get(name), flag, systems, suite=kind == 'suite')

    h = deepcopy(hub) if isinstance(hub, dict) else {}
    h['passed'] = (type(h.get('returncode')) is int and h['returncode'] == 0 and
                   h.get('timed_out') is False and valid_counts(h.get('counts')) and
                   successful_counts(h['counts']))
    if not hub or h.get('returncode') != meta.get('hub_exit_code'):
        incomplete.append('Hub test process was not observed consistently.')
    finding('hub/tests', h if hub else None, 'passed', [], suite=True)

    suites_ok = all(v['state'] == 'pass' for k, v in out['findings'].items() if k.startswith(('suite/', 'compile/', 'adversarial/')))
    connections_ok = all(v['state'] == 'pass' for k, v in out['findings'].items() if k.startswith('connection/'))
    for value, expected, label in ((report.get('all_suites_and_compile_ok'), suites_ok, 'suite aggregate'),
                                    (report.get('connections_ok'), connections_ok, 'connection aggregate'),
                                    (report.get('connections', {}).get('ok') if isinstance(report.get('connections'), dict) else None,
                                     connections_ok, 'nested connection aggregate')):
        if type(value) is not bool or value != expected:
            incomplete.append(f'{label} missing or contradictory.')
    failed = [k for k, v in out['findings'].items() if v['state'] == 'fail']
    native_failed = any(k != 'hub/tests' for k in failed)
    if type(meta.get('validator_exit_code')) is int and ((meta['validator_exit_code'] == 0) == native_failed):
        incomplete.append('Validator exit code contradicts native evidence.')
    out['state'] = 'incomplete' if incomplete else 'unhealthy' if failed else 'healthy'
    out['reasons'] = list(dict.fromkeys(incomplete)) + ([f'Failed checks: {", ".join(failed)}'] if failed else [])
    out['environment_hash'] = digest({'python': out['python'], 'platform': out['platform'], 'dependencies': out['dependencies']})
    return seal_receipt(out)


def compare(current: dict, previous: dict | None) -> dict:
    result = dict(baseline_run_id=previous.get('run_id') if previous else None,
                  first_observation=previous is None, regressions=[], continuing_failures=[],
                  recoveries=[], lost_observations=[], inventory_added=[], inventory_removed=[], measurement_changes=[])
    now, old = current.get('findings', {}), previous.get('findings', {}) if previous else {}
    result['inventory_added'] = sorted(set(now) - set(old))
    result['inventory_removed'] = sorted(set(old) - set(now))
    result['lost_observations'] = list(result['inventory_removed'])
    for key in sorted(set(now) & set(old)):
        a, b = old[key].get('state'), now[key].get('state')
        if a == 'pass' and b == 'fail':
            result['regressions'].append(key)
        elif a == b == 'fail':
            result['continuing_failures'].append(key)
        elif a == 'fail' and b == 'pass':
            result['recoveries'].append(key)
        elif a != 'not_observed' and b == 'not_observed':
            result['lost_observations'].append(key)
        for field in ('counts', 'seconds'):
            if old[key].get(field) != now[key].get(field):
                result['measurement_changes'].append(dict(id=key, field=field, before=old[key].get(field), after=now[key].get(field)))
    result['environment_changed'] = bool(previous and current.get('environment_hash') != previous.get('environment_hash'))
    return result


def safe_url(receipt: dict) -> str:
    repo = receipt.get('repository', '')
    run_id = receipt.get('run_id')
    if isinstance(repo, str) and re.fullmatch(r'[\w.-]+/[\w.-]+', repo) and type(run_id) is int and run_id >= 0:
        return f'https://github.com/{repo}/actions/runs/{run_id}'
    return '#'


def markdown_text(value: object) -> str:
    # Entity-encode punctuation to prevent links, mentions, HTML, and table breaks.
    return ''.join(c if c.isalnum() or c in ' ./:-_' else f'&#{ord(c)};' for c in str(value)).replace('\n', ' ')


def render_markdown(receipt: dict, delta: dict) -> str:
    lines = ['# ICARUS Observatory', '', f"**{receipt['state'].upper()}** · [Actions run]({safe_url(receipt)})",
             '', f"Source: `{receipt.get('commit')}` · Finished: {markdown_text(receipt.get('finished_at'))}",
             '', 'Engineering fixtures only. Live engine: not observed. Execution and production authority: false.', '',
             f"Receipt: `{receipt['receipt_hash']}`", '', '## Changes since last complete run', '']
    if delta['first_observation']:
        lines.append('First observation; no previous complete baseline.')
    for label in ('regressions', 'continuing_failures', 'recoveries', 'lost_observations', 'inventory_added', 'inventory_removed'):
        items = delta[label]
        if items:
            lines.append(f"- {label.replace('_', ' ').title()}: {', '.join(markdown_text(x) for x in items)}")
    if delta['environment_changed']:
        lines.append('- Installed environment changed; comparisons are descriptive.')
    if delta['measurement_changes']:
        lines.extend(['', '### Measurement changes', '', 'Count and duration changes are descriptive, not proof of regression.', ''])
        for change in delta['measurement_changes']:
            before = markdown_text(json.dumps(change['before'], sort_keys=True))
            after = markdown_text(json.dumps(change['after'], sort_keys=True))
            lines.append(f"- {markdown_text(change['id'])} {change['field']}: {before} → {after}")
    lines.extend(['', '## Evidence', '', '| Check | State | Passed tests | Seconds |', '|---|---|---:|---:|'])
    for key, f in sorted(receipt['findings'].items()):
        count = f['counts'].get('passed', 0) if isinstance(f['counts'], dict) else 'not recorded'
        lines.append(f"| {markdown_text(key)} | {f['state']} | {count} | {f['seconds'] if f['seconds'] is not None else 'not recorded'} |")
    lines.extend(['', '## Findings', ''])
    for reason in receipt['reasons']:
        lines.append('- ' + markdown_text(reason))
    for key, f in sorted(receipt['findings'].items()):
        if f['state'] != 'pass' or f['diagnostic']:
            lines.extend(['', f"**{markdown_text(key)}**", '', markdown_text(f['diagnostic'])])
    return '\n'.join(lines) + '\n'


def render_html(receipt: dict, delta: dict, history: list | None = None, *, durable: bool = False) -> str:
    esc = lambda value: html.escape(str(value), quote=True)
    findings = receipt['findings']
    n_pass = sum(f['state'] == 'pass' for f in findings.values())
    n_fail = sum(f['state'] == 'fail' for f in findings.values())
    n_missing = len(findings) - n_pass - n_fail
    cards = []
    for name, coverage in sorted(receipt.get('inventory', {}).get('coverage', {}).items()):
        related = [f for f in findings.values() if name in f.get('systems', [])]
        state = ('not_observed' if not related or any(f['state'] == 'not_observed' for f in related)
                 else 'fail' if any(f['state'] == 'fail' for f in related) else 'pass')
        why = coverage.get('reason') or ', '.join(coverage.get('connections', [])) or coverage.get('status', 'not recorded')
        cards.append(f'<article class="system {state}"><div class="eyebrow">{esc(coverage.get("status"))}</div><h3>{esc(name)}</h3><p>{esc(why)}</p><span class="badge {state}">{esc(state.replace("_", " "))}</span></article>')
    rows = []
    for key, f in sorted(findings.items()):
        counts = f.get('counts')
        measurement = f"{counts.get('passed', 0)} passed" if isinstance(counts, dict) else 'counts not recorded'
        duration = f"{f['seconds']}s" if f.get('seconds') is not None else 'time not recorded'
        rows.append(f'<details class="finding" data-state="{esc(f["state"])}"><summary><span class="badge {esc(f["state"])}">{esc(f["state"].replace("_", " "))}</span><strong>{esc(key)}</strong><span>{esc(measurement)} · {esc(duration)}</span></summary><div class="finding-body"><pre>{esc(f.get("diagnostic", ""))}</pre><div class="hash">Finding receipt {esc(f.get("finding_hash"))}</div></div></details>')
    changes = []
    for key in ('regressions', 'continuing_failures', 'recoveries', 'lost_observations', 'inventory_added', 'inventory_removed'):
        if delta[key]:
            changes.append(f'<li><strong>{esc(key.replace("_", " "))}</strong><span>{esc(", ".join(delta[key]))}</span></li>')
    if not changes:
        changes = ['<li>No previous complete baseline.</li>' if delta['first_observation'] else '<li>No state or inventory changes since the last complete run.</li>']
    if delta['environment_changed']:
        changes.append('<li><strong>Installed environment changed</strong><span>Dependencies or interpreter changed; comparisons remain descriptive.</span></li>')
    if delta['measurement_changes']:
        measurements = ''.join(f'<li><strong>{esc(c["id"])} {esc(c["field"])}</strong><span>{esc(json.dumps(c["before"], sort_keys=True))} → {esc(json.dumps(c["after"], sort_keys=True))}</span></li>' for c in delta['measurement_changes'])
        changes.append(f'<li><details><summary>Measurement changes ({len(delta["measurement_changes"])})</summary><p>Descriptive count and duration changes.</p><ul>{measurements}</ul></details></li>')
    trail = []
    for row in (history or [])[-90:]:
        state = row.get('state', 'incomplete')
        url = safe_url({**receipt, 'run_id': row.get('run_id')})
        trail.append(f'<a class="tick {esc(state)}" href="{esc(url)}" title="Run {esc(row.get("run_id"))}: {esc(state)}">{esc(row.get("run_id"))}</a>')
    reasons = ''.join(f'<li>{esc(reason)}</li>' for reason in receipt['reasons']) or '<li>All expected engineering checks observed and passed.</li>'
    body = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>ICARUS Observatory · Proof atlas</title>
<style>
:root{color-scheme:dark;--bg:#09101a;--panel:#101c2b;--line:#24364b;--text:#e8eff8;--muted:#a0b3c9;--green:#67ddb1;--red:#ff8e94;--amber:#f8cf79}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 75% 0,#183849 0,transparent 48%),var(--bg);font:15px/1.6 system-ui,sans-serif;color:var(--text)}main{max-width:1200px;margin:auto;padding:48px 24px}a{color:var(--green)}header{display:flex;justify-content:space-between;gap:24px;border-bottom:1px solid var(--line);padding-bottom:32px}.eyebrow{color:var(--muted);text-transform:uppercase;letter-spacing:.18em;font-size:11px}h1{font-size:clamp(36px,6vw,64px);line-height:1.1;letter-spacing:-.05em;margin:12px 0}h2{font-size:24px;letter-spacing:-.03em}p{color:var(--muted)}.badge{display:inline-block;font-size:11px;text-transform:uppercase;letter-spacing:.06em;border:1px solid;padding:3px 9px;border-radius:20px;white-space:nowrap}.pass,.healthy{color:var(--green)}.fail,.unhealthy{color:var(--red)}.not_observed,.incomplete{color:var(--amber)}.meta{max-width:340px;overflow-wrap:anywhere;font-size:13px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:28px 0}.stat{background:var(--panel);border:1px solid var(--line);padding:20px;border-radius:12px}.stat b{display:block;font-size:32px}.stat span{color:var(--muted)}.systems{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}.system{border:1px solid var(--line);background:#101c2bc9;padding:20px;border-radius:12px}.system h3{font-size:22px;margin:8px 0}.system p{font-size:12px;min-height:40px}.changes{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin:32px 0}.box{border:1px solid var(--line);border-radius:12px;padding:24px;background:#101c2b88}.box ul{padding-left:18px}.box li{margin-bottom:12px;overflow-wrap:anywhere}.box li span{display:block;color:var(--muted)}.toolbar{display:flex;gap:12px;margin-bottom:12px}input,select{font:inherit;color:var(--text);background:var(--panel);border:1px solid var(--line);padding:10px;border-radius:8px}input{flex:1}.finding{border:1px solid var(--line);border-radius:9px;margin-bottom:8px;background:var(--panel)}summary{cursor:pointer;display:flex;align-items:center;gap:16px;padding:16px}summary strong{flex:1}summary>span:last-child{font-size:12px;color:var(--muted)}.finding-body{padding:0 20px 20px}pre{white-space:pre-wrap;overflow-wrap:anywhere;color:var(--muted);font:12px/1.6 ui-monospace,monospace}.hash{font:11px/1.7 ui-monospace,monospace;overflow-wrap:anywhere;color:var(--muted)}.timeline{display:flex;gap:4px;overflow:auto;padding:10px 0}.tick{min-width:10px;width:14px;height:36px;overflow:hidden;font-size:0;border-radius:3px;background:var(--amber);flex-shrink:0}.tick.healthy{background:var(--green)}.tick.unhealthy{background:var(--red)}footer{margin-top:32px;border-top:1px solid var(--line);padding-top:20px;color:var(--muted);font-size:12px}[hidden]{display:none!important}@media(max-width:650px){header{display:block}.stats{grid-template-columns:repeat(2,1fr)}.changes{grid-template-columns:1fr}summary{flex-wrap:wrap}.toolbar{flex-wrap:wrap}main{padding:28px 16px}}
</style></head><body><main>'''
    body += f'<header><div><div class="eyebrow">ICARUS / engineering evidence</div><h1>Observatory</h1><p>A proof atlas for the system of systems.</p><span class="badge {esc(receipt["state"])}">{esc(receipt["state"])}</span></div><div class="meta"><a href="{esc(safe_url(receipt))}">Open Actions run {esc(receipt.get("run_id"))}</a><p>Finished <time id="observed" data-time="{esc(receipt.get("finished_at"))}">{esc(receipt.get("finished_at"))}</time><br><span id="age">Observation age unavailable</span></p><div class="hash">Source {esc(receipt.get("commit"))}</div><p><a href="run.json">Run JSON</a> · <a href="SHA256SUMS">Verify bundle</a></p></div></header>'
    body += f'<div class="stats"><div class="stat"><b>{len(receipt.get("inventory",{}).get("systems",[]))}</b><span>Subsystems observed</span></div><div class="stat pass"><b>{n_pass}</b><span>Checks passed</span></div><div class="stat fail"><b>{n_fail}</b><span>Checks failed</span></div><div class="stat not_observed"><b>{n_missing}</b><span>Checks not observed</span></div></div>'
    body += f'<h2>System map</h2><p>Connections show declared dependencies. Their fixtures do not measure live engine or provider availability.</p><div class="systems">{"".join(cards)}</div>'
    body += f'<div class="changes"><section class="box"><div class="eyebrow">Compared with complete run {esc(delta["baseline_run_id"])}</div><h2>What changed</h2><ul>{"".join(changes)}</ul></section><section class="box"><div class="eyebrow">Current run</div><h2>Evidence assessment</h2><ul>{reasons}</ul></section></div>'
    body += f'<h2>Observation history</h2><p>Green: healthy · Red: failed checks · Amber: incomplete. Measurements describe this checkout and its installed dependencies.</p><div class="timeline">{"".join(trail) or "First retained observation."}</div><h2>Inspect the proofs</h2><div class="toolbar"><input id="search" aria-label="Search checks" placeholder="Search systems, contracts, diagnostics"><select id="filter" aria-label="Filter check status"><option value="all">All checks</option><option value="fail">Failed</option><option value="not_observed">Not observed</option><option value="pass">Passed</option></select></div>{"".join(rows)}'
    body += f'<footer>Local engineering fixtures only. Live engine: not observed. Execution authorized: false. Production authorized: false.<br>Hashes expose content changes; they are not signatures or profitability evidence.<div class="hash">Receipt {esc(receipt["receipt_hash"])}</div></footer>'
    if durable:
        body = body.replace('href="run.json"', 'href="latest.json"').replace('href="SHA256SUMS"', 'href="index.json"').replace('Verify bundle</a>', 'History index</a>')
    body = body.replace('Subsystems observed</span>', 'Subsystems tracked</span>')
    body += '''</main><script>
const age=document.getElementById('age');const dt=Date.parse(document.getElementById('observed').dataset.time);function refreshAge(){const hours=(Date.now()-dt)/3600000;age.textContent=Number.isFinite(hours)?(hours>48?'STALE · ':'')+Math.max(0,hours).toFixed(1)+' hours since observation':'Observation time unavailable';age.style.color=hours>48?'var(--amber)':'var(--muted)'}refreshAge();setInterval(refreshAge,60000);function filter(){const q=document.getElementById('search').value.toLowerCase();const state=document.getElementById('filter').value;for(const row of document.querySelectorAll('.finding'))row.hidden=!(row.textContent.toLowerCase().includes(q)&&(state==='all'||row.dataset.state===state))}document.getElementById('search').addEventListener('input',filter);document.getElementById('filter').addEventListener('change',filter);
</script></body></html>'''
    return body


def write_bundle(receipt: dict, out: Path, baseline: dict | None = None, history: list | None = None) -> None:
    out.mkdir(parents=True, exist_ok=True)
    current = deepcopy(receipt)
    current['evidence_hashes'] = {name: hashlib.sha256((out / name).read_bytes()).hexdigest()
                                  for name in EVIDENCE_FILES if (out / name).is_file()
                                  and not (out / name).is_symlink() and (out / name).stat().st_size <= MAX_FILE}
    current = seal_receipt(current)
    delta = compare(current, baseline)
    products = {'run.json': canonical_bytes(current) + b'\n',
                'comparison.json': canonical_bytes(delta) + b'\n',
                'summary.md': render_markdown(current, delta).encode(),
                'index.html': render_html(current, delta, history).encode()}
    for name, content in products.items():
        if (out / name).is_symlink():
            raise ValueError('Bundle output must not contain symbolic links.')
        (out / name).write_bytes(content)
    names = sorted(set(products) | set(current['evidence_hashes']))
    (out / 'SHA256SUMS').write_text(''.join(f'{hashlib.sha256((out/name).read_bytes()).hexdigest()}  {name}\n' for name in names))


def read_json(path: Path) -> dict | None:
    def unique_pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError('Duplicate JSON key.')
            value[key] = item
        return value
    try:
        if path.is_symlink() or path.stat().st_size > MAX_FILE:
            return None
        value = json.loads(path.read_text(), object_pairs_hook=unique_pairs,
                           parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
        return value if isinstance(value, dict) else None
    except (OSError, UnicodeError, ValueError, RecursionError):
        return None


def fallback_metadata() -> dict:
    def number(key, default):
        try:
            return int(os.environ.get(key, default))
        except ValueError:
            return default
    now = datetime.now(timezone.utc).isoformat()
    repo = os.environ.get('GITHUB_REPOSITORY', 'local/checkout')
    run_id = number('GITHUB_RUN_ID', 0)
    return dict(schema='icarus.observatory.collection.v1', run_id=run_id,
                run_attempt=number('GITHUB_RUN_ATTEMPT', 1), event=os.environ.get('GITHUB_EVENT_NAME', 'local'),
                repository=repo, ref=os.environ.get('GITHUB_REF', 'local'), commit=os.environ.get('GITHUB_SHA', ''),
                run_url=f'https://github.com/{repo}/actions/runs/{run_id}', started_at=now, finished_at=now,
                python='not_observed', platform='not_observed',
                inventory={'systems': [], 'connections': {}, 'adversarial': [], 'coverage': {}},
                collection_errors=['Collection artifact was not available.'], dependencies=[])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--enforce', action='store_true')
    args = parser.parse_args(argv)
    if args.enforce:
        saved = read_json(args.input / 'run.json')
        return 0 if saved and saved.get('state') == 'healthy' else 1
    meta = read_json(args.input / 'collection.json') or fallback_metadata()
    receipt = normalize(meta, read_json(args.input / 'validation_report.json'), read_json(args.input / 'hub.json'))
    if args.input.resolve() != args.output.resolve():
        for name in EVIDENCE_FILES:
            source = args.input / name
            if source.is_file() and not source.is_symlink() and source.stat().st_size <= MAX_FILE:
                args.output.mkdir(parents=True, exist_ok=True)
                (args.output / name).write_bytes(source.read_bytes())
    write_bundle(receipt, args.output)
    print(f'ICARUS Observatory: {receipt["state"]} -> {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
