import json, os, sqlite3, subprocess, sys
from pathlib import Path

import pytest

from kairn.core.profiles import list_builtin_profiles, load_profile
from kairn.core.catalog.detection import detect_source_type, detect_artifact_role, extract_team_hint, extract_participant_hint
from kairn.core.catalog.artifact_catalog import build_artifact_catalog, export_artifact_catalog
from kairn.core.ingestion.service import ingest_root


def art(rel, kind=None, path=None):
    p = Path(rel)
    return {"rel_path": rel, "name": p.name, "extension": p.suffix, "kind": kind or p.suffix.lstrip('.'), "path": path or rel}


def test_builtin_profiles_and_file_load(tmp_path):
    builtins = list_builtin_profiles()
    assert any(p["name"] == "problem_framing_workshop" for p in builtins)
    profile = load_profile("problem_framing_workshop")
    assert "tldraw_sqlite" in profile["expected_source_types"]
    custom = tmp_path / "profile.json"
    custom.write_text(json.dumps({"name":"custom","description":"x","expected_source_types":[],"artifact_roles":["unknown"],"phases":[],"role_rules":[]}), encoding="utf-8")
    assert load_profile(str(custom))["name"] == "custom"


@pytest.mark.parametrize("rel,kind,source,role", [
    ("Team 1/TLDraw Logs.db", "sqlite", "tldraw_sqlite", "tldraw_board_log"),
    ("dailyLog.csv", "csv", "drive_activity_csv", "drive_activity_log"),
    ("docs/changelog.txt", "text", "document_changelog", "unknown"),
    ("Team 2/problem framing statement.docx", "docx", "static_docx", "problem_framing_statement"),
    ("Participant 17/individual synthesis.docx", "docx", "static_docx", "individual_synthesis"),
    ("team1/team synthesis.docx", "docx", "static_docx", "team_synthesis"),
    ("exports/board.html", "html", "html_export", "unknown"),
    ("materials/rubric.docx", "docx", "static_docx", "rubric_material"),
    ("raw/archive.zip", "archive", "archive", "archive"),
])
def test_detection_examples(rel, kind, source, role):
    a = art(rel, kind)
    assert detect_source_type(a)["value"] == source
    assert detect_artifact_role(a)["value"] == role


def test_hint_extraction():
    assert extract_team_hint("Team 3/foo")["value"] == "Team 3"
    assert extract_team_hint("T2/foo")["value"] == "Team 2"
    assert extract_team_hint("team1/foo")["value"] == "Team 1"
    assert extract_participant_hint("Participant 17/foo")["value"] == "Participant 17"
    assert extract_participant_hint("P2/foo")["value"] == "Participant 2"
    assert extract_team_hint("misc/foo")["value"] is None


def test_catalog_build_and_export_after_ingestion(tmp_path):
    root = tmp_path / "root"; root.mkdir()
    (root / "Team 1").mkdir()
    (root / "Team 1" / "dailyLog.csv").write_text("a,b\n1,2\n")
    (root / "Team 1" / "problem framing statement.docx").write_bytes(b"not a real docx")
    db = tmp_path / "kairn.db"
    result = ingest_root(str(root), str(db))
    rows = build_artifact_catalog(str(db), collection_id=result["collection_id"])
    assert len(rows) >= 2
    assert any(r["source_type"] == "drive_activity_csv" for r in rows)
    out = tmp_path / "out"
    paths = export_artifact_catalog(str(db), str(out), collection_id=result["collection_id"])
    for key in ["catalog_csv", "catalog_json", "summary_json", "summary_txt"]:
        assert Path(paths[key]).exists()


def test_cli_profiles_smoke():
    env = os.environ.copy(); env["PYTHONPATH"] = str(Path.cwd() / "src") + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run([sys.executable, "-m", "kairn.cli.main", "profiles", "list"], text=True, capture_output=True, check=True, env=env)
    assert "problem_framing_workshop" in proc.stdout


def test_gui_import_safe():
    pytest.importorskip("PySide6")
    from kairn.apps.desktop.state import AppState
    assert AppState().active_profile_name == "problem_framing_workshop"
