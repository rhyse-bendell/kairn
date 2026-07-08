from __future__ import annotations

import pytest


def test_dashboard_tab_imports_without_running_dialogs():
    pytest.importorskip("PySide6")
    import kairn.apps.desktop.tabs.dashboard as dashboard

    assert dashboard.DashboardTab is not None
    assert dashboard.NewProjectDialog is not None
    assert dashboard.LoadProjectDialog is not None


def test_dashboard_tab_instantiates_offscreen_qapplication(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QLabel, QTextEdit
    from kairn.apps.desktop.state import AppState
    from kairn.apps.desktop.tabs.dashboard import DashboardTab

    app = QApplication.instance() or QApplication([])
    state = AppState(
        workspace_dir=str(tmp_path / "kairn_workspace"),
        db_path=str(tmp_path / "kairn_workspace" / "kairn.db"),
        snapshots_dir=str(tmp_path / "kairn_workspace" / "snapshots"),
        outputs_dir=str(tmp_path / "kairn_workspace" / "outputs"),
    )
    tab = DashboardTab(state, QTextEdit())

    assert tab.start_button.text() == "Start New Project"
    assert tab.load_button.text() == "Load Project"
    assert tab.open_button.text() == "Open Project Files"
    assert tab.project_name.text() == "No project loaded."
    assert tab.project_path.text().startswith("Project home:")
    assert tab.next_step.text() == "Start or load a project to begin."

    title = tab.findChild(QLabel, "dashboardTitle")
    assert title is not None
    assert title.text() == "Kairn"
    assert title.font().bold()
    assert title.font().pointSize() >= 34
    assert not any(label.text() == "Collaboration Observatory" for label in tab.findChildren(QLabel))
    for button in (tab.start_button, tab.load_button, tab.open_button):
        assert button.minimumHeight() >= 52
        assert button.minimumWidth() >= 260
    app.processEvents()
