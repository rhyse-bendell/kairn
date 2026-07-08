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


def test_project_tab_imports_and_empty_state(monkeypatch):
    app = _qt_app(monkeypatch)
    from PySide6.QtWidgets import QTextEdit
    from kairn.apps.desktop.tabs.project import ProjectTab
    tab = ProjectTab(AppState(), QTextEdit())
    assert tab.switch_to_subview("Overview") is True
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
