from __future__ import annotations

import csv, json, uuid
from datetime import datetime, timezone
from pathlib import Path

from kairn.core.observatory import build_observatory_report, export_observatory_report, process_registered_sources
from kairn.core.progression import prepare_artifact_progression, generate_deterministic_progression_candidates, export_artifact_progression_package
from kairn.core.progression import repository as progression_repo

VALID_STREAMS = {"drive", "document_changelog", "tldraw", "transcript"}
CHECK_COLUMNS = ["check_id", "status", "summary", "detail", "suggested_action"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _check(checks, check_id, status, summary, detail="", suggested_action=""):
    checks.append({"check_id": check_id, "status": status, "summary": summary, "detail": detail, "suggested_action": suggested_action})


def _table(report, table_id):
    return next((t for t in report.tables if t.table_id == table_id), None)


def _write_checks(path: Path, checks: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CHECK_COLUMNS, extrasaction="ignore")
        w.writeheader(); w.writerows(checks)


def _write_report(path: Path, manifest: dict, summary: dict, checks: list[dict], stream_rows: list[dict]) -> None:
    failures = [c for c in checks if c["status"] == "fail"]
    actions = "\n".join(f"- **{c['check_id']}**: {c['suggested_action'] or c['summary']}" for c in failures) or "- No hard failures detected. Review warnings before semantic assistance."
    streams = "\n".join(f"- {r.get('source_stream')}: {r.get('status')} ({r.get('records')} records)" for r in stream_rows) or "- No stream status rows were available."
    text = f"""# Evidence Readiness Validation

## Project summary
- Project: {manifest.get('project_name') or ''}
- Project ID: {manifest.get('project_id') or ''}
- Project root: {manifest.get('project_root') or ''}
- Expected streams: {', '.join(manifest.get('expected_streams') or []) or 'none specified'}

## Source processing summary
- Registered sources seen: {summary.get('sources_seen', 0)}
- Unique sources considered: {summary.get('sources_considered', 0)}
- Sources processed: {summary.get('sources_processed', 0)}
- Discovered sources: {summary.get('discovered_source_count', 0)}
- Duplicate sources skipped: {summary.get('sources_skipped_duplicates', 0)}

## Stream status summary
{streams}

## Normalized event summary
- Normalized observatory events: {summary.get('normalized_event_count', 0)}
- Normalized streams represented: {', '.join(summary.get('normalized_streams') or []) or 'none'}

## Artifact progression summary
- Artifacts in manifest: {summary.get('artifact_manifest_count', 0)}
- Evidence units: {summary.get('evidence_unit_count', 0)}
- Evidence units with source locators: {summary.get('evidence_units_with_source_locator', 0)}
- Deterministic candidates: {summary.get('deterministic_candidate_count', 0)}

## Readiness verdict
**Ready for local semantic assistance:** {manifest.get('ready_for_local_llm')}

This verdict only means the deterministic evidence layer is structurally ready for later local semantic assistance. It is not a validation of research findings, participant performance, collaboration quality, or cognition.

## Failures and recommended actions
{actions}
"""
    path.write_text(text, encoding="utf-8")


def run_evidence_readiness_validation(project: dict, out_dir: str | Path, profile: str = "problem_framing_workshop", include_reflections: bool = False, expected_streams: list[str] | None = None, bin_minutes: int = 15) -> dict:
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    expected = [s for s in (expected_streams or []) if s in VALID_STREAMS]
    db_path = project.get("db_path") or str(Path(project.get("project_root", ".")) / "kairn.db")
    process = process_registered_sources(project, db_path, collection_id=project.get("active_collection_id"), run_id=project.get("active_run_id"), profile=profile, workspace_dir=project.get("project_root"))
    report = build_observatory_report(project, db_path, run_id=process.get("run_id") or project.get("active_run_id"), bin_minutes=bin_minutes)
    obs_dir = out / "observatory_metrics"
    obs_paths = export_observatory_report(report, obs_dir)
    prog_summary = prepare_artifact_progression(project, collection_id=process.get("collection_id") or project.get("active_collection_id"), profile=profile, include_reflections=include_reflections)
    candidate_summary = generate_deterministic_progression_candidates(db_path, prog_summary["analysis_run_id"])
    prog_dir = out / "artifact_progression"
    prog_export = export_artifact_progression_package(db_path, prog_summary["analysis_run_id"], str(prog_dir))

    checks=[]
    _check(checks, "source_registry_present", "pass" if process.get("sources_seen",0)>0 else "warn", f"{process.get('sources_seen',0)} registered sources seen", suggested_action="Register project sources before validation." )
    _check(checks, "sources_processed", "pass" if process.get("sources_processed",0)>0 else "fail", f"{process.get('sources_processed',0)} sources processed", suggested_action="Confirm registered source paths exist and are supported.")
    _check(checks, "discovered_sources_present", "pass" if process.get("discovered_source_count",0)>0 else "fail", f"{process.get('discovered_source_count',0)} observatory sources discovered", suggested_action="Add supported drive, changelog, TLDraw, or transcript sources.")
    _check(checks, "no_duplicate_source_contamination", "pass", f"{process.get('sources_skipped_duplicates',0)} duplicate sources skipped", detail="Duplicates are deduplicated before processing.")
    sps = _table(report, "source_processing_summary")
    cols = set(sps.columns if sps else [])
    _check(checks, "source_processing_summary_export_has_registered_provenance", "pass" if {"registered_source_id","registered_processing_path"} <= cols else "fail", "Registered-source provenance columns are exported" if {"registered_source_id","registered_processing_path"} <= cols else "Registered-source provenance columns are missing", suggested_action="Update observatory diagnostic table columns.")
    stream_table = _table(report, "stream_record_counts")
    stream_rows = stream_table.rows if stream_table else []
    parsed_streams=[]
    for stream in ["drive","document_changelog","tldraw","transcript"]:
        row = next((r for r in stream_rows if r.get("source_stream")==stream), {})
        status = row.get("status") or "not_detected"
        ok = status in {"parsed","parsed_with_warnings"}
        parsed = ok and int(float(row.get("records") or 0)) > 0
        if parsed: parsed_streams.append(stream)
        check_status = "pass" if ok else ("fail" if stream in expected else "warn")
        _check(checks, f"stream_{stream}_status", check_status, f"{stream} status is {status}", detail=json.dumps(row), suggested_action=f"Provide and register a parseable {stream} source." if check_status != "pass" else "")
    norm = _table(report, "normalized_observatory_events")
    norm_count = len(norm.rows) if norm else 0
    norm_streams = sorted({r.get("source_stream") for r in (norm.rows if norm else []) if r.get("source_stream")})
    _check(checks, "normalized_events_present", "pass" if norm_count>0 else "fail", f"{norm_count} normalized events available", suggested_action="Process supported observatory sources.")
    _check(checks, "normalized_events_have_multiple_streams", "pass" if (len(parsed_streams)<=1 or len(norm_streams)>1) else "warn", f"Normalized events include {len(norm_streams)} stream(s)", detail=", ".join(norm_streams), suggested_action="Confirm all parsed streams produce normalized rows.")
    analysis_run_id = prog_summary["analysis_run_id"]
    manifest_rows = progression_repo.fetch_rows(db_path, progression_repo.MANIFEST_TABLE, analysis_run_id)
    evidence_rows = progression_repo.fetch_rows(db_path, progression_repo.EVIDENCE_TABLE, analysis_run_id)
    candidate_count = candidate_summary.get("candidate_count",0)
    loc_count = sum(1 for r in evidence_rows if r.get("source_locator"))
    loc_ok = bool(evidence_rows) and loc_count >= max(1, int(len(evidence_rows)*0.9))
    _check(checks, "progression_manifest_present", "pass" if manifest_rows else "fail", f"{len(manifest_rows)} artifact manifest rows", suggested_action="Register artifacts that can be cataloged for progression.")
    _check(checks, "progression_evidence_units_present", "pass" if evidence_rows else "fail", f"{len(evidence_rows)} evidence units", suggested_action="Provide artifacts with extractable deterministic content.")
    _check(checks, "progression_source_locators_present", "pass" if loc_ok else "warn", f"{loc_count}/{len(evidence_rows)} evidence units include source locators", suggested_action="Review extraction support for sources without locators.")
    amb = [w for w in prog_summary.get("warnings",[]) if "multiple transcript" in w.lower() or "multiple tldraw" in w.lower()]
    amb_expected = any(s in expected for s in ["transcript","tldraw"])
    _check(checks, "progression_no_ambiguous_source_scoping", "fail" if amb and amb_expected else ("warn" if amb else "pass"), "No ambiguous transcript/TLDraw source scoping detected" if not amb else "; ".join(amb), suggested_action="Narrow source registration so each expected transcript/TLDraw scope is unambiguous.")
    _check(checks, "deterministic_candidates_generated", "pass" if candidate_count>0 else "warn", f"{candidate_count} deterministic candidates generated", suggested_action="Zero candidates can be legitimate; review evidence units and stage ordering.")
    failures = [c for c in checks if c["status"]=="fail"]
    ready = not failures and bool(evidence_rows) and loc_ok and Path(obs_paths.get("out_dir", obs_dir)).exists() and prog_dir.exists()
    _check(checks, "ready_for_local_llm", "pass" if ready else "fail", "Deterministic evidence layer is structurally ready for local semantic assistance" if ready else "Deterministic evidence layer is not structurally ready", suggested_action="Resolve failed checks before using local semantic assistance.")
    failures = [c for c in checks if c["status"]=="fail"]
    warnings = [c for c in checks if c["status"]=="warn"]
    summary = {**{k: process.get(k) for k in ["sources_seen","sources_considered","sources_processed","discovered_source_count","sources_skipped_duplicates"]}, "normalized_event_count": norm_count, "normalized_streams": norm_streams, "artifact_manifest_count": len(manifest_rows), "evidence_unit_count": len(evidence_rows), "evidence_units_with_source_locator": loc_count, "deterministic_candidate_count": candidate_count, "ready_for_local_llm": ready, "warning_count": len(warnings), "failure_count": len(failures), "checks": checks}
    checks_csv = out / "evidence_readiness_checks.csv"; _write_checks(checks_csv, checks)
    (out / "evidence_readiness_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    manifest = {"validation_run_id": str(uuid.uuid4()), "created_at": _now(), "project_id": project.get("project_id"), "project_name": project.get("name"), "project_root": project.get("project_root"), "expected_streams": expected, "ready_for_local_llm": ready, "observatory_metrics_path": str(obs_dir), "artifact_progression_path": str(prog_dir), "checks_csv_path": str(checks_csv), "warning_count": len(warnings), "failure_count": len(failures)}
    (out / "evidence_readiness_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _write_report(out / "evidence_readiness_report.md", manifest, summary, checks, stream_rows)
    return {"out_dir": str(out), "manifest": manifest, "summary": summary, "observatory_export": obs_paths, "artifact_progression_export": prog_export}
