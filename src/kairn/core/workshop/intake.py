from __future__ import annotations
from pathlib import Path
import json, sqlite3
from kairn.core.sources.detection import detect_compatible_source
from kairn.core.sources.archive import inspect_zip_archive, extract_zip_to_workspace
from kairn.core.tldraw.sqlite_parser import inspect_tldraw_db, parse_tldraw_audit_logs
from kairn.core.drive.activity_parser import parse_drive_activity_csv
from kairn.core.documents.changelog_parser import parse_document_changelog, parse_all_changelogs_under_root
from kairn.core.ingestion.service import ingest_root
from kairn.core.catalog.artifact_catalog import export_artifact_catalog
from kairn.core.process.unified_events import build_unified_process_events
from kairn.core.replay import load_replay_events, get_replay_summary
from kairn.core.replay.export import export_replay_events_csv, export_replay_events_json, export_replay_summary_json
from kairn.core.export.workshop import export_workshop_data

def _folder_summary(root:Path):
    files=list(root.rglob('*'))
    return {'dailyLog.csv':[str(p) for p in files if p.name=='dailyLog.csv'],'tldraw_dbs':[str(p) for p in files if p.name=='TLDraw Logs.db' or p.suffix.lower() in ('.db','.sqlite','.sqlite3')],'changelogs':[str(p) for p in files if p.suffix.lower()=='.txt' and 'changelog' in p.name.lower()],'html_exports':[str(p) for p in files if p.suffix.lower()=='.html' and p.name.lower().startswith('email_export')],'documents':[str(p) for p in files if p.suffix.lower()=='.docx'],'slides':[str(p) for p in files if p.suffix.lower()=='.pptx'],'nested_zips':[str(p) for p in files if p.suffix.lower()=='.zip'],'team_folders':[str(p) for p in root.iterdir() if p.is_dir() and p.name.lower().startswith('team ')],'participant_folders':[str(p) for p in root.iterdir() if p.is_dir() and p.name.lower().startswith('participant ')]}

def inspect_workshop_path(path:str)->dict:
    p=Path(path); det=detect_compatible_source(path); out={'path':str(p),'detection':det,'warnings':list(det.get('warnings',[]))}
    if det.get('kind')=='archive': out['archive']=inspect_zip_archive(p)
    elif det.get('source_type')=='workshop_root_folder': out['folder_summary']=_folder_summary(p)
    elif det.get('source_type')=='tldraw_sqlite_log': out['tldraw']=inspect_tldraw_db(p)
    elif det.get('kind') in ('csv','text'): out['parser_ready']=det.get('compatible')
    return out

def _count(db,t):
    c=sqlite3.connect(str(db))
    try: return c.execute(f'select count(*) from {t}').fetchone()[0]
    except Exception: return 0
    finally: c.close()

def _write_summary(summary,out_dir):
    out=Path(out_dir); out.mkdir(parents=True,exist_ok=True)
    (out/'workshop_intake_summary.json').write_text(json.dumps(summary,indent=2,default=str),encoding='utf-8')
    (out/'workshop_intake_summary.txt').write_text('\n'.join(f'{k}: {v}' for k,v in summary.items() if k!='detection')+'\n',encoding='utf-8')
    return {'workshop_intake_summary_json':str(out/'workshop_intake_summary.json'),'workshop_intake_summary_txt':str(out/'workshop_intake_summary.txt')}

def prepare_workshop_source(path:str, db_path:str, workspace_dir:str, collection_id=None, run_id=None, profile='problem_framing_workshop', extract=False)->dict:
    p=Path(path); insp=inspect_workshop_path(path); det=insp['detection']; warnings=list(insp.get('warnings',[])); outputs={}; root=None
    if det.get('kind')=='archive':
        if extract:
            ex=extract_zip_to_workspace(p,workspace_dir); outputs['extraction']=ex; root=Path(ex['extracted_root_paths'][0]) if ex.get('extracted_root_paths') else None; warnings+=ex.get('warnings',[])
        else:
            return {'detection':det,'archive':insp.get('archive'),'extracted_root_path':None,'warnings':warnings+['Archive inspected only; call with extract=True to extract safely.'],'output_paths':outputs}
    elif p.is_dir(): root=p
    if root:
        ing=ingest_root(str(root),db_path,collaboration_id=None); collection_id=collection_id or ing['collection_id']; run_id=run_id or ing['run_id']
        out_dir=Path(workspace_dir)/'exports'/str(run_id); outputs.update(export_artifact_catalog(db_path,out_dir,collection_id=collection_id,profile_name_or_path=profile))
        fs=_folder_summary(root)
        for csvp in fs['dailyLog.csv']: outputs['drive_activity']=parse_drive_activity_csv(csvp,db_path,collection_id,run_id)
        outputs['document_changelogs']=parse_all_changelogs_under_root(root,db_path,collection_id,run_id)
        for dbp in fs['tldraw_dbs']:
            try: outputs.setdefault('tldraw',[]).append(parse_tldraw_audit_logs(dbp,db_path,collection_id,run_id))
            except Exception as e: warnings.append(f'TLDraw parse skipped for {dbp}: {e}')
    elif det.get('source_type')=='tldraw_sqlite_log': outputs['tldraw']=parse_tldraw_audit_logs(p,db_path,collection_id,run_id)
    elif det.get('source_type')=='drive_activity_log': outputs['drive_activity']=parse_drive_activity_csv(p,db_path,collection_id,run_id)
    elif det.get('kind')=='text': outputs['document_changelog']=parse_document_changelog(p,db_path,collection_id,run_id)
    outputs['unified_process_events']=build_unified_process_events(db_path,collection_id,run_id)
    events=load_replay_events(db_path,collection_id,run_id); summ=get_replay_summary(events); out_dir=Path(workspace_dir)/'exports'/str(run_id or 'ad_hoc'); outputs.update(export_workshop_data(db_path,out_dir)); outputs['replay_events_csv']=export_replay_events_csv(events,out_dir/'replay_events.csv'); outputs['replay_events_json']=export_replay_events_json(events,out_dir/'replay_events.json'); outputs['replay_summary_json']=export_replay_summary_json(summ,out_dir/'replay_summary.json')
    summary={'detection':det,'collection_id':collection_id,'run_id':run_id,'catalog_rows':_count(db_path,'artifacts'),'raw_tldraw_events':_count(db_path,'raw_tldraw_events'),'parsed_tldraw_events':_count(db_path,'parsed_tldraw_events'),'drive_activity_events':_count(db_path,'drive_activity_events'),'document_edit_events':_count(db_path,'document_edit_events'),'unified_process_events':_count(db_path,'unified_process_events'),'board_snapshots':_count(db_path,'board_snapshots'),'warnings':warnings,'output_paths':outputs}
    summary['output_paths'].update(_write_summary(summary,out_dir)); return summary
