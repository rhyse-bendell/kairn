from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Any
@dataclass
class ReplayEvent:
    replay_event_id: str
    source: str
    source_table: str|None=None
    source_event_id: str|None=None
    timestamp_utc: str|None=None
    relative_time_s: float=0.0
    sequence_index: int=0
    team_id: str|None=None
    participant_id: str|None=None
    participant_name: str|None=None
    actor_label: str|None=None
    action: str|None=None
    object_type: str|None=None
    artifact_stream: str|None=None
    artifact_ref: str|None=None
    content_text: str|None=None
    summary: str|None=None
    callout_title: str|None=None
    callout_body: str|None=None
    x: float|None=None; y: float|None=None; width: float|None=None; height: float|None=None
    metadata: dict[str,Any]=field(default_factory=dict)
    def to_dict(self): return asdict(self)
