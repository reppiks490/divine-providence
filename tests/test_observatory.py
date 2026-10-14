import copy
import hashlib
import importlib
import json
import re

import pytest


def api():
    return importlib.import_module('scripts.observatory.report')


@pytest.fixture
def inputs():
    inventory = {
        'systems': ['nexus', 'aion'],
        'connections': {'siblings': {'systems': ['nexus', 'aion'], 'contract': 'fixture'}},
        'adversarial': ['hostile.py'],
        'coverage': {'nexus': {'status': 'connected', 'connections': ['siblings']},
                     'aion': {'status': 'connected', 'connections': ['siblings']}},
    }
    meta = dict(schema='icarus.observatory.collection.v1', run_id=12, run_attempt=1,
                repository='owner/repo', ref='refs/heads/main', event='push',
                commit='a' * 40, run_url='https://github.com/owner/repo/actions/runs/12',
                started_at='2026-10-14T04:17:00+00:00', finished_at='2026-10-14T04:19:00+00:00',
                python='3.11', platform='Linux', validator_exit_code=0, hub_exit_code=0,
                validator_timed_out=False, hub_timed_out=False, inventory=inventory,
                collection_errors=[], dependencies=[{'name': 'pytest', 'version': '8.0'}])
    native = dict(generated_at='2026-10-14T04:18:00+00:00',
                  systems={n: dict(passed=True, counts={'passed': 2}, seconds=1.0,
                                   timed_out=False, tail='') for n in inventory['systems']},
                  compile={n: dict(ok=True, errors='', stderr_tail='') for n in inventory['systems']},
                  ascension_adversarial={'hostile.py': dict(ok=True, output='')},
                  connections=dict(ok=True, connections={'siblings': dict(ok=True)}),
                  all_suites_and_compile_ok=True, connections_ok=True)
    hub = dict(returncode=0, timed_out=False, counts={'passed': 4}, seconds=1.0,
               stdout_tail='4 passed in 1s', stderr_tail='')
    return meta, native, hub


def test_complete_native_report_uses_real_shape_and_no_invented_measurements(inputs):
    result = api().normalize(*inputs)
    assert result['state'] == 'healthy'
    assert len(result['findings']) == 7
    assert result['findings']['compile/nexus']['seconds'] is None
    assert result['findings']['compile/nexus']['counts'] is None
    assert result['execution_authorized'] is False
    assert result['production_authorized'] is False
    assert result['live_engine'] == 'not_observed'


def test_valid_failing_connection_stays_unhealthy_without_accepting_quarantine(inputs):
    meta, native, hub = inputs
    meta['validator_exit_code'] = 1
    native['connections']['connections']['siblings'].update(ok=False, link_state='QUARANTINED_AS_EXPECTED')
    native['connections']['ok'] = native['connections_ok'] = False
    result = api().normalize(meta, native, hub)
    assert result['state'] == 'unhealthy'
    assert result['findings']['connection/siblings']['state'] == 'fail'
    assert 'QUARANTINED_AS_EXPECTED' in result['findings']['connection/siblings']['diagnostic']


@pytest.mark.parametrize('damage', ['missing', 'truthy', 'zero', 'contradiction', 'stale',
                                  'extra', 'empty_inventory', 'no_hub', 'bad_count', 'timeout'])
def test_incomplete_evidence_cannot_be_healthy(inputs, damage):
    meta, native, hub = inputs
    if damage == 'missing':
        del native['compile']['nexus']
    elif damage == 'truthy':
        native['systems']['nexus']['passed'] = 'true'
    elif damage == 'zero':
        native['systems']['nexus']['counts'] = {'passed': 0}
    elif damage == 'contradiction':
        native['connections_ok'] = False
    elif damage == 'stale':
        native['generated_at'] = '2026-10-13T04:18:00+00:00'
    elif damage == 'extra':
        native['systems']['ghost'] = native['systems']['nexus']
    elif damage == 'empty_inventory':
        meta['inventory']['systems'] = []
    elif damage == 'no_hub':
        hub = None
    elif damage == 'bad_count':
        native['systems']['nexus']['counts']['passed'] = True
    elif damage == 'timeout':
        meta['validator_timed_out'] = True
    assert api().normalize(meta, native, hub)['state'] == 'incomplete'


def test_missing_report_emits_unobserved_findings(inputs):
    meta, _, hub = inputs
    result = api().normalize(meta, None, hub)
    assert result['state'] == 'incomplete'
    assert result['findings']['suite/nexus']['state'] == 'not_observed'


def test_hub_failure_also_fails_overall_run(inputs):
    meta, native, hub = inputs
    meta['hub_exit_code'] = hub['returncode'] = 1
    hub['counts'] = {'passed': 3, 'failed': 1}
    assert api().normalize(meta, native, hub)['state'] == 'unhealthy'


def test_comparison_exposes_regression_recovery_removed_and_new_checks(inputs):
    old = api().normalize(*inputs)
    old['findings']['hub/tests']['state'] = 'fail'
    now = copy.deepcopy(old)
    now['run_id'] = 13
    now['findings']['hub/tests']['state'] = 'pass'
    now['findings']['suite/nexus']['state'] = 'fail'
    del now['findings']['suite/aion']
    now['findings']['suite/new'] = dict(state='pass', counts={'passed': 1}, seconds=1)
    diff = api().compare(now, old)
    assert diff['regressions'] == ['suite/nexus']
    assert diff['recoveries'] == ['hub/tests']
    assert diff['inventory_removed'] == ['suite/aion']
    assert diff['lost_observations'] == ['suite/aion']
    assert diff['inventory_added'] == ['suite/new']
    assert api().compare(now, None)['first_observation'] is True


