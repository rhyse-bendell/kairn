from __future__ import annotations
from collections import Counter,defaultdict
from datetime import datetime, timezone, timedelta
def _key(v): return v if v not in (None,'') else '(unknown)'
def events_by_actor(events): return dict(Counter(_key(e.actor_label or e.participant_name) for e in events))
def events_by_source(events): return dict(Counter(_key(e.source) for e in events))
def events_by_action(events): return dict(Counter(_key(e.action) for e in events))
def events_by_team(events): return dict(Counter(_key(e.team_id) for e in events))
def _dt(s):
 if not s: return None
 try: return datetime.fromisoformat(str(s).replace('Z','+00:00'))
 except Exception: return None
def event_density(events, bin_minutes=5):
 if not events: return []
 first=min((_dt(e.timestamp_utc) for e in events if _dt(e.timestamp_utc)), default=None)
 if not first: return []
 bins=Counter()
 for e in events:
  d=_dt(e.timestamp_utc)
  if d: bins[int((d-first).total_seconds()//(bin_minutes*60))]+=1
 return [{'bin_index':i,'start_offset_minutes':i*bin_minutes,'count':bins[i]} for i in range(max(bins.keys(), default=-1)+1)]
def actor_source_matrix(events):
 m=defaultdict(Counter)
 for e in events: m[_key(e.actor_label or e.participant_name)][_key(e.source)]+=1
 return {k:dict(v) for k,v in m.items()}
def actor_action_matrix(events):
 m=defaultdict(Counter)
 for e in events: m[_key(e.actor_label or e.participant_name)][_key(e.action)]+=1
 return {k:dict(v) for k,v in m.items()}
def object_type_over_time(events, bin_minutes=5):
 first=min((_dt(e.timestamp_utc) for e in events if _dt(e.timestamp_utc)), default=None); m=defaultdict(Counter)
 if not first: return {}
 for e in events:
  d=_dt(e.timestamp_utc)
  if d: m[int((d-first).total_seconds()//(bin_minutes*60))][_key(e.object_type)]+=1
 return {str(k):dict(v) for k,v in m.items()}
def active_windows(events, idle_gap_minutes=10):
 ds=sorted(d for d in (_dt(e.timestamp_utc) for e in events) if d); wins=[]
 if not ds: return wins
 start=prev=ds[0]
 for d in ds[1:]:
  if (d-prev)>timedelta(minutes=idle_gap_minutes): wins.append({'start':start.isoformat(),'end':prev.isoformat(),'event_count':None}); start=d
  prev=d
 wins.append({'start':start.isoformat(),'end':prev.isoformat(),'event_count':None}); return wins
