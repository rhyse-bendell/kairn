import csv
from ..storage.repositories import fetchall
def export_timeline_csv(db_path,out_csv):
    events=sorted(fetchall(db_path,'events'), key=lambda x:x['ts'])
    with open(out_csv,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['ts','action','actor','artifact_id','mentioned_unit','summary']); w.writeheader(); [w.writerow({k:e.get(k) for k in w.fieldnames}) for e in events]
