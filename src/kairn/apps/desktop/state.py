from dataclasses import dataclass

@dataclass
class AppState:
    db_path:str='./kairn_workspace/kairn.db'
    active_collaboration_id:str|None=None
    active_collection_id:str|None=None
    active_root_path:str|None=None
    last_run_id:str|None=None
    last_output_dir:str|None=None
