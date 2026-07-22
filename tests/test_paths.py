


def test_data_root_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("NEXUSFLOW_DATA_ROOT", str(tmp_path))
    from ingestion.paths import data_root

    assert data_root() == tmp_path


def test_quality_rules_path_env_override(monkeypatch, tmp_path):
    p = tmp_path / "rules.yaml"
    p.write_text("numeric_ranges: {}\n", encoding="utf-8")
    monkeypatch.setenv("QUALITY_RULES_PATH", str(p))
    from ingestion.paths import quality_rules_path

    assert quality_rules_path() == p


def test_project_root_contains_ingestion():
    from ingestion.paths import project_root

    assert (project_root() / "ingestion" / "paths.py").is_file()
