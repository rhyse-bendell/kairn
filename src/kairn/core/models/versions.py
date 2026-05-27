from dataclasses import dataclass
@dataclass
class Version:
    id:str
    artifact_id:str
    content_hash:str
    created_at:str
    snapshot_path:str|None=None
