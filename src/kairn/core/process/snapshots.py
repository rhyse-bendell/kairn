from __future__ import annotations
import sqlite3,json
from datetime import datetime,timedelta

def ensure_table(c):
 c.executescript('''create table if not exists board_snapshots(id integer primary key autoincrement, collection_id text, run_id text, team_id text, room_id text, snapshot_ts text, event_index integer, object_count integer, node_count integer, arrow_count integer, binding_count integer, payload_json text);''')
def _filters(team_id,room_id,collection_id,run_id,up_to_ts):
 wh=[]; args=[]
 for col,val in [('team_id',team_id),('room_id',room_id),('collection_id',collection_id),('run_id',run_id)]:
  if val is not None: wh.append(f'{col}=?'); args.append(val)
 if up_to_ts: wh.append('timestamp_utc<=?'); args.append(up_to_ts)
 return (' where '+ ' and '.join(wh) if wh else ''),args
def reconstruct_board_state(db_path, team_id=None, room_id=None, collection_id=None, run_id=None, up_to_ts=None):
 c=sqlite3.connect(str(db_path)); c.row_factory=sqlite3.Row; ensure_table(c); wh,args=_filters(team_id,room_id,collection_id,run_id,up_to_ts); state={}
 for r in c.execute('select * from parsed_tldraw_events '+wh+' order by timestamp_utc,id',args):
  if r['action']=='delete': state.pop(r['entity_id'],None)
  else: state[r['entity_id']]={k:r[k] for k in r.keys() if k in ('entity_id','entity_type','object_type','shape_text','x','y','width','height','room_id','team_id')}
 c.close(); return state
def create_board_snapshots(db_path, collection_id=None, run_id=None, interval_minutes=5):
 c=sqlite3.connect(str(db_path)); c.row_factory=sqlite3.Row; ensure_table(c); c.execute('delete from board_snapshots where ifnull(collection_id,\'\')=ifnull(?,\'\') and ifnull(run_id,\'\')=ifnull(?,\'\')',(collection_id,run_id))
 events=c.execute('select * from parsed_tldraw_events where ifnull(collection_id,\'\')=ifnull(?,\'\') order by team_id,room_id,timestamp_utc,id',(collection_id,)).fetchall(); state={}; count=0
 for i,r in enumerate(events,1):
  key=(r['team_id'],r['room_id']); state.setdefault(key,{})
  if r['action']=='delete': state[key].pop(r['entity_id'],None)
  else: state[key][r['entity_id']]=dict(r)
  objs=state[key]; arrows=sum(1 for o in objs.values() if 'arrow' in str(o.get('object_type') or o.get('entity_type')).lower()); binds=sum(1 for o in objs.values() if 'binding' in str(o.get('entity_type')).lower())
  c.execute('insert into board_snapshots(collection_id,run_id,team_id,room_id,snapshot_ts,event_index,object_count,node_count,arrow_count,binding_count,payload_json) values(?,?,?,?,?,?,?,?,?,?,?)',(collection_id,run_id,r['team_id'],r['room_id'],r['timestamp_utc'],i,len(objs),len(objs)-arrows-binds,arrows,binds,json.dumps({'objects':list(objs.keys())}))); count+=1
 c.commit(); c.close(); return {'inserted':count,'count':count}
