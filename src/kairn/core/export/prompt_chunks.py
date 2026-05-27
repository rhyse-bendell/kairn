import gzip, json
from pathlib import Path
from ..storage.repositories import _conn

def export_prompt_chunks(db_path,out_dir,chunk_size=200,collection_id=None):
    out=Path(out_dir); out.mkdir(parents=True,exist_ok=True)
    conn=_conn(db_path)
    q='''select e.id event_id,e.ts,e.action,e.actor actor_id,coalesce(p.display_name,p.pid_label,e.actor,'unknown') actor_label,
         coalesce(e.mentioned_unit,a.rel_path) unit,e.artifact_id,a.kind artifact_kind,e.summary
         from events e left join artifacts a on a.id=e.artifact_id left join participants p on p.actor_id=e.actor where 1=1''';p=[]
    if collection_id:q+=' and e.collection_id=?';p.append(collection_id)
    q+=' order by e.ts'
    rows=[dict(r) for r in conn.execute(q,tuple(p))]
    paths=[]
    for i in range(0,len(rows),chunk_size):
        chunk=rows[i:i+chunk_size]
        jpath=out/f'prompt_chunk_{i//chunk_size+1:03d}.json'
        jpath.write_text(json.dumps({'events':chunk},indent=2),encoding='utf-8')
        gz=out/f'compact_chunk_{i//chunk_size+1:03d}.jsonl.gz'
        with gzip.open(gz,'wt',encoding='utf-8') as g:
            for e in chunk: g.write(json.dumps(e,separators=(',',':'))+'\n')
        paths.extend([str(jpath),str(gz)])
    return paths
