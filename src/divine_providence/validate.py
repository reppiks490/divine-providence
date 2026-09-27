"""Full-build validation: every subsystem suite, compile checks, adversarial scripts, connections.

Writes provenance/validation_report.json. Exit code 0 only if everything passed.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import platform
import sys
from datetime import datetime, timezone

from . import connections, registry, runner

# ASCENSION ships its property/hostile/failure-injection evidence as scripts, not pytest files.
ASCENSION_SCRIPTS = ["property_test_v0_7.py", "property_test_v0_8.py", "hostile_test_v0_8.py",
                     "failure_injection_v0_1.py", "failure_injection_v0_4.py"]


# Byte-compiles every source file in memory (same syntax gate as compileall) without writing __pycache__.
_COMPILE_ALL = (
    "import pathlib,sys\n"
    "bad=[]\n"
    "for p in sorted(pathlib.Path('.').rglob('*.py')):\n"
    "    if {'.git','build','__pycache__','.venv'} & set(p.parts): continue\n"
    "    try: compile(p.read_bytes(), str(p), 'exec')\n"
    "    except SyntaxError as e: bad.append(f'{p}: {e}')\n"
    "print('\\n'.join(bad)); sys.exit(1 if bad else 0)\n"
)


def compile_check(name: str) -> dict:
    s = registry.get(name)
    r = runner.run(["-c", _COMPILE_ALL], cwd=s.path, pythonpath=s.pythonpath(), timeout_s=300)
    return {"ok": r.returncode == 0, "errors": r.stdout_tail[-800:], "stderr_tail": r.stderr_tail[-800:]}


def ascension_scripts() -> dict:
    s = registry.get("ascension")
    out = {}
    for script in ASCENSION_SCRIPTS:
        r = runner.run([script], cwd=s.path, pythonpath=s.pythonpath(), timeout_s=900)
        out[script] = {"ok": r.returncode == 0, "output": r.stdout_tail.strip()[-600:]}
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="dp-validate")
    ap.add_argument("--systems", nargs="*", default=sorted(registry.SYSTEMS))
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(argv)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "python": sys.version.split()[0], "platform": platform.platform(), "systems": {}}
    with cf.ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(runner.run_system_tests, n): n for n in a.systems}
        for f in cf.as_completed(futs):
            n = futs[f]
            r = f.result()
            report["systems"][n] = {"passed": r["passed"], "counts": r["counts"], "seconds": r["seconds"],
                                    "timed_out": r["timed_out"], "tail": r["stdout_tail"][-1500:] if not r["passed"] else ""}
            print(f"{n:15s} {'PASS' if r['passed'] else 'FAIL'} {r['counts']} {r['seconds']}s", flush=True)
    report["compile"] = {n: compile_check(n) for n in a.systems}
    report["ascension_adversarial"] = ascension_scripts() if "ascension" in a.systems else {}
    report["connections"] = connections.check_all()
    ok = (all(v["passed"] for v in report["systems"].values()) and all(v["ok"] for v in report["compile"].values())
          and all(v["ok"] for v in report["ascension_adversarial"].values()))
    report["all_suites_and_compile_ok"] = ok
    report["connections_ok"] = report["connections"]["ok"]
    ok = ok and report["connections_ok"]
    out = registry.repo_root() / "provenance" / "validation_report.json"
    out.write_text(json.dumps(report, indent=1, sort_keys=True), encoding="utf-8")
    total = sum(v["counts"].get("passed", 0) for v in report["systems"].values())
    print(f"suites+compile: {'OK' if ok else 'FAILED'}  total passed tests: {total}  connections: "
          f"{'OK' if report['connections_ok'] else 'see report'}  -> {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
