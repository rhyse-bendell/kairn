from __future__ import annotations

from pathlib import Path

import pytest

from kairn.apps.desktop.state import AppState
from kairn.core.observatory.schemas import ObservatoryReport, table_from_rows


def _qt_app(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _fake_report():
    table = table_from_rows("summary", "Summary", "desc", "test", [{"a": 1}])
    return ObservatoryReport("p", "Project", "root", "run1", "now", {}, [table], [], [], ["warn"], ["caveat"])


def test_project_overview_has_generate_metrics_button(monkeypatch):
    app = _qt_app(monkeypatch)
    from PySide6.QtWidgets import QTextEdit, QPushButton
    from kairn.apps.desktop.tabs.project import ProjectTab

    tab = ProjectTab(AppState(), QTextEdit())
    labels = [b.text() for b in tab.overview.findChildren(QPushButton)]

    assert "Generate Metrics Package" in labels
    assert tab.overview.generate_metrics_button.isEnabled() is False
    app.processEvents()


def test_project_overview_generate_can_be_called_with_mock_worker(monkeypatch, tmp_path):
    app = _qt_app(monkeypatch)
    from PySide6.QtWidgets import QTextEdit
    from kairn.apps.desktop.tabs import project as project_tab
    from kairn.apps.desktop.tabs.project import ProjectTab
    from kairn.core.projects import create_project, register_project_source

    project = create_project("Metrics", kairn_home=tmp_path)
    source = tmp_path / "source.txt"
    source.write_text("hello", encoding="utf-8")
    register_project_source(project, str(source), copy_into_project=False)
    state = AppState()
    state.set_active_project(project)
    result = {"process_result": {"sources_seen": 1, "sources_processed": 1, "output_dir": str(tmp_path / "out")}, "report": _fake_report(), "paths": {"out_dir": str(tmp_path / "metrics")}, "collection_id": "c1", "run_id": "r1", "out_dir": str(tmp_path / "metrics")}

    class DummySignal:
        def __init__(self): self.fn = None
        def connect(self, fn): self.fn = fn
        def emit(self, value): self.fn(value)

    class DummyWorker:
        def __init__(self, *args, **kwargs):
            self.finished_task = DummySignal(); self.failed_task = DummySignal()
        def start(self): self.finished_task.emit(result)

    monkeypatch.setattr(project_tab, "TaskWorker", DummyWorker)
    tab = ProjectTab(state, QTextEdit())
    tab.overview.generate_metrics_package()

    assert state.last_observatory_report is result["report"]
    assert state.last_observatory_output_dir == str(tmp_path / "metrics")
    app.processEvents()


def test_generate_metrics_package_helper_calls_existing_functions(monkeypatch, tmp_path):
    pytest.importorskip("PySide6")
    from kairn.apps.desktop.tabs import project as project_tab

    calls = []
    report = _fake_report()

    def fake_process_registered_sources(**kwargs):
        calls.append("process")
        return {"sources_seen": 1, "sources_processed": 1, "collection_id": "c1", "run_id": "r1", "output_dir": str(tmp_path / "processed")}

    def fake_build_observatory_report(**kwargs):
        calls.append("build")
        assert kwargs["run_id"] == "r1"
        return report

    def fake_export_observatory_report(rep, out_dir):
        calls.append("export")
        assert rep is report
        return {"out_dir": str(out_dir)}

    monkeypatch.setattr(project_tab, "process_registered_sources", fake_process_registered_sources)
    monkeypatch.setattr(project_tab, "build_observatory_report", fake_build_observatory_report)
    monkeypatch.setattr(project_tab, "export_observatory_report", fake_export_observatory_report)

    result = project_tab._generate_metrics_package_for_project({"project_id": "p", "name": "P", "project_root": str(tmp_path)}, {"db_path": str(tmp_path / "k.db"), "workspace_dir": str(tmp_path)})

    assert calls == ["process", "build", "export"]
    assert result["report"] is report
    assert result["process_result"]["sources_processed"] == 1
    assert result["out_dir"].endswith("observatory_metrics")


def test_project_overview_metrics_done_updates_app_state(monkeypatch, tmp_path):
    app = _qt_app(monkeypatch)
    from PySide6.QtWidgets import QTextEdit
    from kairn.apps.desktop.tabs.project import ProjectTab

    state = AppState(active_project_root=str(tmp_path), active_project_manifest_path=str(tmp_path / "kairn_project.json"))
    report = _fake_report()
    tab = ProjectTab(state, QTextEdit())
    tab.overview._metrics_package_done({"process_result": {"sources_seen": 1, "sources_processed": 1, "output_dir": str(tmp_path / "out")}, "report": report, "collection_id": "c1", "run_id": "r1", "out_dir": str(tmp_path / "metrics")})

    assert state.last_observatory_report is report
    assert state.last_observatory_output_dir == str(tmp_path / "metrics")
    assert state.last_observatory_tables == report.tables
    assert state.last_observatory_warnings == report.warnings
    app.processEvents()


def test_analysis_load_observatory_report_from_state(monkeypatch, tmp_path):
    app = _qt_app(monkeypatch)
    from PySide6.QtWidgets import QTextEdit
    from kairn.apps.desktop.tabs.analysis import AnalysisTab

    state = AppState()
    state.last_observatory_report = _fake_report()
    state.last_observatory_output_dir = str(tmp_path / "metrics")
    tab = AnalysisTab(state, QTextEdit())
    tab.load_observatory_report_from_state()

    assert "Tables: 1" in tab.obs_summary.text()
    assert "Warnings: 1" in tab.obs_summary.text()
    assert tab.obs_tables.count() == 1
    assert tab.obs_tables.item(0).text() == "summary"
    app.processEvents()
