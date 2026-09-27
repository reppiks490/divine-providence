from pathlib import Path


def test_research_loop_source_guards_nondeterminism_by_same_code_version():
    source = Path("src/nexus/research_loop.py").read_text()
    assert 'previous.get("loop_code_version") == LOOP_CODE_VERSION' in source
    assert "A deliberate code migration" in source
