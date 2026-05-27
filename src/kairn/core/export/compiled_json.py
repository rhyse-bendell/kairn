from __future__ import annotations
import json
from collections import Counter, defaultdict
from ..analysis.timelines import build_timeline
from ..storage.repositories import _conn


def _events(conn, collection_id=None):
    q='''select e.*,a.rel_path,a.kind,p.pid_label,p.display_name from events e left join artifacts a on a.id=e.artifact_id left join participants p on p.actor_id=e.actor where 1=1''';p=[]
    if collection_id:q+=' and e.collection_id=?';p.append(collection_id)
    q+=' order by e.ts'
    return [dict(r) for r in conn.execute(q,tuple(p))]


def export_compiled(db_path,out_path,collection_id=None):
    conn=_conn(db_path)
    events=_events(conn,collection_id)
    seen=set(); dedup=[]
    for e in events:
        k=(e.get('ts'),e.get('actor'),e.get('artifact_id'),e.get('action'),e.get('summary'))
        if k in seen: continue
        seen.add(k); dedup.append(e)
    actors=Counter((e.get('display_name') or e.get('pid_label') or e.get('actor') or 'unknown') for e in dedup)
    units=defaultdict(list)
    for e in dedup:
        unit=e.get('mentioned_unit') or e.get('rel_path') or 'unknown'
        units[unit].append(e)
    timeline=build_timeline(db_path,collection_id=collection_id)
    payload={
        'meta':{'db_path':db_path,'collection_id':collection_id,'event_count':len(dedup)},
        'global_events':dedup,
        'units':{u:{'event_count':len(v),'events':v} for u,v in units.items()},
        'sessions':timeline['sessions'],
        'actors':dict(actors),
        'warnings':[dict(r) for r in conn.execute('select * from ingestion_warnings')]
    }
    with open(out_path,'w',encoding='utf-8') as f: json.dump(payload,f,indent=2)
    return out_path
