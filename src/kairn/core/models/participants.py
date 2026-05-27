from dataclasses import dataclass
@dataclass
class Participant:
    actor_id:str
    pid_label:str
    display_name:str|None=None
    first_seen_ts:str|None=None