def test_human_reports_show_descriptive_measurement_and_environment_changes(inputs, tmp_path):
    old = api().normalize(*inputs)
    new = copy.deepcopy(old)
    new['findings']['suite/nexus']['counts']['passed'] = 99
    new['findings']['suite/nexus']['seconds'] = 9
    new['environment_hash'] = 'b' * 64
    api().write_bundle(new, tmp_path, baseline=old)
    for name in ('summary.md', 'index.html'):
        content = (tmp_path / name).read_text()
        assert 'Measurement changes' in content
        assert '99' in content and '9' in content
        assert 'Installed environment changed' in content


def test_durable_dashboard_uses_receipt_paths_present_on_history_branch(inputs):
    receipt = api().normalize(*inputs)
    page = api().render_html(receipt, api().compare(receipt, None), durable=True)
    assert 'href="latest.json"' in page
    assert 'href="index.json"' in page
    assert 'href="run.json"' not in page
    assert 'href="SHA256SUMS"' not in page


def test_html_and_markdown_escape_diagnostics_and_bundle_hashes(inputs, tmp_path):
    receipt = api().normalize(*inputs)
    receipt['findings']['hub/tests']['diagnostic'] = '<script>alert(1)</script> | [x](javascript:bad)'
    (tmp_path / 'validation.stdout.log').write_text('safe log')
    api().write_bundle(receipt, tmp_path)
    html = (tmp_path / 'index.html').read_text()
    md = (tmp_path / 'summary.md').read_text()
    assert '<script>alert(1)</script>' not in html
    assert '&lt;script&gt;' in html
    assert '[x](javascript:bad)' not in md
    saved = json.loads((tmp_path / 'run.json').read_text())
    assert saved == api().seal_receipt(saved)
    for line in (tmp_path / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        assert hashlib.sha256((tmp_path / name).read_bytes()).hexdigest() == digest


def test_cli_missing_input_writes_fresh_incomplete_receipt(tmp_path, monkeypatch):
    monkeypatch.setenv('GITHUB_RUN_ID', '12')
    assert api().main(['--input', str(tmp_path / 'missing'), '--output', str(tmp_path / 'out')]) == 0
    assert json.loads((tmp_path / 'out' / 'run.json').read_text())['state'] == 'incomplete'


def test_duplicate_json_keys_are_incomplete_evidence(tmp_path):
    path = tmp_path / 'ambiguous.json'
    path.write_text('{"passed": false, "passed": true}')
    assert api().read_json(path) is None


def test_hash_changes_when_evidence_or_finding_changes(inputs):
    first = api().normalize(*inputs)
    changed = copy.deepcopy(first)
    changed['findings']['suite/nexus']['diagnostic'] = 'changed'
    second = api().seal_receipt(changed)
    assert second['receipt_hash'] != first['receipt_hash']
    assert second['findings']['suite/nexus']['finding_hash'] != first['findings']['suite/nexus']['finding_hash']


def test_malformed_collection_inventory_still_renders_incomplete(inputs, tmp_path):
    meta, native, hub = inputs
    meta['inventory']['coverage'] = {'nexus': 'wrong', 'aion': {'status': 'invented'}}
    receipt = api().normalize(meta, native, hub)
    assert receipt['state'] == 'incomplete'
    api().write_bundle(receipt, tmp_path)
    assert (tmp_path / 'index.html').is_file()


@pytest.mark.parametrize('damage', ['systems_scalar', 'extra_coverage', 'connections_scalar', 'bad_link'])
def test_bad_inventory_shapes_always_produce_inspectable_incomplete_bundle(inputs, tmp_path, damage):
    meta, native, hub = inputs
    if damage == 'systems_scalar':
        meta['inventory']['systems'] = 3
    elif damage == 'extra_coverage':
        meta['inventory']['coverage']['ghost'] = None
    elif damage == 'connections_scalar':
        meta['inventory']['coverage']['nexus']['connections'] = 3
    elif damage == 'bad_link':
        meta['inventory']['connections']['siblings']['systems'] = 3
    receipt = api().normalize(meta, native, hub)
    assert receipt['state'] == 'incomplete'
    api().write_bundle(receipt, tmp_path)
    assert (tmp_path / 'index.html').is_file()


def test_workflow_recurrence_and_write_job_boundaries():
    from pathlib import Path
    import yaml
    workflow = yaml.safe_load((Path(__file__).parents[1] / '.github/workflows/icarus-observatory.yml').read_text())
    assert workflow['on']['schedule'] == [{'cron': '17 4 * * *'}]
    assert workflow['permissions'] == {'contents': 'read'}
    assert workflow['concurrency']['cancel-in-progress'] is False
    jobs = workflow['jobs']
    assert jobs['collect']['timeout-minutes'] == 60
    assert jobs['publish']['permissions'] == {'contents': 'write', 'issues': 'write', 'actions': 'read'}
    assert "github.ref == 'refs/heads/main'" in jobs['publish']['if']
    assert "github.event_name != 'pull_request'" in jobs['publish']['if']
    assert jobs['publish']['needs'] == ['collect']
    assert all(re.search(r'@[0-9a-f]{40}$', step['uses']) for job in jobs.values()
               for step in job['steps'] if 'uses' in step)
    assert all('GITHUB_TOKEN' not in step.get('env', {}) for step in jobs['collect']['steps'])
    for job in jobs.values():
        for step in job['steps']:
            if step.get('uses', '').startswith('actions/upload-artifact'):
                assert step['with']['retention-days'] == 30
