from dataclasses import dataclass
@dataclass
class Event:
    id:str
    collection_id:str
    artifact_id:str|None=None
    action:str=''
    actor:str|None=None
    ts:str=''
    mentioned_unit:str|None=None
    summary:str|None=None
    raw_row:str|None=None
