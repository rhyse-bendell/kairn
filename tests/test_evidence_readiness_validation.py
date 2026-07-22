from __future__ import annotations

import json
import subprocess
import os
import sys
from pathlib import Path

import pytest


def _make_project(tmp_path, with_transcript=False):
    from kairn.core.projects import create_project, register_project_source

    project = create_project("Evidence Readiness Synthetic", kairn_home=tmp_path)
    drive = tmp_path / "drive_source"; drive.mkdir()
    (drive / "dailyLog.csv").write_text("time,user,action,file_id,file name,mimeType,parent folder\n2024-01-01,Alice,create,f1,Idea Doc,text/plain,Team 1\n", encoding="utf-8")
    register_project_source(project, str(drive), copy_into_project=False)
    if with_transcript:
        tr = tmp_path / "transcript_source"; tr.mkdir()
        (tr / "labeledTranscriptions.srt").write_text("1\n00:00:01,000 --> 00:00:03,000\nBob: hello there problem framing\n", encoding="utf-8")
        register_project_source(project, str(tr), copy_into_project=False)
    return project


def test_core_project_pipeline_importable_without_pyside():
    import kairn.core.observatory.project_pipeline as pipeline
    assert hasattr(pipeline, "process_registered_sources")


def test_desktop_project_tab_backwards_compatible_helpers():
    pytest.importorskip("PySide6")
    import kairn.apps.desktop.tabs.project as project_tab
    assert hasattr(project_tab, "process_registered_sources")
    assert hasattr(project_tab, "_generate_metrics_package_for_project")


def test_source_processing_summary_report_includes_registered_provenance_columns(tmp_path):
    from kairn.core.observatory import build_observatory_report, process_registered_sources
    project = _make_project(tmp_path, with_transcript=True)
    process_registered_sources(project, project["db_path"])
    report = build_observatory_report(project, project["db_path"])
    table = next(t for t in report.tables if t.table_id == "source_processing_summary")
    assert "registered_source_id" in table.columns
    assert "registered_processing_path" in table.columns


def test_evidence_readiness_validation_produces_required_files(tmp_path):
    from kairn.core.validation import run_evidence_readiness_validation
    project = _make_project(tmp_path, with_transcript=True)
    out = tmp_path / "readiness"
    result = run_evidence_readiness_validation(project, out, expected_streams=["drive", "transcript"])
    for rel in ["evidence_readiness_checks.csv", "evidence_readiness_summary.json", "evidence_readiness_report.md", "evidence_readiness_manifest.json", "observatory_metrics/report_manifest.json", "artifact_progression/artifact_progression_manifest.json"]:
        assert (out / rel).exists()
    assert "ready_for_local_llm" in result["summary"]


def test_expected_missing_stream_fails(tmp_path):
    from kairn.core.validation import run_evidence_readiness_validation
    project = _make_project(tmp_path, with_transcript=False)
    result = run_evidence_readiness_validation(project, tmp_path / "readiness", expected_streams=["drive", "transcript"])
    assert result["summary"]["ready_for_local_llm"] is False
    checks = {c["check_id"]: c for c in result["summary"]["checks"]}
    assert checks["stream_transcript_status"]["status"] == "fail"


def test_missing_non_expected_stream_warns_not_fails(tmp_path):
    from kairn.core.validation import run_evidence_readiness_validation
    project = _make_project(tmp_path, with_transcript=False)
    result = run_evidence_readiness_validation(project, tmp_path / "readiness", expected_streams=["drive"])
    checks = {c["check_id"]: c for c in result["summary"]["checks"]}
    assert checks["stream_transcript_status"]["status"] == "warn"


def test_cli_validate_evidence_smoke(tmp_path):
    project = _make_project(tmp_path, with_transcript=False)
    out = tmp_path / "cli_readiness"
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    cp = subprocess.run([sys.executable, "-m", "kairn.cli.main", "validate", "evidence", project["project_root"], "--out", str(out), "--expect-stream", "drive"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, env=env)
    payload = json.loads(cp.stdout)
    assert payload["manifest"]["project_id"] == project["project_id"]
    assert (out / "evidence_readiness_manifest.json").exists()


def test_observatory_report_process_sources_smoke(tmp_path):
    project = _make_project(tmp_path, with_transcript=False)
    out = tmp_path / "obs"
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    cp = subprocess.run([sys.executable, "-m", "kairn.cli.main", "observatory", "report", project["project_root"], "--process-sources", "--out", str(out)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, env=env)
    payload = json.loads(cp.stdout)
    assert payload["process_summary"]["sources_processed"] == 1
    assert (out / "tables" / "source_processing_summary.csv").exists()
