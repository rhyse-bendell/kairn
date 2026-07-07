import csv,json,sqlite3
from pathlib import Path
from kairn.core.sources import detect_compatible_source
from kairn.core.replay import load_replay_events,get_replay_summary
from kairn.core.replay.summaries import events_by_actor,event_density,actor_source_matrix
from kairn.core.replay.export import export_replay_events_csv,export_replay_events_json,export_replay_summary_json

def test_source_detection(tmp_path):
 db=tmp_path/'TLDraw Logs.db'; c=sqlite3.connect(db); c.execute('create table audit_logs(id,entity,action,entity_id,entity_type,payload,performed_by_id,performed_by_name,source,room_id,ts)'); c.close()
 assert detect_compatible_source(str(db))['detected_handlers'][0]['handler']=='tldraw_sqlite'
 csvp=tmp_path/'dailyLog.csv'; csvp.write_text('time,user,action,fileID,file name,mimeType,parent folder\n2024,a,edit,f,n,t,p\n')
 assert detect_compatible_source(str(csvp))['kind']=='csv'
 txt=tmp_path/'changelog.txt'; txt.write_text('[EDIT] Alice changed text')
 assert detect_compatible_source(str(txt))['compatible']
 unk=tmp_path/'x.bin'; unk.write_bytes(b'abc')
 assert not detect_compatible_source(str(unk))['compatible']
 assert detect_compatible_source(str(tmp_path))['compatible']

def test_replay_unified_summary_exports(tmp_path):
 db=tmp_path/'k.db'; c=sqlite3.connect(db)
 c.execute('create table unified_process_events(id integer primary key, collection_id text, run_id text, event_source text, source_table text, source_event_id text, team_id text, participant_id text, participant_name text, artifact_id text, artifact_stream text, timestamp_utc text, relative_time_from_team_start_s real, event_sequence_index integer, phase_code text, action text, object_type text, content_text text, artifact_ref text, summary text, provenance_json text)')
 c.execute('insert into unified_process_events values(1,"c1",null,"drive","drive_activity_events","7","Team 1","p1","Alice",null,"drive","2024-01-01T00:00:00Z",0,0,null,"edited","document","Text","Doc","sum",?)',(json.dumps({'file_id':'f1','parent_folder':'Team 1'}),))
 c.execute('insert into unified_process_events values(2,"c1",null,"document","document_edit_events","8","Team 1","p2","Bob",null,"document","2024-01-01T00:05:00Z",300,1,null,"edited","document_edit","Snippet","Doc","sum2",?)',('{}',)); c.commit(); c.close()
 ev=load_replay_events(str(db),'c1')
 assert [e.actor_label for e in ev]==['Alice','Bob']; assert ev[1].relative_time_s==300; assert ev[0].callout_title
 summ=get_replay_summary(ev); assert summ['counts_by_actor']['Alice']==1; assert events_by_actor(ev)['Bob']==1; assert event_density(ev,5)[1]['count']==1; assert actor_source_matrix(ev)['Alice']['drive']==1
 assert Path(export_replay_events_csv(ev,tmp_path/'out'/'r.csv')).exists()
 assert Path(export_replay_events_json(ev,tmp_path/'out'/'r.json')).exists()
 assert Path(export_replay_summary_json(summ,tmp_path/'out'/'s.json')).exists()

def test_replay_fallback_tldraw(tmp_path):
 db=tmp_path/'k.db'; c=sqlite3.connect(db)
 c.execute('create table parsed_tldraw_events(id integer primary key, collection_id text, run_id text, team_id text, room_id text, participant_id text, participant_name text, source text, event_sequence_index integer, timestamp_utc text, relative_time_from_team_start_s real, entity text, action text, entity_id text, entity_type text, object_type text, shape_text text, x real, y real, width real, height real)')
 c.execute('insert into parsed_tldraw_events values(1,"c1",null,"Team 2","room","p1","Alice","user",0,"2024-01-01T00:00:00Z",0,"shape","created","s1","text","text shape","Urban heat",1,2,3,4)'); c.commit(); c.close()
 ev=load_replay_events(str(db),'c1')
 assert len(ev)==1 and ev[0].source=='tldraw' and 'Urban heat' in ev[0].callout_body

def test_gui_imports():
 import pytest
 pytest.importorskip("PySide6")
 from kairn.apps.desktop.tabs.replay import ReplayTab
 from kairn.apps.desktop import main
 assert ReplayTab and main
