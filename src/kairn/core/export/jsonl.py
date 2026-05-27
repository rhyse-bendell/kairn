import json,gzip
from ..storage.repositories import fetchall
def export_jsonl(db_path,out_path,compact_gz=None):
    events=fetchall(db_path,'events')
    with open(out_path,'w') as f:
        for e in events: f.write(json.dumps(e)+'\n')
    if compact_gz:
        with gzip.open(compact_gz,'wt') as g:
            for e in events: g.write(json.dumps(e,separators=(',',':'))+'\n')
