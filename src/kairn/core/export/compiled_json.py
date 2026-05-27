import json
from ..storage.repositories import fetchall
def export_compiled(db_path,out_path):
    payload={'meta':{'db_path':db_path},'global_events':fetchall(db_path,'events'),'units':fetchall(db_path,'artifacts')}
    open(out_path,'w').write(json.dumps(payload,indent=2))
