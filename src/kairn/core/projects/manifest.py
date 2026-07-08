from __future__ import annotations

import json
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

MANIFEST_FILENAME = "kairn_project.json"
SCHEMA_VERSION = 1
DEFAULT_SETTINGS = {
    "copy_sources_into_project": False,
    "safe_archive_extract": True,
    "parse_remote_tldraw_events": True,
    "contribution_filter_default": "user_originated",
    "default_idle_gap_minutes": 10,
    "timezone": "UTC",
    "anonymize_exports": False,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _manifest_path(project_root_or_manifest_path: str | Path) -> Path:
    p = Path(project_root_or_manifest_path).expanduser()
    return p if p.name == MANIFEST_FILENAME else p / MANIFEST_FILENAME


def _database_value(project_root: Path, database_path: str | Path) -> str:
    db = Path(database_path)
    try:
        return str(db.resolve().relative_to(project_root.resolve()))
    except Exception:
        return "kairn.db" if db.name == "kairn.db" else str(db)


def create_project_manifest(name, description, project_root, database_path, profile="problem_framing_workshop") -> dict:
    root = Path(project_root).expanduser().resolve()
    now = _now()
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": str(uuid.uuid4()),
        "name": name or "Untitled Project",
        "description": description or "",
        "created_at": now,
        "updated_at": now,
        "project_root": str(root),
        "database_path": _database_value(root, database_path),
        "active_profile": profile,
        "active_collaboration_id": None,
        "active_collection_id": None,
        "active_run_id": None,
        "sources": [],
        "settings": deepcopy(DEFAULT_SETTINGS),
    }


def load_project_manifest(project_root_or_manifest_path) -> dict:
    path = _manifest_path(project_root_or_manifest_path)
    return json.loads(path.read_text(encoding="utf-8"))


def save_project_manifest(manifest: dict) -> str:
    manifest = dict(manifest)
    manifest["updated_at"] = _now()
    root = Path(manifest["project_root"]).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    path = root / MANIFEST_FILENAME
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(path)


def update_project_manifest(project_root_or_manifest_path, **fields) -> dict:
    manifest = load_project_manifest(project_root_or_manifest_path)
    manifest.update(fields)
    save_project_manifest(manifest)
    return manifest
