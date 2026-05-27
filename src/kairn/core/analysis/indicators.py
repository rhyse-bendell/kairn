from __future__ import annotations
from ..storage.repositories import _conn

def participation_balance(db_path, collection_id=None):
    conn=_conn(db_path); q='select actor,count(*) c from events where actor is not null'; p=[]
    if collection_id: q+=' and collection_id=?'; p.append(collection_id)
    q+=' group by actor order by c desc'
    return [dict(r) for r in conn.execute(q,tuple(p))]

def artifact_activity_summary(db_path, collection_id=None):
    conn=_conn(db_path); q='select a.rel_path,count(e.id) event_count from artifacts a left join events e on e.artifact_id=a.id where 1=1'; p=[]
    if collection_id: q+=' and a.collection_id=?'; p.append(collection_id)
    q+=' group by a.id order by event_count desc'
    return [dict(r) for r in conn.execute(q,tuple(p))]

def coordination_indicators(db_path, collection_id=None):
    conn=_conn(db_path); q='select action,count(*) c from events where 1=1'; p=[]
    if collection_id: q+=' and collection_id=?'; p.append(collection_id)
    q+=' group by action order by c desc'
    return {"action_mix":[dict(r) for r in conn.execute(q,tuple(p))]}

def reentry_candidates(db_path, collection_id=None, since_ts=None):
    conn=_conn(db_path); q='select actor,max(ts) last_ts,count(*) c from events where actor is not null'; p=[]
    if collection_id: q+=' and collection_id=?'; p.append(collection_id)
    if since_ts: q+=' and ts>=?'; p.append(since_ts)
    q+=' group by actor order by last_ts desc'
    return [dict(r) for r in conn.execute(q,tuple(p))]

def unresolved_warning_summary(db_path, collection_id=None):
    conn=_conn(db_path)
    return [dict(r) for r in conn.execute('select rel_path,warning,count(*) c from ingestion_warnings group by rel_path,warning order by c desc')]
