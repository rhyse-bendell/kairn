from __future__ import annotations
from ..storage.repositories import _conn

def run_diagnostics(db_path):
    conn=_conn(db_path)
    out={}
    out['collaborations_count']=conn.execute('select count(*) c from collaborations').fetchone()['c']
    out['collections_count']=conn.execute('select count(*) c from collections').fetchone()['c']
    out['runs_count']=conn.execute('select count(*) c from runs').fetchone()['c']
    out['participants_count']=conn.execute('select count(*) c from participants').fetchone()['c']
    out['warnings_count']=conn.execute('select count(*) c from ingestion_warnings').fetchone()['c']
    out['artifacts_by_kind']={r['kind']:r['c'] for r in conn.execute('select coalesce(kind,\'unknown\') kind,count(*) c from artifacts group by kind')}
    out['events_by_action']={r['action']:r['c'] for r in conn.execute('select coalesce(action,\'unknown\') action,count(*) c from events group by action')}
    out['deltas_by_type']={r['delta_type']:r['c'] for r in conn.execute('select coalesce(delta_type,\'unknown\') delta_type,count(*) c from deltas group by delta_type')}
    out['events_missing_artifact']=conn.execute('select count(*) c from events e left join artifacts a on a.id=e.artifact_id where e.artifact_id is not null and a.id is null').fetchone()['c']
    out['actors_missing_participant']=conn.execute("select count(distinct e.actor) c from events e left join participants p on p.actor_id=e.actor where e.actor is not null and e.actor!='' and p.actor_id is null").fetchone()['c']
    out['artifacts_without_events']=conn.execute('select count(*) c from artifacts a left join events e on e.artifact_id=a.id where e.id is null').fetchone()['c']
    ts=conn.execute('select min(ts) mn,max(ts) mx from events').fetchone()
    out['earliest_event_ts']=ts['mn']; out['latest_event_ts']=ts['mx']
    return out
