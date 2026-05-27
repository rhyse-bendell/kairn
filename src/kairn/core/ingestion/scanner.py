from pathlib import Path
from datetime import datetime, timezone
from .classify import classify
from ..models.runs import RawInputCandidate

def scan(root_path:str):
    root=Path(root_path)
    for p in root.rglob('*'):
        if p.is_file():
            rel=p.relative_to(root)
            st=p.stat()
            yield RawInputCandidate(root_path=str(root), path=str(p), rel_path=str(rel), name=p.name, extension=p.suffix.lower(), size_bytes=st.st_size, modified_at=datetime.fromtimestamp(st.st_mtime,timezone.utc).isoformat(), guessed_kind=classify(p), depth=len(rel.parts)-1, parent_rel_path=str(rel.parent) if rel.parent!=Path('.') else None)
