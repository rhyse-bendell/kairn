from __future__ import annotations
import csv
import json
from collections import Counter
from ..storage.repositories import _conn
from .sessions import build_sessions


def build_timeline(db_path, idle_minutes=10, collection_id=None, collaboration_id=None, run_id=None):
    conn = _conn(db_path)
    q = '''
    select e.id event_id,e.ts,e.action,e.actor actor_id,
           coalesce(p.display_name,p.pid_label,e.actor,'unknown') actor_label,
           e.artifact_id,coalesce(e.mentioned_unit,a.rel_path) unit,
           a.kind artifact_kind,a.rel_path artifact_rel_path,e.summary
    from events e
    left join artifacts a on a.id=e.artifact_id
    left join participants p on p.actor_id=e.actor
    where 1=1
    '''
    ps = []
    if collection_id:
        q += ' and e.collection_id=?'; ps.append(collection_id)
    q += ' order by e.ts'
    events = [dict(r) for r in conn.execute(q, tuple(ps))]
    sessions = build_sessions(events, idle_minutes=idle_minutes)
    by_actor = dict(Counter((e.get('actor_label') or 'unknown') for e in events))
    by_artifact = dict(Counter((e.get('artifact_rel_path') or 'unknown') for e in events))
    by_action = dict(Counter((e.get('action') or 'unknown') for e in events))
    return {"events": events, "sessions": sessions, "by_actor": by_actor, "by_artifact": by_artifact, "by_action": by_action,
            "event_count": len(events), "first_ts": events[0]['ts'] if events else None, "last_ts": events[-1]['ts'] if events else None,
            "session_count": len(sessions)}


def export_timeline_json(db_path, out_path, **kwargs):
    data = build_timeline(db_path, **kwargs)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    return out_path


def export_sessions_csv(db_path, out_path, **kwargs):
    rows = build_timeline(db_path, **kwargs).get("sessions", [])
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["session_id", "start_ts", "end_ts", "duration_minutes", "event_count", "actors", "units", "actions"])
        w.writeheader()
        for r in rows:
            w.writerow({**r, "actors": "|".join(r.get("actors", [])), "units": "|".join(r.get("units", [])), "actions": "|".join(r.get("actions", []))})
    return out_path
