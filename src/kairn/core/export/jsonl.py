import gzip, json
from ..storage.repositories import _conn

def export_jsonl(db_path,out_path,compact_gz=None,collection_id=None):
    conn=_conn(db_path)
    q='select * from events'; p=()
    if collection_id: q+=' where collection_id=?'; p=(collection_id,)
    events=[dict(r) for r in conn.execute(q,p)]
    with open(out_path,'w',encoding='utf-8') as f:
        for e in events: f.write(json.dumps(e)+'\n')
    if compact_gz:
        with gzip.open(compact_gz,'wt',encoding='utf-8') as g:
            for e in events: g.write(json.dumps(e,separators=(',',':'))+'\n')
    return out_path
