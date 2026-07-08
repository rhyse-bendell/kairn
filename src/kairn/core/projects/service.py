from __future__ import annotations

import json
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from kairn.core.storage.sqlite import connect, init_db
from kairn.core.storage import repositories as repo
from .manifest import DEFAULT_SETTINGS, MANIFEST_FILENAME, create_project_manifest, load_project_manifest, save_project_manifest, update_project_manifest
from .paths import get_default_kairn_home, project_root_for_name


class ProjectExistsError(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_path(manifest: dict) -> Path:
    db = Path(manifest.get("database_path") or "kairn.db")
    return db if db.is_absolute() else Path(manifest["project_root"]) / db


def _descriptor(manifest: dict) -> dict:
    root = Path(manifest["project_root"])
    db = _db_path(manifest)
    return {
        "project_id": manifest["project_id"],
        "name": manifest["name"],
        "project_root": str(root),
        "manifest_path": str(root / MANIFEST_FILENAME),
        "db_path": str(db),
        "active_collaboration_id": manifest.get("active_collaboration_id"),
        "active_collection_id": manifest.get("active_collection_id"),
        "active_run_id": manifest.get("active_run_id"),
        "active_profile": manifest.get("active_profile", "problem_framing_workshop"),
        "settings": manifest.get("settings", DEFAULT_SETTINGS),
    }


def ensure_project_structure(project_root: str | Path) -> dict[str, str]:
    root = Path(project_root)
    names = ["data", "data/original", "data/extracted", "data/linked_sources", "data/staging", "catalog", "parsed", "parsed/tldraw", "parsed/drive", "parsed/documents", "parsed/process", "runs", "exports", "exports/manual_exports", "logs", "settings"]
    paths = {}
    for name in names:
        p = root / name; p.mkdir(parents=True, exist_ok=True); paths[name.replace('/', '_') or 'root'] = str(p)
    return paths


def _write_settings(root: Path, manifest: dict) -> None:
    settings = root / "settings"
    files = {
        "project_settings.json": manifest.get("settings", DEFAULT_SETTINGS),
        "profile_settings.json": {"active_profile": manifest.get("active_profile", "problem_framing_workshop")},
        "source_registry.json": {"sources": []},
        "participant_map.json": {"participants": []},
    }
    for name, data in files.items():
        path = settings / name
        if not path.exists(): path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(str(path)); init_db(conn); conn.close()


def _unique_root(name: str, home: Path, exist_ok: bool) -> Path:
    root = project_root_for_name(name, home)
    if exist_ok or not root.exists(): return root
    for i in range(2, 1000):
        candidate = root.with_name(f"{root.name}_{i}")
        if not candidate.exists(): return candidate
    raise ProjectExistsError(f"Could not create a unique project folder for {name!r}")


def create_project(name: str, description: str = "", kairn_home: str | Path | None = None, profile: str = "problem_framing_workshop", exist_ok: bool = False) -> dict:
    home = Path(kairn_home).expanduser() if kairn_home else get_default_kairn_home()
    home.mkdir(parents=True, exist_ok=True)
    root = _unique_root(name, home, exist_ok); root.mkdir(parents=True, exist_ok=exist_ok)
    ensure_project_structure(root)
    db = root / "kairn.db"
    manifest = create_project_manifest(name, description, root, db, profile)
    _write_settings(root, manifest)
    _init_db(db)
    cid = repo.create_collaboration(str(db), name or "Untitled Project", description or "", default_root_path=str(root))
    manifest["active_collaboration_id"] = cid
    save_project_manifest(manifest)
    return _descriptor(manifest)


def _resolve_project_ref(project_root_or_manifest_path: str | Path) -> Path:
    p = Path(project_root_or_manifest_path).expanduser()
    if p.exists() or p.name == MANIFEST_FILENAME or str(p.parent) not in (".", ""):
        return p
    for item in list_projects():
        if item.get("name") == str(project_root_or_manifest_path) or Path(item.get("project_root", "")).name == str(project_root_or_manifest_path):
            return Path(item["manifest_path"])
    return p

def load_project(project_root_or_manifest_path: str | Path) -> dict:
    manifest = load_project_manifest(_resolve_project_ref(project_root_or_manifest_path))
    root = Path(manifest["project_root"])
    ensure_project_structure(root); _write_settings(root, manifest); _init_db(_db_path(manifest))
    return _descriptor(manifest)


def list_projects(kairn_home: str | Path | None = None) -> list[dict]:
    home = Path(kairn_home).expanduser() if kairn_home else get_default_kairn_home()
    if not home.exists(): return []
    out=[]
    for manifest_path in sorted(home.glob(f"*/{MANIFEST_FILENAME}")):
        try:
            m=load_project_manifest(manifest_path)
            out.append({"name":m.get("name"),"project_root":m.get("project_root"),"manifest_path":str(manifest_path),"updated_at":m.get("updated_at"),"active_profile":m.get("active_profile"),"active_collaboration_id":m.get("active_collaboration_id")})
        except Exception:
            continue
    return sorted(out, key=lambda r: r.get("updated_at") or "", reverse=True)


def register_project_source(project: dict, source_path: str, source_type: str | None = None, copy_into_project: bool | None = None, metadata: dict | None = None, project_path: str | None = None) -> dict:
    manifest = load_project_manifest(project.get("manifest_path") or project["project_root"])
    root = Path(manifest["project_root"]); src = Path(source_path).expanduser()
    copied = bool(manifest.get("settings", {}).get("copy_sources_into_project", False) if copy_into_project is None else copy_into_project)
    project_path_value = str(project_path) if project_path else None
    rec = {"source_id": str(uuid.uuid4()), "original_path": str(src), "source_type": source_type, "added_at": _now(), "copied_into_project": copied, "metadata": metadata or {}}
    if project_path_value:
        rec["project_path"] = project_path_value
    if copied and not project_path_value:
        dest = root / "data" / "original" / src.name
        if src.is_dir():
            if dest.exists(): dest = dest.with_name(f"{dest.name}_{uuid.uuid4().hex[:6]}")
            shutil.copytree(src, dest)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dest)
        rec["project_path"] = str(dest)
    registry_path = root / "settings" / "source_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.exists() else {"sources": []}
    existing = next((r for r in registry.setdefault("sources", []) if r.get("original_path") == rec.get("original_path") and r.get("project_path") == rec.get("project_path")), None)
    if existing:
        existing.update({k: v for k, v in rec.items() if k != "source_id"})
        rec = existing
    else:
        registry["sources"].append(rec)
    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    sources = manifest.setdefault("sources", [])
    existing_manifest = next((r for r in sources if r.get("original_path") == rec.get("original_path") and r.get("project_path") == rec.get("project_path")), None)
    if existing_manifest:
        existing_manifest.update(rec)
    else:
        sources.append(rec)
    save_project_manifest(manifest)
    return rec


