from __future__ import annotations
import json, sqlite3
from datetime import datetime
from .models import ReplayEvent
from .summaries import events_by_actor,events_by_source,events_by_action,events_by_team,active_windows

def _exists(c,t): return c.execute("select 1 from sqlite_master where type='table' and name=?",(t,)).fetchone() is not None
def _cols(c,t): return {r[1] for r in c.execute(f'pragma table_info({t})')}
def _dt(s):
 try: return datetime.fromisoformat(str(s).replace('Z','+00:00')) if s else None
 except Exception: return None
def _meta(r):
 d=dict(r); prov=d.get('provenance_json')
 if prov:
  try: d['provenance']=json.loads(prov)
  except Exception: pass
 return d
def _callout(src, actor, action, obj, content, art, meta):
 actor=actor or 'Unknown actor'; action=action or 'performed action'; obj=obj or 'object'
 if src=='tldraw':
  title=f'{actor} {action} {obj}'.strip(); parts=[]
  if content: parts.append(f'Text: {content}')
  if meta.get('room_id') or meta.get('team_id'): parts.append(f"Room: {meta.get('room_id') or meta.get('team_id')}")
  if meta.get('source'): parts.append(f"Source: {meta.get('source')}")
  return title,' | '.join(parts) or (art or '')
 if src=='drive': return f'{actor} {action} {art or obj}'.strip(), f"File ID: {meta.get('file_id') or ''} | Parent folder: {meta.get('parent_folder') or ''}".strip()
 if src=='document': return f'{actor} {action} document text'.strip(), content or art or ''
 return f'{actor} {action}'.strip(), content or art or meta.get('summary') or ''
def _ev(row, source, table, idx):
 r=dict(row); actor=r.get('participant_name') or r.get('user') or r.get('actor') or r.get('actor_label')
 ts=r.get('timestamp_utc') or r.get('ts'); action=r.get('action'); obj=r.get('object_type') or r.get('entity_type') or r.get('mime_type')
 content=r.get('content_text') or r.get('shape_text') or r.get('text_snippet') or r.get('file_name')
 art=r.get('artifact_ref') or r.get('entity_id') or r.get('file_name') or r.get('source_path')
 meta=_meta(row); title,body=_callout(source,actor,action,obj,content,art,meta)
 return ReplayEvent(f'{table}:{r.get("id")}',source,table,str(r.get('id')),ts,0.0,idx,r.get('team_id') or r.get('inferred_team_id'),r.get('participant_id') or r.get('inferred_participant_id'),r.get('participant_name') or r.get('user') or r.get('actor'),actor,action,obj,r.get('artifact_stream'),art,content,r.get('summary') or f'{source} {action or ""} {art or ""}'.strip(),title,body,r.get('x'),r.get('y'),r.get('width'),r.get('height'),meta)
def _select(c,t,collection_id,run_id,team_id,participant_id):
 cols=_cols(c,t); wh=[]; args=[]
 for col,val in [('collection_id',collection_id),('run_id',run_id)]:
  if val and col in cols: wh.append(f'{col}=?'); args.append(val)
 if team_id:
  col='team_id' if 'team_id' in cols else 'inferred_team_id' if 'inferred_team_id' in cols else None
  if col: wh.append(f'{col}=?'); args.append(team_id)
 if participant_id:
  col='participant_id' if 'participant_id' in cols else 'inferred_participant_id' if 'inferred_participant_id' in cols else None
  if col: wh.append(f'{col}=?'); args.append(participant_id)
 order_col='timestamp_utc' if 'timestamp_utc' in cols else 'ts' if 'ts' in cols else 'id'
 sql=f'select * from {t}'+(' where '+' and '.join(wh) if wh else '')+f' order by {order_col},id'
 return c.execute(sql,args).fetchall()
def load_replay_events(db_path, collection_id=None, run_id=None, sources=None, team_id=None, participant_id=None):
 c=sqlite3.connect(str(db_path)); c.row_factory=sqlite3.Row; events=[]; srcset=set(sources or []); used_unified=False
 if _exists(c,'unified_process_events'):
  rows=_select(c,'unified_process_events',collection_id,run_id,team_id,participant_id)
  if rows:
   used_unified=True; events=[_ev(r,r['event_source'] or 'unified','unified_process_events',i) for i,r in enumerate(rows)]
 if not events:
  for src,t in [('tldraw','parsed_tldraw_events'),('drive','drive_activity_events'),('document','document_edit_events'),('generic','events')]:
   if _exists(c,t) and (not srcset or src in srcset): events += [_ev(r,src,t,len(events)) for r in _select(c,t,collection_id,run_id,team_id,participant_id)]
 c.close(); events=[e for e in events if used_unified and 'unified' in srcset or not srcset or e.source in srcset]
 events.sort(key=lambda e:(e.timestamp_utc or '', e.source_event_id or '')); first=next((_dt(e.timestamp_utc) for e in events if _dt(e.timestamp_utc)),None)
 for i,e in enumerate(events):
  e.sequence_index=i; d=_dt(e.timestamp_utc); e.relative_time_s=(d-first).total_seconds() if d and first else 0.0
 return events
def get_replay_summary(events):
 first=events[0].timestamp_utc if events else None; last=events[-1].timestamp_utc if events else None
 dur=0.0
 if first and last and _dt(first) and _dt(last): dur=(_dt(last)-_dt(first)).total_seconds()/60
 return {'event_count':len(events),'first_ts':first,'last_ts':last,'duration_minutes':dur,'counts_by_source':events_by_source(events),'counts_by_action':events_by_action(events),'counts_by_actor':events_by_actor(events),'counts_by_team':events_by_team(events),'counts_by_object_type':dict(__import__('collections').Counter((e.object_type or '(unknown)') for e in events)),'user_vs_remote_count':dict(__import__('collections').Counter((e.metadata.get('source') or 'unknown') for e in events if e.source=='tldraw')),'active_windows':active_windows(events)}
