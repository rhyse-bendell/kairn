from __future__ import annotations

import pytest

from kairn.apps.desktop.state import AppState


def _qt_app(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_main_window_top_level_tabs(monkeypatch):
    app = _qt_app(monkeypatch)
    from kairn.apps.desktop.main import KairnMainWindow
    window = KairnMainWindow()
    assert window.tab_names() == ["Dashboard", "Project", "Replay", "Analysis", "Exports"]
    assert window.switch_to_tab("Project") is True
    app.processEvents()


def test_main_window_applies_default_startup_mode(monkeypatch):
    app = _qt_app(monkeypatch)
    monkeypatch.delenv("KAIRN_WINDOW_MODE", raising=False)
    from kairn.apps.desktop.main import KairnMainWindow

    window = KairnMainWindow()
    assert hasattr(window, "apply_startup_window_mode")
    window.apply_startup_window_mode()
    app.processEvents()

    assert window.isMaximized() is True
    assert window.isFullScreen() is False


def test_main_window_supports_window_mode_override(monkeypatch):
    app = _qt_app(monkeypatch)
    monkeypatch.setenv("KAIRN_WINDOW_MODE", "windowed")
    from kairn.apps.desktop.main import KairnMainWindow

    window = KairnMainWindow()
    window.apply_startup_window_mode()
    app.processEvents()

    assert window.isVisible() is True
    assert window.isFullScreen() is False


def test_project_tab_imports_and_empty_state(monkeypatch):
    app = _qt_app(monkeypatch)
    from PySide6.QtWidgets import QTextEdit
    from kairn.apps.desktop.tabs.project import ProjectTab
    tab = ProjectTab(AppState(), QTextEdit())
    assert tab.switch_to_subview("Overview") is True
    assert tab.overview.model is not None
    assert tab.overview.tree is not None
    tab.refresh()
    app.processEvents()


def test_old_tabs_still_import():
    pytest.importorskip("PySide6")
    from kairn.apps.desktop.tabs.agents import AgentsTab
    from kairn.apps.desktop.tabs.artifacts import ArtifactsTab
    from kairn.apps.desktop.tabs.categories import CategoriesTab
    from kairn.apps.desktop.tabs.diagnostics import DiagnosticsTab
    from kairn.apps.desktop.tabs.process_data import ProcessDataTab
    from kairn.apps.desktop.tabs.sources import SourcesTab
    from kairn.apps.desktop.tabs.timeline import TimelineTab
    assert all([SourcesTab, AgentsTab, ArtifactsTab, CategoriesTab, ProcessDataTab, DiagnosticsTab, TimelineTab])


def test_replay_tab_instantiates(monkeypatch):
    app = _qt_app(monkeypatch)
    from PySide6.QtWidgets import QTextEdit
    from kairn.apps.desktop.tabs.replay import ReplayTab
    tab = ReplayTab(AppState(), QTextEdit())
    assert hasattr(tab, "timeline")
    app.processEvents()


def test_qdir_filter_enum_compatibility():
    pytest.importorskip("PySide6")
    from PySide6.QtCore import QDir

    flags = QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot
    assert flags is not None


def test_activate_project_refreshes_project_tab(monkeypatch, tmp_path):
    app = _qt_app(monkeypatch)
    from kairn.apps.desktop.main import KairnMainWindow
    from kairn.core.projects import create_project

    monkeypatch.setenv("KAIRN_HOME", str(tmp_path))
    window = KairnMainWindow()
    project = create_project("Test Project", kairn_home=tmp_path)

    window.activate_project(project)
    app.processEvents()

    assert window.state.has_active_project() is True
    assert window.state.active_project_root == project["project_root"]
    assert window.current_tab_name() == "Project"
    assert project["name"] in window.project_tab.mini.text() or project["project_root"] in window.project_tab.mini.text()
    assert project["project_root"] in window.project_tab.overview.summary.text()
    assert window.project_tab.overview.tree.isEnabled() is True
    root_index = window.project_tab.overview.tree.rootIndex()
    assert window.project_tab.overview.model.filePath(root_index) == project["project_root"]


def test_project_tab_empty_state_does_not_show_filesystem_root(monkeypatch):
    app = _qt_app(monkeypatch)
    from PySide6.QtWidgets import QTextEdit
    from kairn.apps.desktop.tabs.project import ProjectTab

    tab = ProjectTab(AppState(), QTextEdit())
    tab.refresh()
    app.processEvents()

    assert "No project loaded" in tab.mini.text()
    assert "No project loaded" in tab.overview.summary.text()
    assert tab.overview.tree.isEnabled() is False or not tab.overview.tree.rootIndex().isValid()


def test_dashboard_project_creation_uses_activation_callback(monkeypatch, tmp_path):
    app = _qt_app(monkeypatch)
    from kairn.apps.desktop.tabs.dashboard import DashboardTab
    from PySide6.QtWidgets import QTextEdit

    state = AppState()
    called = []
    tab = DashboardTab(state, QTextEdit(), on_project_loaded=called.append)
    project_root = tmp_path / "callback-project"
    project_root.mkdir()
    project = {"project_root": str(project_root), "name": "Callback Project"}
    tab._activate_loaded_project(project)

    assert called == [project]
    assert state.has_active_project() is False
    app.processEvents()


def test_project_overview_has_prominent_import_action(monkeypatch):
    app = _qt_app(monkeypatch)
    from PySide6.QtWidgets import QTextEdit
    from kairn.apps.desktop.tabs.project import ProjectTab

    tab = ProjectTab(AppState(), QTextEdit())
    assert hasattr(tab.overview, "import_data_into_project")
    assert tab.overview.import_data_button.text() == "Import Data Into Project"
    assert tab.overview.import_data_button.minimumHeight() >= 40
    app.processEvents()


def test_project_tab_subviews_still_exist(monkeypatch):
    app = _qt_app(monkeypatch)
    from PySide6.QtWidgets import QTextEdit
    from kairn.apps.desktop.tabs.project import ProjectTab

    tab = ProjectTab(AppState(), QTextEdit())
    assert tab.SUBVIEWS == ["Overview", "Sources / Intake", "Artifacts / Catalog", "Parsed Data", "Agents", "Categories / Metadata", "Diagnostics / Warnings"]
    assert tab.nav.count() == len(tab.SUBVIEWS)
    assert tab.nav.item(0).toolTip()
    app.processEvents()
