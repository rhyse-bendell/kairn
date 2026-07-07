import csv,json,sqlite3
from pathlib import Path
from kairn.core.tldraw.sqlite_parser import inspect_tldraw_db, parse_tldraw_audit_logs
from kairn.core.drive.activity_parser import parse_drive_activity_csv
from kairn.core.documents.changelog_parser import parse_document_changelog
from kairn.core.process.unified_events import build_unified_process_events
from kairn.core.process.snapshots import create_board_snapshots, reconstruct_board_state
from kairn.core.catalog.detection import classify_artifact_for_catalog


def make_tldraw(path):
    c=sqlite3.connect(path)
    c.execute('create table audit_logs(id integer, entity text, action text, entity_id text, entity_type text, payload text, performed_by_id text, performed_by_name text, source text, room_id text, ts integer)')
    payload={'type':'geo','x':10,'y':20,'props':{'w':100,'h':50,'color':'red','fill':'solid','richText':{'content':[{'content':[{'text':'Hello'}]}]}}}
    rows=[(1,'shape','create','s1','shape',json.dumps(payload),'p1','Alice','user','tldraw-test-team1',1718064000000),(2,'binding','create','b1','binding',json.dumps({'fromId':'s1','toId':'s2'}),'p2','Bob','remote','tldraw-test-team1',1718064060000),(3,'shape','delete','s1','shape',json.dumps({}),'p1','Alice','user','tldraw-test-team1',1718064120000)]
    c.executemany('insert into audit_logs values(?,?,?,?,?,?,?,?,?,?,?)',rows); c.commit(); c.close()

def test_tldraw_parser(tmp_path):
    src=tmp_path/'TLDraw Logs.db'; out=tmp_path/'out.db'; make_tldraw(src)
    assert inspect_tldraw_db(src)['row_count']==3
    r=parse_tldraw_audit_logs(src,out,collection_id='c1')
    assert r['inserted_raw']==3
    c=sqlite3.connect(out); c.row_factory=sqlite3.Row
    assert c.execute('select count(*) from raw_tldraw_events').fetchone()[0]==3
    row=c.execute("select * from parsed_tldraw_events where entity_id='s1' and action='create'").fetchone()
    assert row['shape_text']=='Hello' and row['x']==10 and row['team_id']=='Team 1' and row['is_user_originated']==1
    assert c.execute("select count(*) from parsed_tldraw_events where source='remote'").fetchone()[0]==1

def test_drive_document_unified_snapshots(tmp_path):
    db=tmp_path/'k.db'; csvp=tmp_path/'dailyLog.csv'
    with csvp.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['time','user','action','fileID','file name','mimeType','parent folder','old file name','old parent folder']); w.writeheader(); w.writerow({'time':'2024-06-11T00:00:00.000Z','user':'A','action':'edited','fileID':'f1','file name':'Problem Framing Statement','mimeType':'doc','parent folder':'Team 1/Individual Synthesis','old file name':'','old parent folder':''})
    assert parse_drive_activity_csv(csvp,db,'c1')['inserted']==1
    ch=tmp_path/'Team 1_doc_changelog.txt'; ch.write_text('[EDIT] Alice (• 5:20 PM, Jun 11 (UTC)): text\n2024-06-11T00:01:00.000Z - people/1 edited File at path\n')
    assert parse_document_changelog(ch,db,'c1')['inserted']==2
    tdb=tmp_path/'TLDraw Logs.db'; make_tldraw(tdb); parse_tldraw_audit_logs(tdb,db,'c1')
    u=build_unified_process_events(db,'c1'); assert u['count']>=6
    s=create_board_snapshots(db,'c1'); assert s['count']==3
    state=reconstruct_board_state(db,collection_id='c1'); assert 's1' not in state
    c=sqlite3.connect(db); assert c.execute('select count(*) from unified_process_events').fetchone()[0]>=6

def test_catalog_profile_detection():
    art={'rel_path':'Team 2/Participant 7/Problem Framing Statement [abc123]/email_export_1.html','name':'email_export_1.html','extension':'.html','kind':'file'}
    c=classify_artifact_for_catalog(art,{})
    assert c['source_type']['value']=='google_doc_html_export'
    assert c['team_hint']['value']=='Team 2'
    assert c['participant_hint']['value']=='Participant 7'
    assert c['task_module']=='Problem Framing Statement'
    assert c['file_id']=='abc123'
