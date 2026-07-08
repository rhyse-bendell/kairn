from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .storage.repositories import get_collaboration, get_latest_run


def safe_name(name: str | None) -> str:
    value = (name or "default").strip()
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    return value.strip("._") or "default"


def new_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"run_{stamp}_{uuid.uuid4().hex[:8]}"


def _workspace_from_db(db_path: str) -> Path:
    return Path(db_path).resolve().parent


def ensure_run_dirs(db_path: str, collaboration_id: str | None = None, collection_id: str | None = None, run_id: str | None = None) -> dict[str, str]:
    workspace = _workspace_from_db(db_path)
    collab_name = collaboration_id or collection_id or "default"
    collab = get_collaboration(db_path, collaboration_id) if collaboration_id else None
    collab_safe = safe_name(collab["name"] if collab else collab_name)
    rid = run_id or new_run_id()
    if (workspace / "kairn_project.json").exists():
        run_dir = workspace / "runs" / rid
    else:
        run_dir = workspace / "collaborations" / collab_safe / "runs" / rid
    paths = {
        "workspace_dir": workspace,
        "run_dir": run_dir,
        "json_dir": run_dir / "json",
        "chunks_dir": run_dir / "json" / "chunks",
        "prompt_dir": run_dir / "json" / "prompt_chunks",
        "csv_dir": run_dir / "csv",
        "viz_dir": run_dir / "viz",
        "viz_units_dir": run_dir / "viz" / "units",
        "reports_dir": run_dir / "reports",
    }
    for p in paths.values():
        if isinstance(p, Path):
            p.mkdir(parents=True, exist_ok=True)
    meta = run_dir / "meta.json"
    if not meta.exists():
        meta.write_text(json.dumps({"run_id": rid, "collection_id": collection_id, "collaboration_id": collaboration_id}, indent=2), encoding="utf-8")
    return {k: str(v) for k, v in paths.items()} | {"run_id": rid, "meta_path": str(meta)}


def update_run_meta(path_or_run_id: str, key: str, value) -> str:
    p = Path(path_or_run_id)
    meta_path = p if p.name == "meta.json" else p / "meta.json"
    data = {}
    if meta_path.exists():
        data = json.loads(meta_path.read_text(encoding="utf-8"))
    data[key] = value
    meta_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return str(meta_path)


def get_run_output_paths(db_path: str, collaboration_id: str | None = None, collection_id: str | None = None, run_id: str | None = None) -> dict[str, str]:
    rid = run_id
    if not rid:
        latest = get_latest_run(db_path, collection_id=collection_id)
        rid = latest["id"] if latest else None
    return ensure_run_dirs(db_path, collaboration_id=collaboration_id, collection_id=collection_id, run_id=rid)
