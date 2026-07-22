from __future__ import annotations

from datetime import datetime
from pathlib import Path

from kairn.core.projects import read_source_registry
from kairn.core.workshop.intake import prepare_workshop_source
from kairn.core.observatory.report import build_observatory_report
from kairn.core.observatory.export import export_observatory_report
from kairn.core.observatory.source_processing import discover_observatory_sources, _process_discovered_sources


def _canonical_source_path(value: str | None) -> str | None:
    """Return a stable, case-insensitive identity for a source path."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("\\", "/").rstrip("/\\")
    if not text:
        return None
    try:
        normalized = Path(text).expanduser().resolve(strict=False)
        text = str(normalized)
    except Exception:
        text = str(Path(text).expanduser())
    text = text.replace("\\", "/").rstrip("/\\")
    return text.casefold() or None


def _source_identity_key(rec: dict, fallback_index: int | None = None) -> str:
    """Choose the duplicate-detection identity for a registry record."""
    return (
        _canonical_source_path(rec.get("original_path"))
        or _canonical_source_path(rec.get("project_path"))
        or str(rec.get("source_id") or "")
        or f"malformed-source-{fallback_index}"
    )


def _processing_path(rec: dict) -> str | None:
    """Return the path that should be processed for a registry record."""
    return rec.get("project_path") or rec.get("original_path") or None


def _processing_path_exists(rec: dict) -> bool:
    """Return whether the path that would be processed exists on disk."""
    path = _processing_path(rec)
    if not path:
        return False
    try:
        return Path(str(path)).expanduser().resolve(strict=False).exists()
    except Exception:
        return False


def _prefer_source_record(existing: dict, candidate: dict) -> dict:
    """Choose which duplicate record should be processed."""
    existing_exists = _processing_path_exists(existing)
    candidate_exists = _processing_path_exists(candidate)
    if candidate_exists and not existing_exists:
        return candidate
    if existing_exists and not candidate_exists:
        return existing

    existing_project_exists = bool(existing.get("project_path")) and _processing_path_exists({"project_path": existing.get("project_path")})
    candidate_project_exists = bool(candidate.get("project_path")) and _processing_path_exists({"project_path": candidate.get("project_path")})
    existing_copied = bool(existing.get("copied_into_project")) and existing_project_exists
    candidate_copied = bool(candidate.get("copied_into_project")) and candidate_project_exists
    if candidate_copied and not existing_copied:
        return candidate
    return existing


def _duplicate_reason_for_key(rec: dict) -> str:
    if _canonical_source_path(rec.get("original_path")):
        return "duplicate original_path"
    if _canonical_source_path(rec.get("project_path")):
        return "duplicate project_path"
    return "duplicate source_id"


def _dedupe_registered_sources(sources: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return registry records to process and duplicate records skipped."""
    groups: dict[str, list[dict]] = {}
    order: list[str] = []
    for idx, rec in enumerate(sources):
        key = _source_identity_key(rec, idx)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(rec)

    sources_to_process: list[dict] = []
    skipped_duplicates: list[dict] = []
    for key in order:
        records = groups[key]
        kept = records[0]
        for candidate in records[1:]:
            kept = _prefer_source_record(kept, candidate)
        sources_to_process.append(kept)
        kept_id = kept.get("source_id") or "unknown"
        for rec in records:
            if rec is kept:
                continue
            skipped_duplicates.append({
                "source_id": rec.get("source_id"),
                "original_path": rec.get("original_path"),
                "project_path": rec.get("project_path"),
                "duplicate_of_source_id": kept_id,
                "duplicate_key": key,
                "skipped_reason": _duplicate_reason_for_key(rec),
            })
    return sources_to_process, skipped_duplicates


