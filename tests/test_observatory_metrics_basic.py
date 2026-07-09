import sqlite3
from pathlib import Path
from kairn.core.observatory.data_origins import compute_data_origin_inventory
from kairn.core.observatory.tldraw_metrics import compute_tldraw_metrics
from kairn.core.observatory.drive_metrics import compute_drive_metrics
from kairn.core.observatory.document_metrics import compute_document_metrics
from kairn.core.observatory.report import build_observatory_report
from kairn.core.observatory.export import export_observatory_report

def db(tmp_path):
    p=tmp_path/'kairn.db'; c=sqlite3.connect(p)
    c.execute('create table parsed_tldraw_events(timestamp text, actor text, action text, object_id text, object_type text, room text, source text, text text)')
    c.execute("insert into parsed_tldraw_events values('2024-01-01T00:00:00Z','A','create','o1','text','Team 2','user','hello')")
    c.execute('create table drive_activity_events(time text, user text, action text, fileID text, "file name" text, mimeType text, "parent folder" text)')
    c.execute("insert into drive_activity_events values('2024-01-01T01:00:00Z','u','edit','f','Team 2 problem framing','doc','Team 2')")
    c.execute('create table document_edit_events(timestamp text, actor_label text, action text, document_name text, text_snippet text)')
    c.execute("insert into document_edit_events values('2024-01-01T02:00:00Z','A','edit','Team 2 problem framing','some words')")
    c.commit(); c.close(); return p

def test_observatory_end_to_end(tmp_path):
    root=tmp_path/'proj'; (root/'data'/'original').mkdir(parents=True); (root/'data'/'original'/'Team 2 problem framing.txt').write_text('x')
    d=db(tmp_path); project={'project_id':'p','name':'P','project_root':str(root),'db_path':str(d)}
    assert compute_data_origin_inventory(project)[0].rows
    assert any(t.table_id=='tldraw_actor_summary' and t.rows for t in compute_tldraw_metrics(str(d)))
    assert any(t.table_id=='drive_action_counts' and t.rows for t in compute_drive_metrics(str(d),project))
    assert any(t.table_id=='document_changelog_actor_counts' and t.rows for t in compute_document_metrics(str(d),project))
    r=build_observatory_report(project,str(d),team='Team 2',activity='problem framing'); out=export_observatory_report(r,tmp_path/'out')
    assert Path(out['markdown']).exists(); assert (tmp_path/'out'/'output_table_inventory.csv').exists(); assert (tmp_path/'out'/'report_manifest.json').exists()

def test_missing_tldraw_returns_caveat(tmp_path):
    p=tmp_path/'empty.db'; sqlite3.connect(p).close(); tabs=compute_tldraw_metrics(str(p)); assert tabs[0].caveat
