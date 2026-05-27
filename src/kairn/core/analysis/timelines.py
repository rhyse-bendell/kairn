from __future__ import annotations
import json
from ..storage.repositories import _conn
from .sessions import build_sessions


def build_timeline(db_path, idle_minutes=10, collection_id=None, collaboration_id=None, run_id=None):
    conn = _conn(db_path)
    q = '''
    select e.id event_id,e.ts,e.action,e.actor actor_id,
           coalesce(p.display_name,p.pid_label,e.actor,'unknown') actor_label,
           e.artifact_id,coalesce(e.mentioned_unit,a.rel_path) unit,
           a.kind artifact_kind,e.summary,r.id run_id,a.path artifact_path
    from events e
    left join artifacts a on a.id=e.artifact_id
    left join participants p on p.actor_id=e.actor
    left join runs r on r.collection_id=e.collection_id
    where 1=1
    '''
    ps=[]
    if collection_id: q+=' and e.collection_id=?'; ps.append(collection_id)
    q+=' order by e.ts'
    events=[dict(r) for r in conn.execute(q,tuple(ps))]
    sessions=build_sessions(events,idle_minutes=idle_minutes)
    by_actor={}
    by_artifact={}
    for e in events:
        by_actor.setdefault(e['actor_label'],0); by_actor[e['actor_label']]+=1
        by_artifact.setdefault(e.get('unit') or 'unknown',0); by_artifact[e.get('unit') or 'unknown']+=1
    return {"events":events,"sessions":sessions,"by_actor":by_actor,"by_artifact":by_artifact}


def export_timeline_json(db_path,out_path,**kwargs):
    data=build_timeline(db_path,**kwargs)
    with open(out_path,'w',encoding='utf-8') as f: json.dump(data,f,indent=2)
    return out_path
