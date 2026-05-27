from dataclasses import dataclass, field
from typing import Any

@dataclass
class RawInputCandidate:
    root_path:str
    path:str
    rel_path:str
    name:str
    extension:str
    size_bytes:int
    modified_at:str
    mime_type:str|None=None
    guessed_kind:str='unknown'
    depth:int=0
    parent_rel_path:str|None=None

@dataclass
class IngestionContext:
    collection_id:str
    root_path:str
    root_label:str
    run_id:str
    db_path:str
    snapshot_dir:str
    actor_hint:str|None=None
    mode:str='scan'
    event_sink:Any=None

@dataclass
class IngestionResult:
    artifacts:list=field(default_factory=list)
    versions:list=field(default_factory=list)
    events:list=field(default_factory=list)
    deltas:list=field(default_factory=list)
    representations:list=field(default_factory=list)
    warnings:list=field(default_factory=list)

@dataclass
class Run:
    id:str
    collection_id:str
    root_path:str
    started_at:str
