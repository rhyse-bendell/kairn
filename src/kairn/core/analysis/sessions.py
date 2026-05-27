from __future__ import annotations
from datetime import datetime


def _dt(ts: str):
    return datetime.fromisoformat(ts.replace('Z', '+00:00'))


def build_sessions(events: list[dict], idle_minutes: int = 10) -> list[dict]:
    if not events:
        return []
    ordered = sorted(events, key=lambda e: e.get('ts') or '')
    sessions = []
    current = {"start_ts": ordered[0].get("ts"), "end_ts": ordered[0].get("ts"), "events": [ordered[0]]}
    for e in ordered[1:]:
        gap = (_dt(e['ts']) - _dt(current['end_ts'])).total_seconds() / 60.0
        if gap > idle_minutes:
            sessions.append(current)
            current = {"start_ts": e.get("ts"), "end_ts": e.get("ts"), "events": [e]}
        else:
            current['events'].append(e)
            current['end_ts'] = e.get('ts')
    sessions.append(current)
    out = []
    for i, s in enumerate(sessions, 1):
        actors = sorted({(e.get('actor_label') or e.get('actor_id') or 'unknown') for e in s['events']})
        units = sorted({(e.get('unit') or 'unknown') for e in s['events']})
        actions = sorted({(e.get('action') or 'unknown') for e in s['events']})
        duration = (_dt(s['end_ts']) - _dt(s['start_ts'])).total_seconds() / 60.0
        out.append({"session_id": f"S{i:03d}", "start_ts": s['start_ts'], "end_ts": s['end_ts'], "duration_minutes": round(duration, 2), "event_count": len(s['events']), "actors": actors, "units": units, "actions": actions, "events": s['events']})
    return out
