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


def test_new_project_dialog_values_include_initial_data(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    from kairn.apps.desktop.tabs.dashboard import NewProjectDialog

    app = QApplication.instance() or QApplication([])
    dialog = NewProjectDialog()
    data_path = tmp_path / "source"
    dialog.name.setText("Initial Data Project")
    dialog.description.setPlainText("desc")
    dialog.add_initial_data_paths([str(data_path), str(data_path)])

    name, description, initial_data_paths = dialog.values()

    assert name == "Initial Data Project"
    assert description == "desc"
    assert initial_data_paths == [str(data_path)]
    app.processEvents()


def test_dashboard_start_new_project_imports_initial_files_and_folders(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QDialog, QTextEdit
    from kairn.apps.desktop.state import AppState
    from kairn.apps.desktop.tabs import dashboard
    from kairn.apps.desktop.tabs.dashboard import DashboardTab

    app = QApplication.instance() or QApplication([])
    folder = tmp_path / "folder-source"
    folder.mkdir()
    file_path = tmp_path / "file-source.txt"
    file_path.write_text("hello", encoding="utf-8")
    project = {"project_root": str(tmp_path / "project")}
    calls = {"created": [], "folders": [], "files": [], "detections": [], "activated": []}

    class FakeDialog:
        def __init__(self, parent=None):
            pass

        def exec(self):
            return QDialog.Accepted

        def values(self):
            return "New Project", "desc", [str(folder), str(file_path), str(tmp_path / "missing")]

    def fake_create_project(name, description):
        calls["created"].append((name, description))
        return project

    def fake_detect(path):
        calls["detections"].append(path)
        return {"path": path, "compatible": True}

    def fake_import_folder(proj, path, copy=True, metadata=None):
        calls["folders"].append((proj, path, copy, metadata))
        return {"project_path": str(tmp_path / "project" / "data" / "original" / "folder-source")}

    def fake_import_file(proj, path, copy=True, metadata=None):
        calls["files"].append((proj, path, copy, metadata))
        raise RuntimeError("synthetic import failure")

    monkeypatch.setattr(dashboard, "NewProjectDialog", FakeDialog)
    monkeypatch.setattr(dashboard, "create_project", fake_create_project)
    monkeypatch.setattr(dashboard, "detect_compatible_source", fake_detect)
    monkeypatch.setattr(dashboard, "import_folder_to_project", fake_import_folder)
    monkeypatch.setattr(dashboard, "import_file_to_project", fake_import_file)
    monkeypatch.setattr(dashboard, "show_info", lambda *args, **kwargs: None)

    tab = DashboardTab(AppState(), QTextEdit())
    monkeypatch.setattr(tab, "_activate_loaded_project", lambda proj: calls["activated"].append(proj))

    tab.start_new_project()

    assert calls["created"] == [("New Project", "desc")]
    assert len(calls["folders"]) == 1
    assert calls["folders"][0][1] == str(folder)
    assert calls["folders"][0][2] is True
    assert calls["folders"][0][3]["detection"]["compatible"] is True
    assert len(calls["files"]) == 1
    assert calls["files"][0][1] == str(file_path)
    assert calls["activated"] == [project]
    app.processEvents()
