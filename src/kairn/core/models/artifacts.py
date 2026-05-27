from dataclasses import dataclass
@dataclass
class Artifact:
    id:str
    collection_id:str
    rel_path:str
    path:str
    name:str
    extension:str
    kind:str
    size_bytes:int
    modified_at:str
    content_hash:str|None=None

@dataclass
class ArtifactRepresentation:
    artifact_id:str
    rep_type:str
    payload:str
