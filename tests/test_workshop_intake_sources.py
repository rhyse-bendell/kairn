import csv, json, sqlite3, zipfile
from pathlib import Path
from kairn.core.sources import detect_compatible_source
from kairn.core.sources.archive import inspect_zip_archive, extract_zip_to_workspace
from kairn.core.workshop.intake import prepare_workshop_source, inspect_workshop_path
from kairn.core.replay import load_replay_events, get_replay_summary

COLS=['time','user','action','fileID','file name','mimeType','parent folder','old file name','old parent folder']

def make_folder(root:Path):
    root.mkdir(); (root/'Team 1 [1MMrs]').mkdir(); (root/'Participant 2').mkdir()
    with (root/'dailyLog.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=COLS); w.writeheader(); w.writerow({'time':'2024-06-11T00:00:00.000Z','user':'Amy','action':'edit','fileID':'f1','file name':'Problem Framing Statement','mimeType':'application/vnd.google-apps.document','parent folder':'Teams [124PG]/Team 1 [1MMrs]/Participant 2','old file name':'','old parent folder':''})
    (root/'Team 1 [1MMrs]'/'doc_changelog.txt').write_text('2024-06-11T00:01:00.000Z - people/2 created Team 1 at Groups [124PG]/Team 1 [1MMrs]\n[EDIT] Mueller, Amy Mueller (• 5:20 PM, Jun 11 (UTC)): hello\n[DELETE] Forest Cook (• 9:30 PM, Jun 10 (UTC)): bye\n',encoding='utf-8')
    (root/'Team 1 [1MMrs]'/'email_export_1.html').write_text('<html>hi</html>')
    (root/'Team 1 [1MMrs]'/'material.docx').write_bytes(b'PKfake')
    (root/'Team 1 [1MMrs]'/'slides.pptx').write_bytes(b'PKfake')
    (root/'Team 2 [1poyK].zip').write_bytes(b'PK\x05\x06'+b'\0'*18)
    db=root/'TLDraw Logs.db'; c=sqlite3.connect(db)
    c.execute('create table audit_logs(id integer primary key, entity text, action text, entity_id text, entity_type text, payload text, performed_by_id text, performed_by_name text, source text, room_id text, ts integer)')
    c.executemany('insert into audit_logs values(?,?,?,?,?,?,?,?,?,?,?)',[(1,'shape','create','s1','geo',json.dumps({'type':'geo','x':1,'y':2,'props':{'w':3,'h':4,'richText':{'content':[{'text':'Idea'}]}}}),'p1','Alice','user','tldraw-test-team-1',1718064000000),(2,'binding','update','b1','arrow',json.dumps({'props':{'start':{'boundShapeId':'s1'},'end':{'boundShapeId':'s2'}}}),'p2','Bob','remote','tldraw-test-team2',1718064060000)])
    c.commit(); c.close(); return db

def test_detect_teams_like_zip_and_archive_counts(tmp_path):
    root=tmp_path/'Teams [124PG]'; make_folder(root); zp=tmp_path/'Teams [124PG].zip'
    with zipfile.ZipFile(zp,'w') as z:
        for p in root.rglob('*'): z.write(p,p.relative_to(tmp_path).as_posix())
    det=detect_compatible_source(zp)
    assert det['source_type']=='workshop_archive' and 'extract_to_workspace' in det['available_actions']
    insp=inspect_zip_archive(zp)
    assert insp['important_files']['dailyLog.csv'] and insp['important_files']['html_exports'] and insp['important_files']['nested_zips']
    ex=extract_zip_to_workspace(zp,tmp_path/'ws')
    assert ex['extracted_root_paths'][0].endswith('Teams [124PG]')

def test_detect_folder_db_csv_changelog_and_prepare(tmp_path):
    root=tmp_path/'Teams [124PG]'; dbsrc=make_folder(root)
    assert detect_compatible_source(root)['source_type']=='workshop_root_folder'
    assert detect_compatible_source(dbsrc)['source_type']=='tldraw_sqlite_log'
    assert detect_compatible_source(root/'dailyLog.csv')['source_type']=='drive_activity_log'
    txt=root/'Team 1 [1MMrs]'/'doc_changelog.txt'; assert detect_compatible_source(txt)['source_type']=='mixed_changelog'
    out=prepare_workshop_source(str(root),str(tmp_path/'k.db'),str(tmp_path/'workspace'))
    assert out['catalog_rows'] >= 6 and out['drive_activity_events']==1 and out['document_edit_events']==3 and out['parsed_tldraw_events']==2 and out['unified_process_events']>=6
    ev=load_replay_events(str(tmp_path/'k.db'),out['collection_id'],out['run_id'])
    summ=get_replay_summary(ev)
    assert ev and summ['counts_by_source']['tldraw']==2 and 'Alice' in summ['counts_by_actor']
    assert Path(out['output_paths']['workshop_intake_summary_json']).exists()

def test_document_static_detection(tmp_path):
    html=tmp_path/'email_export_1.html'; html.write_text('<html></html>')
    doc=tmp_path/'material.docx'; doc.write_bytes(b'')
    ppt=tmp_path/'slides.pptx'; ppt.write_bytes(b'')
    assert detect_compatible_source(html)['source_type']=='google_doc_html_export'
    assert detect_compatible_source(doc)['kind']=='document'
    assert detect_compatible_source(ppt)['kind']=='slides'
