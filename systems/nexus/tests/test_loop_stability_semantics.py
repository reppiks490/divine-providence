from pathlib import Path


def test_research_loop_source_guards_nondeterminism_by_same_code_version():
    source = Path("src/nexus/research_loop.py").read_text()
    assert 'previous.get("loop_code_version") == LOOP_CODE_VERSION' in source
    assert "A deliberate code migration" in source


def test_cli_defaults_to_reconciled_ten_archive_checkpoint():
    source=Path("src/nexus/cli.py").read_text()
    assert 'default=659' in source
    assert 'default=13_788_256' in source
    assert 'default=803' in source
    assert '"PARALLAX_TEN_ARCHIVE_CHECKPOINT"' in source
    assert '"AION_PRIOR_CHECKPOINT"' not in source
