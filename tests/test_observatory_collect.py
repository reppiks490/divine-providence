"""Collector behavior against isolated repositories and real child processes."""
from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import textwrap
import time
import unittest
from unittest import mock


SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "observatory" / "collect.py"
ENV = {
    "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "2",
    "GITHUB_EVENT_NAME": "workflow_dispatch",
    "GITHUB_REPOSITORY": "example/icarus", "GITHUB_REF": "refs/heads/main",
    "GITHUB_SHA": "a" * 40,
}


def collector():
    assert SOURCE.is_file(), "Observatory collector implementation is missing"
    return importlib.import_module("scripts.observatory.collect")


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.output = Path(self.temp.name) / "evidence"
        self.package = self.root / "src" / "divine_providence"
        self.package.mkdir(parents=True)
        (self.package / "__init__.py").write_text("")
        (self.package / "registry.py").write_text("SYSTEMS = {'beta': None, 'alpha': None}\n")
        (self.package / "connections.py").write_text(textwrap.dedent("""
            from types import SimpleNamespace
            CONNECTIONS = {'alpha-beta': SimpleNamespace(systems=('alpha', 'beta'), contract='fixture.v1')}
            def coverage():
                return {'alpha': {'status': 'connected', 'connections': ['alpha-beta']},
                        'beta': {'status': 'standalone', 'reason': 'fixture standalone explanation'}}
        """))
        (self.root / "provenance").mkdir()
        (self.root / "tests").mkdir()
        self.set_hub("assert True")
        self.set_validator()

    def set_hub(self, body):
        (self.root / "tests" / "test_fixture.py").write_text(
            "import os\ndef test_fixture():\n" + textwrap.indent(body, "    ") + "\n")

    def set_validator(self, *, exit_code=0, report=True, body=""):
        native = {"generated_at": "2026-10-14T01:00:00+00:00", "fixture": True}
        script = "ASCENSION_SCRIPTS = ['hostile.py', 'property.py']\n"
        script += "if __name__ == '__main__':\n"
        script += textwrap.indent(textwrap.dedent("""
            import json, pathlib, sys
            assert sys.argv[1:] == ['--workers', '2']
            pathlib.Path('validator-ran').write_text('yes')
        """).strip() + "\n", "    ")
        if body:
            script += textwrap.indent(textwrap.dedent(body).strip() + "\n", "    ")
        if report:
            script += "    pathlib.Path('provenance/validation_report.json').write_text(" + repr(json.dumps(native)) + ")\n"
        script += f"    sys.exit({exit_code})\n"
        (self.package / "validate.py").write_text(script)

    def test_initialize_removes_stale_evidence_and_creates_pre_setup_receipt(self):
        mod = collector()
        self.output.mkdir()
        for name in ("collection.json", "hub.json", "validation_report.json", "run.json", "index.html", "SHA256SUMS"):
            (self.output / name).write_text("stale healthy output")
        native = self.root / "provenance" / "validation_report.json"
        native.write_text("stale native")
        receipt = mod.initialize(self.output, root=self.root, environ=ENV)
        self.assertFalse(native.exists())
        self.assertFalse((self.output / "validation_report.json").exists())
        self.assertFalse((self.output / "hub.json").exists())
        self.assertFalse((self.output / "run.json").exists())
        self.assertEqual(receipt, json.loads((self.output / "collection.json").read_text()))
        self.assertEqual(receipt["schema"], "icarus.observatory.collection.v1")
        self.assertEqual(receipt["run_id"], 123)
        self.assertEqual(receipt["run_attempt"], 2)
        self.assertEqual(receipt["run_url"], "https://github.com/example/icarus/actions/runs/123")
        self.assertIsNone(receipt["hub_exit_code"])
        self.assertIsNone(receipt["validator_exit_code"])
        self.assertFalse(receipt["hub_timed_out"])
        self.assertEqual(receipt["phase"], "initialized")
        self.assertTrue(receipt["started_at"].endswith("+00:00"))

    def test_inventory_retains_contract_participants_and_standalone_explanation(self):
        mod = collector()
        receipt = mod.initialize(self.output, root=self.root, environ=ENV)
        self.assertEqual(receipt["inventory"]["systems"], ["alpha", "beta"])
        self.assertEqual(receipt["inventory"]["adversarial"], ["hostile.py", "property.py"])
        self.assertEqual(receipt["inventory"]["connections"], {
            "alpha-beta": {"systems": ["alpha", "beta"], "contract": "fixture.v1"}})
        self.assertEqual(receipt["inventory"]["coverage"]["beta"]["reason"], "fixture standalone explanation")
        self.assertTrue(receipt["dependencies"])
        self.assertEqual(receipt["dependencies"], sorted(receipt["dependencies"], key=lambda d: (d["name"], d["version"])))
        self.assertTrue(all(set(d) == {"name", "version"} for d in receipt["dependencies"]))
        self.assertRegex(receipt["dependency_hash"], r"^[a-f0-9]{64}$")

    def test_hub_failure_does_not_prevent_validator_or_erase_its_success(self):
        mod = collector()
        before = mod.initialize(self.output, root=self.root, environ=ENV)
        self.set_hub("assert False, 'hub-only failure'")
        receipt = mod.collect(self.output, root=self.root, environ=ENV, hub_timeout=30, validator_timeout=30)
        hub = json.loads((self.output / "hub.json").read_text())
        self.assertEqual(receipt["hub_exit_code"], 1)
        self.assertEqual(hub["counts"]["failed"], 1)
        self.assertEqual(receipt["validator_exit_code"], 0)
        self.assertTrue((self.root / "validator-ran").exists())
        self.assertTrue(json.loads((self.output / "validation_report.json").read_text())["fixture"])
        self.assertEqual(receipt["started_at"], before["started_at"])
        self.assertEqual(receipt["phase"], "completed")

    def test_validator_failure_retains_native_report_and_its_exit(self):
        mod = collector()
        self.set_validator(exit_code=7)
        receipt = mod.collect(self.output, root=self.root, environ=ENV, hub_timeout=30, validator_timeout=30)
        self.assertEqual(receipt["hub_exit_code"], 0)
        self.assertEqual(receipt["validator_exit_code"], 7)
        self.assertTrue((self.output / "validation_report.json").exists())

    def test_crashing_validator_cannot_reuse_stale_healthy_native_report(self):
        mod = collector()
        (self.root / "provenance" / "validation_report.json").write_text('{"healthy": true}')
        self.set_validator(exit_code=1, report=False, body="print('validator crashed', file=sys.stderr)")
        receipt = mod.collect(self.output, root=self.root, environ=ENV, hub_timeout=30, validator_timeout=30)
        self.assertEqual(receipt["validator_exit_code"], 1)
        self.assertFalse((self.output / "validation_report.json").exists())
        self.assertTrue(any("report" in error for error in receipt["collection_errors"]))
        self.assertIn("validator crashed", (self.output / "validation.stderr.log").read_text())

    def test_root_tests_ignore_inherited_selection_and_do_not_receive_tokens(self):
        mod = collector()
        contaminated = {**os.environ, **ENV, "PYTEST_ADDOPTS": "-k absent",
                        "PYTHONOPTIMIZE": "2", "GITHUB_TOKEN": "private-token", "GH_TOKEN": "private-token"}
        self.set_hub("assert 'GITHUB_TOKEN' not in os.environ\nassert 'GH_TOKEN' not in os.environ\nassert 'PYTEST_ADDOPTS' not in os.environ\nassert 'PYTHONOPTIMIZE' not in os.environ")
        receipt = mod.collect(self.output, root=self.root, environ=contaminated, hub_timeout=30, validator_timeout=30)
        self.assertEqual(receipt["hub_exit_code"], 0)
        self.assertEqual(json.loads((self.output / "hub.json").read_text())["counts"], {"passed": 1})

    def test_timeout_keeps_both_logs_and_kills_descendant(self):
        mod = collector()
        marker = Path(self.temp.name) / "orphan-survived"
        child = "import time,pathlib;time.sleep(.8);pathlib.Path(" + repr(str(marker)) + ").write_text('bad')"
        script = "import subprocess,sys,time;subprocess.Popen([sys.executable,'-c'," + repr(child) + "]);print('stdout before timeout',flush=True);print('stderr before timeout',file=sys.stderr,flush=True);time.sleep(10)"
        result = mod.run_process([sys.executable, "-c", script], root=self.root, timeout=.3,
                                 stdout_path=Path(self.temp.name) / "out.log", stderr_path=Path(self.temp.name) / "err.log", environ=ENV)
        self.assertTrue(result["timed_out"])
        self.assertNotEqual(result["returncode"], 0)
        self.assertIn("stdout before timeout", result["stdout_tail"])
        self.assertIn("stderr before timeout", result["stderr_tail"])
        time.sleep(.9)
        self.assertFalse(marker.exists(), "timeout left a descendant process running")

    def test_logs_are_bounded_while_capturing_and_have_valid_unicode(self):
        mod = collector()
        out = Path(self.temp.name) / "large.log"
        err = Path(self.temp.name) / "large-error.log"
        script = (
            "import os\n"
            "def write_all(fd,data):\n"
            "    v=memoryview(data)\n"
            "    while v:\n"
            "        v=v[os.write(fd,v):]\n"
            "write_all(1,b'x'*1000000+b'\\xf0\\x9f\\x8c\\x9e')\n"
            "write_all(2,b'\\xff'*1000000)\n"
        )
        result = mod.run_process([sys.executable, "-c", script], root=self.root, timeout=10,
                                 stdout_path=out, stderr_path=err, environ=ENV)
        self.assertEqual(result["returncode"], 0)
        self.assertLessEqual(out.stat().st_size, mod.LOG_LIMIT)
        self.assertLessEqual(err.stat().st_size, mod.LOG_LIMIT)
        self.assertTrue(out.read_text().endswith("🌞"))
        self.assertTrue(err.read_text())

    def test_finalize_after_setup_failure_marks_incomplete_and_discards_stale_report(self):
        mod = collector()
        receipt = mod.initialize(self.output, root=self.root, environ=ENV)
        (self.output / "validation_report.json").write_text('{"stale": true}')
        finalized = mod.finalize(self.output, root=self.root, environ=ENV)
        self.assertEqual(finalized["started_at"], receipt["started_at"])
        self.assertIsNone(finalized["validator_exit_code"])
        self.assertFalse((self.output / "validation_report.json").exists())
        self.assertTrue(any("not completed" in e for e in finalized["collection_errors"]))

    def test_finalize_keeps_completed_failure_data_and_is_idempotent(self):
        mod = collector()
        self.set_validator(exit_code=3)
        receipt = mod.collect(self.output, root=self.root, environ=ENV, hub_timeout=30, validator_timeout=30)
        native = (self.output / "validation_report.json").read_bytes()
        finalized = mod.finalize(self.output, root=self.root, environ=ENV)
        self.assertEqual(finalized["validator_exit_code"], 3)
        self.assertEqual(finalized["hub_exit_code"], receipt["hub_exit_code"])
        self.assertEqual((self.output / "validation_report.json").read_bytes(), native)
        self.assertEqual(mod.finalize(self.output, root=self.root, environ=ENV), finalized)

    def test_finalize_rejects_previous_run_receipt_and_evidence(self):
        mod = collector()
        mod.collect(self.output, root=self.root, environ=ENV, hub_timeout=30, validator_timeout=30)
        next_env = {**ENV, "GITHUB_RUN_ID": "124"}
        finalized = mod.finalize(self.output, root=self.root, environ=next_env)
        self.assertEqual(finalized["run_id"], 124)
        self.assertIsNone(finalized["validator_exit_code"])
        self.assertFalse((self.output / "validation_report.json").exists())
        self.assertTrue(finalized["collection_errors"])

    def test_missing_inventory_still_writes_receipt_with_visible_error(self):
        mod = collector()
        (self.package / "registry.py").unlink()
        receipt = mod.initialize(self.output, root=self.root, environ=ENV)
        self.assertEqual(receipt["inventory"]["systems"], [])
        self.assertTrue(any("inventory" in e for e in receipt["collection_errors"]))
        self.assertTrue((self.output / "collection.json").is_file())

    def test_output_cannot_be_repository_root(self):
        mod = collector()
        with self.assertRaises(ValueError):
            mod.initialize(self.root, root=self.root, environ=ENV)
        self.assertTrue((self.package / "registry.py").exists())

    def test_cli_initialization_and_finalization_return_receipts_without_validation(self):
        mod = collector()
        self.assertEqual(mod.main(["--output", str(self.output), "--root", str(self.root), "--initialize"]), 0)
        self.assertFalse((self.root / "validator-ran").exists())
        self.assertEqual(mod.main(["--output", str(self.output), "--root", str(self.root), "--finalize"]), 0)
        receipt = json.loads((self.output / "collection.json").read_text())
        self.assertTrue(receipt["collection_errors"])

    def test_hub_timeout_remains_separate_from_successful_validator(self):
        mod = collector()
        self.set_hub("import time\ntime.sleep(10)")
        receipt = mod.collect(self.output, root=self.root, environ=ENV, hub_timeout=.3, validator_timeout=10)
        self.assertTrue(receipt["hub_timed_out"])
        self.assertNotEqual(receipt["hub_exit_code"], 0)
        self.assertEqual(receipt["validator_exit_code"], 0)
        self.assertFalse(receipt["validator_timed_out"])
        self.assertTrue(json.loads((self.output / "hub.json").read_text())["timed_out"])

    def test_validator_timeout_retains_logs_and_unobserved_report(self):
        mod = collector()
        self.set_validator(report=False, body="import time\nprint('before validator timeout', file=sys.stderr, flush=True)\ntime.sleep(10)")
        receipt = mod.collect(self.output, root=self.root, environ=ENV, hub_timeout=10, validator_timeout=.3)
        self.assertEqual(receipt["hub_exit_code"], 0)
        self.assertTrue(receipt["validator_timed_out"])
        self.assertFalse((self.output / "validation_report.json").exists())
        self.assertIn("before validator timeout", (self.output / "validation.stderr.log").read_text())

    def test_failed_process_launch_is_observable_and_writes_stderr(self):
        mod = collector()
        error_log = Path(self.temp.name) / "launch-error.log"
        result = mod.run_process([str(self.root / "missing-interpreter")], root=self.root, timeout=1,
                                 stderr_path=error_log, environ=ENV)
        self.assertIsNone(result["returncode"])
        self.assertFalse(result["timed_out"])
        self.assertIn("missing-interpreter", error_log.read_text())

    def test_original_malformed_report_is_retained_without_being_reinterpreted(self):
        mod = collector()
        self.set_validator(report=False, body="pathlib.Path('provenance/validation_report.json').write_bytes(b'{truncated')")
        receipt = mod.collect(self.output, root=self.root, environ=ENV, hub_timeout=10, validator_timeout=10)
        self.assertEqual(receipt["validator_exit_code"], 0)
        self.assertEqual((self.output / "validation_report.json").read_bytes(), b"{truncated")

    def test_oversized_native_report_is_not_admitted_to_evidence(self):
        mod = collector()
        self.set_validator(report=False, body=f"pathlib.Path('provenance/validation_report.json').write_bytes(b'x' * {mod.REPORT_LIMIT + 1})")
        receipt = mod.collect(self.output, root=self.root, environ=ENV, hub_timeout=10, validator_timeout=10)
        self.assertFalse((self.output / "validation_report.json").exists())
        self.assertTrue(any("size limit" in e for e in receipt["collection_errors"]))

    def test_cli_cannot_report_zero_test_hub_as_success(self):
        # A plugin or corrupted runner can exit zero without giving any test
        # evidence. The CLI must preserve the failing collection gate.
        mod = collector()
        (self.root / "pytest.py").write_text("print('no test evidence')\n")
        old_environment = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(old_environment)))
        os.environ.update(ENV)
        result = mod.main(["--output", str(self.output), "--root", str(self.root)])
        self.assertEqual(result, 1)
        self.assertEqual(json.loads((self.output / "hub.json").read_text())["counts"], {})

    def test_collection_refreshes_interpreter_identity_after_setup(self):
        mod = collector()
        with mock.patch.object(mod.platform, "python_version", return_value="3.12.0"), \
                mock.patch.object(mod.platform, "platform", return_value="setup-host"):
            before = mod.initialize(self.output, root=self.root, environ=ENV)
        with mock.patch.object(mod.platform, "python_version", return_value="3.11.0"), \
                mock.patch.object(mod.platform, "platform", return_value="validation-host"):
            receipt = mod.collect(self.output, root=self.root, environ=ENV, hub_timeout=10, validator_timeout=10)
        self.assertEqual(receipt["started_at"], before["started_at"])
        self.assertEqual(before["python"], "3.12.0")
        self.assertEqual(receipt["python"], "3.11.0")
        self.assertEqual(receipt["platform"], "validation-host")


if __name__ == "__main__":
    unittest.main()
