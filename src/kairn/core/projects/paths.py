from __future__ import annotations

import os
import re
from pathlib import Path

_UNSAFE = '<>:"/\\|?*'


def get_default_kairn_home() -> Path:
    env = os.environ.get("KAIRN_HOME")
    if env:
        return Path(env).expanduser()
    if os.name == "nt":
        profile = os.environ.get("USERPROFILE")
        if profile:
            return Path(profile) / "Documents" / "Kairn"
    docs = Path.home() / "Documents"
    if docs.exists():
        return docs / "Kairn"
    return Path.home() / ".kairn"


def safe_project_slug(name: str) -> str:
    value = re.sub(r"\s+", "_", (name or "").strip())
    value = "".join(ch for ch in value if ch not in _UNSAFE and ord(ch) >= 32)
    value = re.sub(r"_+", "_", value).strip(" ._")
    return value or "Kairn_Project"


def project_root_for_name(name: str, kairn_home: str | Path | None = None) -> Path:
    home = Path(kairn_home).expanduser() if kairn_home else get_default_kairn_home()
    return home / safe_project_slug(name)
