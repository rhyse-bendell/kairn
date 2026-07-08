from __future__ import annotations

import json
from pathlib import Path

from kairn.apps.desktop.state import AppState
from kairn.core.projects import create_project, create_project_run, list_projects, load_project, register_project_source
from kairn.core.projects.manifest import load_project_manifest
from kairn.core.projects.paths import get_default_kairn_home, safe_project_slug
from kairn.core.storage import repositories as repo


def test_default_home_respects_env(monkeypatch, tmp_path):
    monkeypatch.setenv("KAIRN_HOME", str(tmp_path / "home"))
    assert get_default_kairn_home() == tmp_path / "home"


def test_safe_project_slug():
    assert safe_project_slug("My Workshop") == "My_Workshop"
    assert safe_project_slug('Bad<>:"/\\|?* Name. ') == "Bad_Name"
    assert safe_project_slug("   ...   ") == "Kairn_Project"


def test_create_project_structure_and_collaboration(tmp_path):
    project = create_project("Workshop 124PG", "desc", kairn_home=tmp_path)
    root = Path(project["project_root"])
    assert root.exists()
    assert (root / "kairn_project.json").exists()
    assert (root / "kairn.db").exists()
    for rel in ["data/original", "data/extracted", "data/linked_sources", "data/staging", "catalog", "parsed/tldraw", "parsed/drive", "parsed/documents", "parsed/process", "runs", "exports/manual_exports", "logs", "settings"]:
        assert (root / rel).is_dir()
    for rel in ["settings/project_settings.json", "settings/profile_settings.json", "settings/source_registry.json", "settings/participant_map.json"]:
        assert (root / rel).exists()
    assert repo.get_collaboration(project["db_path"], project["active_collaboration_id"])["name"] == "Workshop 124PG"


def test_load_project_recreates_missing_folder(tmp_path):
    project = create_project("Load Me", kairn_home=tmp_path)
    missing = Path(project["project_root"]) / "parsed" / "drive"
    missing.rmdir()
    loaded = load_project(project["project_root"])
    assert Path(loaded["project_root"], "parsed", "drive").is_dir()


def test_list_projects(tmp_path):
    create_project("One", kairn_home=tmp_path)
    create_project("Two", kairn_home=tmp_path)
    names = {p["name"] for p in list_projects(tmp_path)}
    assert {"One", "Two"} <= names


def test_register_project_source_link_and_copy(tmp_path):
    project = create_project("Sources", kairn_home=tmp_path)
    src = tmp_path / "input.txt"; src.write_text("hello", encoding="utf-8")
    linked = register_project_source(project, str(src), source_type="text", copy_into_project=False)
    assert linked["copied_into_project"] is False
    copied = register_project_source(project, str(src), source_type="text", copy_into_project=True)
    assert Path(copied["project_path"]).exists()
    registry = json.loads(Path(project["project_root"], "settings", "source_registry.json").read_text())
    manifest = load_project_manifest(project["manifest_path"])
    assert len(registry["sources"]) == 2
    assert len(manifest["sources"]) == 2


def test_create_project_run_updates_manifest(tmp_path):
    project = create_project("Runs", kairn_home=tmp_path)
    paths = create_project_run(project, "first")
    for key in ["run_dir", "json_dir", "chunks_dir", "prompt_dir", "csv_dir", "viz_dir", "viz_units_dir", "reports_dir"]:
        assert Path(paths[key]).is_dir()
    assert Path(paths["meta_path"]).exists()
    assert load_project_manifest(project["manifest_path"])["active_run_id"] == paths["run_id"]


def test_app_state_set_active_project(tmp_path):
    project = create_project("State", kairn_home=tmp_path)
    state = AppState(workspace_dir=str(tmp_path / "legacy"), db_path=str(tmp_path / "legacy" / "kairn.db"))
    state.set_active_project(project)
    assert state.active_project_root == project["project_root"]
    assert state.db_path == project["db_path"]
    assert state.workspace_dir == project["project_root"]
    assert state.source_registry_path.endswith("source_registry.json")


def test_dashboard_import_instantiates(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    import pytest
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QTextEdit
    from kairn.apps.desktop.tabs.dashboard import DashboardTab
    app = QApplication.instance() or QApplication([])
    state = AppState()
    tab = DashboardTab(state, QTextEdit())
    assert tab.start_button.text() == "Start New Project"
    app.processEvents()
