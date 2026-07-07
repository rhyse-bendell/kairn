from __future__ import annotations
import sqlite3,json
from datetime import datetime

def ensure_table(c):
 c.executescript('''create table if not exists unified_process_events(id integer primary key autoincrement, collection_id text, run_id text, event_source text, source_table text, source_event_id text, team_id text, participant_id text, participant_name text, artifact_id text, artifact_stream text, timestamp_utc text, timestamp_end_utc text, relative_time_from_team_start_s real, event_sequence_index integer, phase_code text, action text, object_type text, content_text text, artifact_ref text, summary text, provenance_json text); create unique index if not exists idx_unified_idem on unified_process_events(source_table,source_event_id,ifnull(collection_id,''));''')
def _exists(c,t): return c.execute("select 1 from sqlite_master where type='table' and name=?",(t,)).fetchone()
def build_unified_process_events(db_path, collection_id=None, run_id=None, include_sources=('tldraw','drive','document')):
 c=sqlite3.connect(str(db_path)); c.row_factory=sqlite3.Row; ensure_table(c); before=c.execute('select count(*) from unified_process_events').fetchone()[0]; rows=[]
 if 'tldraw' in include_sources and _exists(c,'parsed_tldraw_events'):
  for r in c.execute('select * from parsed_tldraw_events where ifnull(collection_id,\'\')=ifnull(?,\'\')',(collection_id,)): rows.append(('tldraw','parsed_tldraw_events',r['id'],r['team_id'],r['participant_id'],r['participant_name'],None,'tldraw',r['timestamp_utc'],r['action'],r['object_type'],r['shape_text'],r['entity_id']))
 if 'drive' in include_sources and _exists(c,'drive_activity_events'):
  for r in c.execute('select * from drive_activity_events where ifnull(collection_id,\'\')=ifnull(?,\'\')',(collection_id,)): rows.append(('drive','drive_activity_events',r['id'],r['inferred_team_id'],r['inferred_participant_id'],r['user'],r['file_id'],'drive',r['timestamp_utc'],r['action'],r['mime_type'],r['file_name'],r['file_name']))
 if 'document' in include_sources and _exists(c,'document_edit_events'):
  for r in c.execute('select * from document_edit_events where ifnull(collection_id,\'\')=ifnull(?,\'\')',(collection_id,)): rows.append(('document','document_edit_events',r['id'],r['inferred_team_id'],r['inferred_participant_id'],r['actor'],None,'document',r['timestamp_utc'],r['action'],'document_edit',r['text_snippet'],r['source_path']))
 rows.sort(key=lambda x:((x[3] or ''),(x[8] or ''),str(x[2]))); starts={}; idx={}
 for e in rows:
  team=e[3] or 'unknown'; idx[team]=idx.get(team,0)+1; starts.setdefault(team,e[8]); rel=None
  if e[8] and starts[team]:
   try: rel=(datetime.fromisoformat(e[8].replace('Z','+00:00'))-datetime.fromisoformat(starts[team].replace('Z','+00:00'))).total_seconds()
   except Exception: pass
  prov=json.dumps({'source_table':e[1],'source_event_id':e[2]})
  c.execute('''insert or ignore into unified_process_events(collection_id,run_id,event_source,source_table,source_event_id,team_id,participant_id,participant_name,artifact_id,artifact_stream,timestamp_utc,relative_time_from_team_start_s,event_sequence_index,phase_code,action,object_type,content_text,artifact_ref,summary,provenance_json) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(collection_id,run_id,e[0],e[1],str(e[2]),e[3],e[4],e[5],e[6],e[7],e[8],rel,idx[team],'unknown',e[9],e[10],e[11],e[12],f'{e[0]} {e[9]} {e[12] or ""}',prov))
 c.commit(); after=c.execute('select count(*) from unified_process_events').fetchone()[0]; c.close(); return {'inserted':after-before,'count':after}
