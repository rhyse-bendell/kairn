from __future__ import annotations
import re, sqlite3
from pathlib import Path
from kairn.core.profiles import get_default_profile

_RESULT_UNKNOWN = {"value": "unknown", "confidence": 0.0, "reason": "no matching catalog rule", "warnings": []}

TASK_MODULES = ["Individual Synthesis","Team Synthesis","Framing Elements & Terms","Problem Framing Statement","Map & Statement Questions & Feedback","Reflection & Building Motivation","Pre-Workshop Introduction Template","TLDraw Whiteboard Tutorial"]

def extract_task_module(rel_path: str) -> str | None:
    low=(rel_path or '').lower()
    return next((m for m in TASK_MODULES if m.lower() in low), None)

def extract_file_id(rel_path: str) -> str | None:
    m=re.search(r"\[([^\]]+)\]", rel_path or "")
    return m.group(1) if m else None


def _artifact_text(artifact: dict) -> tuple[str, str, str, str]:
    rel = str(artifact.get("rel_path") or artifact.get("path") or "")
    name = str(artifact.get("name") or Path(rel).name)
    ext = str(artifact.get("extension") or Path(name).suffix).lower()
    kind = str(artifact.get("kind") or "").lower()
    return rel, name, ext, kind


def _has_audit_logs(path: str | None) -> bool | None:
    if not path:
        return None
    try:
        p = Path(path)
        if not p.exists() or p.stat().st_size == 0:
            return None
        conn = sqlite3.connect(str(p))
        try:
            row = conn.execute("select 1 from sqlite_master where type='table' and name='audit_logs'").fetchone()
            return bool(row)
        finally:
            conn.close()
    except Exception:
        return None


def detect_source_type(artifact: dict, profile: dict | None = None) -> dict:
    rel, name, ext, kind = _artifact_text(artifact); hay = f"{rel} {name}".lower(); warnings=[]
    value, conf, reason = "unknown", 0.0, "no source-type rule matched"
    if ext in {".db", ".sqlite", ".sqlite3"} or kind == "sqlite":
        if re.search(r"tl\s*draw|tldraw|logs?", hay):
            value, conf, reason = "tldraw_sqlite", 0.72, "SQLite-like file name suggests TLDraw/log source"
            audit = _has_audit_logs(artifact.get("path"))
            if audit is True:
                conf, reason = 0.97, "SQLite database contains audit_logs table"
            elif audit is False:
                warnings.append("sqlite file did not contain audit_logs table")
        else:
            value, conf, reason = "sqlite", 0.45, "SQLite-like extension without profile-specific source hint"
    elif ext == ".csv" and re.search(r"daily[_ -]?log|activity[_ -]?log|drive.*activity", hay):
        value, conf, reason = "drive_activity_csv", 0.92, "CSV name matches activity-log pattern"
    elif "changelog" in hay:
        value, conf, reason = ("document_changelog", 0.91, "name/path contains changelog")
    elif ext in {".html", ".htm"}:
        value, conf, reason = ("google_doc_html_export", 0.9, "Google document HTML export") if "email_export" in hay else ("html_export", 0.86, "HTML extension")
    elif ext == ".docx":
        value, conf, reason = "static_docx", 0.75, "DOCX extension"
    elif ext == ".pptx":
        value, conf, reason = "static_pptx", 0.82, "PPTX extension"
    elif ext == ".zip":
        value, conf, reason = "archive", 0.96, "ZIP archive extension"
    elif ext in {".csv", ".jsonl", ".vtt", ".srt", ".txt"} and re.search(r"transcript|diarized|utterance|captions?", hay):
        value, conf, reason = "clean_transcript", 0.9, "transcript-like name and extension"
    elif re.search(r"rubric|scores?|ratings?|rater|outcomes?", hay):
        value, conf, reason = "rubric_scores", 0.78, "name/path matches rubric score pattern"
    return {"value": value, "confidence": conf, "reason": reason, "warnings": warnings}


def detect_artifact_role(artifact: dict, profile: dict | None = None) -> dict:
    profile = profile or get_default_profile(); rel, name, ext, kind = _artifact_text(artifact); text=f"{rel} {name} {kind}"
    best = None
    for rule in profile.get("role_rules", []):
        pattern = rule.get("regex") or re.escape(rule.get("contains", ""))
        if pattern and re.search(pattern, text):
            item = {"value": rule["role"], "confidence": float(rule.get("confidence", 0.7)), "reason": f"matched profile role rule: {pattern}", "warnings": []}
            if best is None or item["confidence"] > best["confidence"]:
                best = item
    if best:
        return best
    st = detect_source_type(artifact, profile)
    mapping = {"tldraw_sqlite":"tldraw_board_log", "drive_activity_csv":"drive_activity_log", "google_doc_html_export":"google_doc_html_export", "clean_transcript":"transcript", "archive":"archive", "rubric_scores":"rubric_scores"}
    if st["value"] in mapping:
        return {"value": mapping[st["value"]], "confidence": max(0.55, st["confidence"]-0.05), "reason": f"inferred from source type {st['value']}", "warnings": st.get("warnings", [])}
    return dict(_RESULT_UNKNOWN)


def extract_team_hint(rel_path: str) -> dict:
    m = re.search(r"(?i)(?:\bteam\s*|\bt)(\d{1,3})\b", rel_path or "")
    return {"value": f"Team {int(m.group(1))}" if m else None, "confidence": 0.86 if m else 0.0, "reason": "matched team hint" if m else "no team hint", "warnings": []}


def extract_participant_hint(rel_path: str) -> dict:
    m = re.search(r"(?i)(?:\bparticipant\s*|\bp)(\d{1,4})\b", rel_path or "")
    return {"value": f"Participant {int(m.group(1))}" if m else None, "confidence": 0.86 if m else 0.0, "reason": "matched participant hint" if m else "no participant hint", "warnings": []}


def classify_artifact_for_catalog(artifact: dict, profile: dict | None = None) -> dict:
    profile = profile or get_default_profile(); source=detect_source_type(artifact, profile); role=detect_artifact_role(artifact, profile); team=extract_team_hint(str(artifact.get("rel_path") or "")); part=extract_participant_hint(str(artifact.get("rel_path") or ""))
    warnings = []
    for r in (source, role, team, part): warnings.extend(r.get("warnings", []))
    if source["confidence"] < 0.5: warnings.append("low source-type confidence")
    if role["confidence"] < 0.5: warnings.append("low artifact-role confidence")
    return {"source_type": source, "artifact_role": role, "team_hint": team, "participant_hint": part, "task_module": extract_task_module(str(artifact.get("rel_path") or "")), "file_id": extract_file_id(str(artifact.get("rel_path") or artifact.get("name") or "")), "warnings": warnings}
