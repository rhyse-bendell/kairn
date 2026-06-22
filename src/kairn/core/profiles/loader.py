from __future__ import annotations
import json
from pathlib import Path

DEFAULT_PROFILE_NAME = "problem_framing_workshop"
_BUILTIN_DIR = Path(__file__).parent / "builtin"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not data.get("name"):
        raise ValueError(f"Invalid profile JSON: {path}")
    return data


def list_builtin_profiles() -> list[dict]:
    profiles = []
    for path in sorted(_BUILTIN_DIR.glob("*.json")):
        p = _load_json(path)
        profiles.append({"name": p["name"], "description": p.get("description", ""), "path": str(path)})
    return profiles


def load_profile(name_or_path: str | None = None) -> dict:
    target = name_or_path or DEFAULT_PROFILE_NAME
    path = Path(target)
    if path.exists():
        return _load_json(path)
    builtin = _BUILTIN_DIR / f"{target}.json"
    if builtin.exists():
        return _load_json(builtin)
    raise ValueError(f"Unknown profile {target!r}; use a built-in name or JSON path")


def get_default_profile() -> dict:
    return load_profile(DEFAULT_PROFILE_NAME)