def read_source_registry(project: dict) -> dict:
    manifest = load_project_manifest(project.get("manifest_path") or project["project_root"])
    path = Path(manifest["project_root"]) / "settings" / "source_registry.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"sources": []}


def get_project_subpaths(project: dict) -> dict[str, str]:
    manifest = load_project_manifest(project.get("manifest_path") or project["project_root"])
    return ensure_project_structure(manifest["project_root"])


def import_file_to_project(project: dict, file_path: str, copy: bool = True, metadata: dict | None = None) -> dict:
    if not copy:
        return register_project_source(project, file_path, copy_into_project=False, metadata=metadata)
    manifest = load_project_manifest(project.get("manifest_path") or project["project_root"])
    root = Path(manifest["project_root"])
    src = Path(file_path).expanduser()
    dest = root / "data" / "original" / src.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() != dest.resolve():
        if dest.exists(): dest = dest.with_name(f"{dest.stem}_{uuid.uuid4().hex[:6]}{dest.suffix}")
        shutil.copy2(src, dest)
    return register_project_source(project, str(src), copy_into_project=True, metadata=metadata, project_path=str(dest))


def import_folder_to_project(project: dict, folder_path: str, copy: bool = True, metadata: dict | None = None) -> dict:
    if not copy:
        return register_project_source(project, folder_path, copy_into_project=False, metadata=metadata)
    manifest = load_project_manifest(project.get("manifest_path") or project["project_root"])
    root = Path(manifest["project_root"])
    src = Path(folder_path).expanduser()
    dest = root / "data" / "original" / src.name
    if src.resolve() != dest.resolve():
        if dest.exists(): dest = dest.with_name(f"{dest.name}_{uuid.uuid4().hex[:6]}")
        shutil.copytree(src, dest)
    return register_project_source(project, str(src), copy_into_project=True, metadata=metadata, project_path=str(dest))


def create_project_run(project: dict, label: str | None = None) -> dict:
    manifest = load_project_manifest(project.get("manifest_path") or project["project_root"])
    root = Path(manifest["project_root"]); rid = f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
    run = root / "runs" / rid
    paths = {"run_id": rid, "run_dir": run, "json_dir": run/"json", "chunks_dir": run/"json"/"chunks", "prompt_dir": run/"json"/"prompt_chunks", "csv_dir": run/"csv", "viz_dir": run/"viz", "viz_units_dir": run/"viz"/"units", "reports_dir": run/"reports"}
    for p in paths.values():
        if isinstance(p, Path): p.mkdir(parents=True, exist_ok=True)
    meta = {"run_id": rid, "label": label, "project_id": manifest.get("project_id"), "created_at": _now()}
    meta_path = run / "meta.json"; meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    manifest["active_run_id"] = rid; save_project_manifest(manifest)
    return {k: str(v) for k, v in paths.items()} | {"meta_path": str(meta_path)}


def open_project_path(project_path: str | Path) -> None:
    path = str(project_path)
    if sys.platform.startswith("win"): subprocess.Popen(["explorer", path])
    elif sys.platform == "darwin": subprocess.Popen(["open", path])
    else: subprocess.Popen(["xdg-open", path])
