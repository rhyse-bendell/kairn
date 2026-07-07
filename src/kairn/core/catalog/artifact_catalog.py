from __future__ import annotations
import csv, json
from collections import Counter
from pathlib import Path
from kairn.core.storage import repositories as repo
from kairn.core.profiles import load_profile
from .detection import classify_artifact_for_catalog

COLUMNS = ["artifact_id","collection_id","rel_path","name","extension","kind","size_bytes","modified_at","event_count","source_type","source_confidence","source_reason","artifact_role","role_confidence","role_reason","team_hint","team_confidence","participant_hint","participant_confidence","task_module","file_id","confidence","warnings"]


def _collection_ids_for_collaboration(db_path: str, collaboration_id: str) -> set[str]:
    return {c["id"] for c in repo.fetchall(db_path, "collections") if c.get("collaboration_id") == collaboration_id}


def build_artifact_catalog(db_path: str, collection_id: str | None = None, collaboration_id: str | None = None, profile_name_or_path: str | None = None) -> list[dict]:
    if not collection_id and not collaboration_id:
        raise ValueError("collection_id or collaboration_id is required to build an artifact catalog")
    profile = load_profile(profile_name_or_path)
    artifacts = repo.list_artifacts(db_path, collection_id=collection_id)
    if collaboration_id and not collection_id:
        ids = _collection_ids_for_collaboration(db_path, collaboration_id)
        artifacts = [a for a in artifacts if a.get("collection_id") in ids]
    rows=[]
    for a in artifacts:
        c = classify_artifact_for_catalog(a, profile); st=c["source_type"]; role=c["artifact_role"]; team=c["team_hint"]; part=c["participant_hint"]
        rows.append({
            "artifact_id": a.get("id"), "collection_id": a.get("collection_id"), "rel_path": a.get("rel_path"), "name": a.get("name"), "extension": a.get("extension"), "kind": a.get("kind"), "size_bytes": a.get("size_bytes"), "modified_at": a.get("modified_at"), "event_count": a.get("event_count", 0),
            "source_type": st["value"], "source_confidence": st["confidence"], "source_reason": st["reason"],
            "artifact_role": role["value"], "role_confidence": role["confidence"], "role_reason": role["reason"],
            "team_hint": team["value"], "team_confidence": team["confidence"], "participant_hint": part["value"], "participant_confidence": part["confidence"], "task_module": c.get("task_module"), "file_id": c.get("file_id"), "confidence": min(st["confidence"], role["confidence"]), "warnings": "; ".join(c["warnings"])
        })
    return rows


def summarize_artifact_catalog(catalog: list[dict], profile: dict) -> dict:
    def count(key): return dict(Counter((r.get(key) or "none") for r in catalog))
    by_source = count("source_type")
    expected = {s: {"present": by_source.get(s, 0) > 0, "count": by_source.get(s, 0)} for s in profile.get("expected_source_types", [])}
    return {"profile": profile.get("name"), "total_artifact_count": len(catalog), "counts_by_source_type": by_source, "counts_by_artifact_role": count("artifact_role"), "counts_by_team_hint": count("team_hint"), "counts_by_participant_hint": count("participant_hint"), "expected_source_coverage": expected, "warnings": [r for r in catalog if r.get("warnings")], "low_confidence_mappings": [r for r in catalog if float(r.get("source_confidence") or 0) < 0.5 or float(r.get("role_confidence") or 0) < 0.5]}


def _summary_text(summary: dict) -> str:
    lines=[f"Artifact catalog summary ({summary.get('profile')})", f"Total artifacts: {summary['total_artifact_count']}", "", "Source types:"]
    lines += [f"- {k}: {v}" for k,v in summary["counts_by_source_type"].items()]
    lines += ["", "Artifact roles:"] + [f"- {k}: {v}" for k,v in summary["counts_by_artifact_role"].items()]
    lines += ["", f"Warnings: {len(summary['warnings'])}", f"Low-confidence mappings: {len(summary['low_confidence_mappings'])}"]
    return "\n".join(lines)+"\n"


def export_artifact_catalog(db_path: str, out_dir: str, collection_id: str | None = None, collaboration_id: str | None = None, profile_name_or_path: str | None = None) -> dict:
    profile = load_profile(profile_name_or_path); catalog = build_artifact_catalog(db_path, collection_id, collaboration_id, profile_name_or_path); summary = summarize_artifact_catalog(catalog, profile)
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    csv_path=out/"artifact_catalog.csv"; json_path=out/"artifact_catalog.json"; sj=out/"artifact_catalog_summary.json"; st=out/"artifact_catalog_summary.txt"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=COLUMNS); w.writeheader(); w.writerows(catalog)
    json_path.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    sj.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    st.write_text(_summary_text(summary), encoding="utf-8")
    return {"catalog_csv": str(csv_path), "catalog_json": str(json_path), "summary_json": str(sj), "summary_txt": str(st), "summary": summary}
