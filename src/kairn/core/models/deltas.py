from dataclasses import dataclass
@dataclass
class Delta:
    id:str
    event_id:str
    delta_type:str
    payload:str
