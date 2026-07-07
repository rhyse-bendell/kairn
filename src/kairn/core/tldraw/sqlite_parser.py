from __future__ import annotations
import sqlite3, json
from pathlib import Path
from .payloads import load_payload, timestamp_ms_to_utc, extract_shape_text, extract_shape_geometry, extract_arrow_or_binding, room_to_team_id

def ensure_tables(conn):
    conn.executescript('''
    create table if not exists raw_tldraw_events(id integer primary key autoincrement, source_db_path text, source_row_id integer, collection_id text, run_id text, entity text, action text, entity_id text, entity_type text, payload_json text, performed_by_id text, performed_by_name text, source text, room_id text, ts integer, timestamp_utc text);
    create unique index if not exists idx_raw_tldraw_idem on raw_tldraw_events(source_db_path, source_row_id, ifnull(collection_id,''));
    create table if not exists parsed_tldraw_events(id integer primary key autoincrement, raw_event_id integer, collection_id text, run_id text, team_id text, room_id text, participant_id text, participant_name text, source text, event_sequence_index integer, timestamp_utc text, relative_time_from_team_start_s real, entity text, action text, entity_id text, entity_type text, object_type text, shape_text text, x real, y real, width real, height real, rotation real, color text, fill text, parent_id text, group_id text, arrow_from_shape_id text, arrow_to_shape_id text, arrow_terminal text, binding_from_id text, binding_to_id text, is_user_originated integer, raw_payload_excerpt text);
    create unique index if not exists idx_parsed_tldraw_raw on parsed_tldraw_events(raw_event_id);
    ''')

def inspect_tldraw_db(db_path) -> dict:
    conn=sqlite3.connect(str(db_path)); conn.row_factory=sqlite3.Row
    tables=[r[0] for r in conn.execute("select name from sqlite_master where type='table'")]
    schema=[dict(r) for r in conn.execute('pragma table_info(audit_logs)')] if 'audit_logs' in tables else []
    def counts(col):
        return {str(r[0]):r[1] for r in conn.execute(f'select {col}, count(*) from audit_logs group by {col}')}
    out={'tables':tables,'audit_logs_schema':schema,'row_count':0,'counts_by_entity':{},'counts_by_action':{},'counts_by_entity_type':{},'counts_by_source':{},'counts_by_room_id':{},'timestamp_min':None,'timestamp_max':None,'detected_rooms':[],'detected_actors':[]}
    if 'audit_logs' in tables:
        out['row_count']=conn.execute('select count(*) from audit_logs').fetchone()[0]
        for c,k in [('entity','counts_by_entity'),('action','counts_by_action'),('entity_type','counts_by_entity_type'),('source','counts_by_source'),('room_id','counts_by_room_id')]: out[k]=counts(c)
        mn,mx=conn.execute('select min(ts), max(ts) from audit_logs').fetchone(); out['timestamp_min']=timestamp_ms_to_utc(mn); out['timestamp_max']=timestamp_ms_to_utc(mx)
        out['detected_rooms']=[r[0] for r in conn.execute('select distinct room_id from audit_logs where room_id is not null')]
        out['detected_actors']=[r[0] for r in conn.execute('select distinct performed_by_name from audit_logs where performed_by_name is not null')]
    conn.close(); return out

def parse_tldraw_audit_logs(db_path, out_db_path=None, collection_id=None, run_id=None, include_remote=True) -> dict:
    src=sqlite3.connect(str(db_path)); src.row_factory=sqlite3.Row
    out=sqlite3.connect(str(out_db_path or db_path)); out.row_factory=sqlite3.Row; ensure_tables(out)
    before=out.execute('select count(*) from raw_tldraw_events').fetchone()[0]
    rows=src.execute('select * from audit_logs order by ts, id').fetchall(); source_path=str(Path(db_path))
    for r in rows:
        if not include_remote and r['source']!='user': continue
        payload_json=r['payload'] if isinstance(r['payload'],str) else json.dumps(r['payload'])
        out.execute('''insert or ignore into raw_tldraw_events(source_db_path,source_row_id,collection_id,run_id,entity,action,entity_id,entity_type,payload_json,performed_by_id,performed_by_name,source,room_id,ts,timestamp_utc) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(source_path,r['id'],collection_id,run_id,r['entity'],r['action'],r['entity_id'],r['entity_type'],payload_json,r['performed_by_id'],r['performed_by_name'],r['source'],r['room_id'],r['ts'],timestamp_ms_to_utc(r['ts'])))
        raw_id=out.execute('select id from raw_tldraw_events where source_db_path=? and source_row_id=? and ifnull(collection_id,\'\')=ifnull(?,\'\')',(source_path,r['id'],collection_id)).fetchone()[0]
        p=load_payload(payload_json); geom=extract_shape_geometry(p); ab=extract_arrow_or_binding(p); obj=p.get('type') or r['entity_type']
        vals=[raw_id,collection_id,run_id,room_to_team_id(r['room_id']),r['room_id'],r['performed_by_id'],r['performed_by_name'],r['source'],None,timestamp_ms_to_utc(r['ts']),None,r['entity'],r['action'],r['entity_id'],r['entity_type'],obj,extract_shape_text(p),geom['x'],geom['y'],geom['width'],geom['height'],geom['rotation'],geom['color'],geom['fill'],geom['parent_id'],geom['group_id'],ab['arrow_from_shape_id'],ab['arrow_to_shape_id'],ab['arrow_terminal'],ab['binding_from_id'],ab['binding_to_id'],1 if r['source']=='user' else 0,payload_json[:500]]
        out.execute('''insert or ignore into parsed_tldraw_events(raw_event_id,collection_id,run_id,team_id,room_id,participant_id,participant_name,source,event_sequence_index,timestamp_utc,relative_time_from_team_start_s,entity,action,entity_id,entity_type,object_type,shape_text,x,y,width,height,rotation,color,fill,parent_id,group_id,arrow_from_shape_id,arrow_to_shape_id,arrow_terminal,binding_from_id,binding_to_id,is_user_originated,raw_payload_excerpt) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', vals)
    # sequence/relative
    parsed=out.execute('select id,team_id,timestamp_utc from parsed_tldraw_events where ifnull(collection_id,\'\')=ifnull(?,\'\') order by team_id,timestamp_utc,id',(collection_id,)).fetchall(); starts={}; idx={}
    from datetime import datetime
    for r in parsed:
        team=r['team_id'] or ''; idx[team]=idx.get(team,0)+1; starts.setdefault(team,r['timestamp_utc'])
        rel=(datetime.fromisoformat(r['timestamp_utc'].replace('Z','+00:00'))-datetime.fromisoformat(starts[team].replace('Z','+00:00'))).total_seconds() if r['timestamp_utc'] else None
        out.execute('update parsed_tldraw_events set event_sequence_index=?, relative_time_from_team_start_s=? where id=?',(idx[team],rel,r['id']))
    out.commit(); after=out.execute('select count(*) from raw_tldraw_events').fetchone()[0]; src.close(); out.close()
    return {'source_rows':len(rows),'inserted_raw':after-before,'raw_count':after}