def process_registered_sources(project: dict, db_path: str, collection_id=None, run_id=None, profile=None, workspace_dir=None) -> dict:
    """Process each unique source in the existing project source registry."""
    all_sources = read_source_registry(project).get("sources", [])
    sources, skipped_duplicates = _dedupe_registered_sources(all_sources)
    result = {"sources_seen": len(all_sources), "sources_considered": len(sources), "sources_processed": 0, "sources_skipped_duplicates": len(skipped_duplicates), "skipped_sources": skipped_duplicates, "warnings": []}
    for skipped in skipped_duplicates:
        result["warnings"].append(f"Skipped duplicate registered source {skipped.get('source_id') or 'unknown'} because it has the same source identity as {skipped.get('duplicate_of_source_id') or 'unknown'}.")
    current_collection_id = collection_id
    current_run_id = run_id
    output_dir = None
    all_discovered = []
    registered_source_results = []
    for rec in sources:
        path = _processing_path(rec)
        if not path:
            result["warnings"].append(f"Source {rec.get('source_id') or 'unknown'} has no path; skipped.")
            continue
        discovered = discover_observatory_sources(path)
        for src in discovered:
            src["registered_source_id"] = rec.get("source_id")
            src["registered_original_path"] = rec.get("original_path")
            src["registered_project_path"] = rec.get("project_path")
            src["registered_processing_path"] = path
        all_discovered.extend(discovered)
        registered_source_results.append({"registered_source": rec, "processing_path": path, "discovered_sources": discovered})

    processing_summary, route_warnings = _process_discovered_sources(all_discovered, db_path)
    result["warnings"].extend(route_warnings)
    result["processing_summary"] = processing_summary
    result["source_processing_summary"] = processing_summary
    result["discovered_source_count"] = len(all_discovered)

    for source_result in registered_source_results:
        rec = source_result["registered_source"]
        path = source_result["processing_path"]
        out = {}
        legacy_warnings = []
        try:
            out = prepare_workshop_source(path, db_path, workspace_dir or project.get("project_root") or ".", collection_id=current_collection_id, run_id=current_run_id, profile=profile or "problem_framing_workshop", extract=False)
            current_collection_id = out.get("collection_id") or current_collection_id
            current_run_id = out.get("run_id") or current_run_id
            output_paths = out.get("output_paths") or {}
            output_dir = output_paths.get("out_dir") or output_paths.get("workshop_intake_summary_json")
            if output_dir and Path(output_dir).is_file():
                output_dir = str(Path(output_dir).parent)
        except Exception as exc:
            legacy_warnings.append(f"Legacy workshop intake skipped for {path}: {exc}")
        result["sources_processed"] += 1
        source_result["processing_summary"] = processing_summary
        source_result["legacy_intake"] = out
        result.setdefault("source_results", []).append(source_result)
        result["warnings"].extend(legacy_warnings + (out.get("warnings") or [] if isinstance(out, dict) else []))
    result["discovered_sources"] = all_discovered
    result["collection_id"] = current_collection_id
    result["run_id"] = current_run_id
    if output_dir:
        result["output_dir"] = str(output_dir)
    return result


def generate_metrics_package_for_project(project: dict, state_values: dict) -> dict:
    process_result = process_registered_sources(project=project, db_path=state_values.get("db_path"), collection_id=state_values.get("collection_id"), run_id=state_values.get("run_id"), profile=state_values.get("profile"), workspace_dir=state_values.get("workspace_dir"))
    collection_id = process_result.get("collection_id") or state_values.get("collection_id")
    run_id = process_result.get("run_id") or state_values.get("run_id")
    report = build_observatory_report(project=project, db_path=state_values.get("db_path"), run_id=run_id, team=None, activity=None, bin_minutes=15)
    if process_result.get("output_dir"):
        out_dir = Path(process_result["output_dir"]) / "observatory_metrics"
    elif state_values.get("active_run_reports_dir"):
        out_dir = Path(state_values["active_run_reports_dir"]) / "observatory_metrics"
    else:
        out_dir = Path(project.get("project_root") or state_values.get("workspace_dir") or ".") / "exports" / f"observatory_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    paths = export_observatory_report(report, out_dir)
    return {"process_result": process_result, "report": report, "paths": paths, "collection_id": collection_id, "run_id": run_id, "out_dir": paths["out_dir"]}
