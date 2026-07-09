from pathlib import Path
from .schemas import table_from_rows
from .report import infer_team_from_path_or_room, infer_activity_keyword, table_exists, read_sql_table_or_empty

def _area(p):
    parts=Path(p).parts
    for a in ['original','extracted','parsed','runs','settings','staging']:
        if a in parts: return a
    return parts[0] if parts else 'project'

def compute_data_origin_inventory(project):
    root=Path(project.get('project_root') or '.'); rows=[]
    if root.exists():
        for p in root.rglob('*'):
            if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts:
                rel=str(p.relative_to(root)); rows.append({'path':rel,'extension':p.suffix.lower() or '[none]','size_bytes':p.stat().st_size,'inferred_team':infer_team_from_path_or_room(rel),'inferred_activity':infer_activity_keyword(rel),'source_area':_area(rel)})
    ext={}
    team={}
    for r in rows:
        ext.setdefault(r['extension'],[0,0]); ext[r['extension']][0]+=1; ext[r['extension']][1]+=r['size_bytes']
        key=(r.get('inferred_team') or '', r['extension']); team[key]=team.get(key,0)+1
    tables=[table_from_rows('data_origin_file_inventory','Data-origin file inventory','Files visible under the project root.','data_origins',rows,{'project_root':str(root)},['path','extension','size_bytes','inferred_team','inferred_activity','source_area']),
            table_from_rows('data_origin_extension_counts','File counts by extension','Trace ecology counts by extension.','data_origins',[{'extension':k,'file_count':v[0],'total_size_bytes':v[1]} for k,v in sorted(ext.items())],columns=['extension','file_count','total_size_bytes']),
            table_from_rows('data_origin_team_extension_counts','File counts by inferred team and extension','File counts grouped by inferred team and extension.','data_origins',[{'team':k[0],'extension':k[1],'file_count':v} for k,v in sorted(team.items())],columns=['team','extension','file_count'])]
    try:
        from kairn.core.projects.service import read_source_registry
        reg=read_source_registry(project)
        entries=reg.get('sources', reg if isinstance(reg,list) else [])
    except Exception: entries=[]
    tables.append(table_from_rows('source_registry_summary','Source registry summary','Registered source streams and copy/link status.','data_origins',entries,columns=['source_id','source_type','status','original_path','project_path','added_at','detection_confidence']))
    db=project.get('db_path') or str(root/'kairn.db')
    streams=[('tldraw',['parsed_tldraw_events','raw_tldraw_events']),('drive',['drive_activity_events']),('document_changelog',['document_edit_events']),('transcript',['transcript_events','speech_events']),('artifacts',['artifacts']),('replay/unified events',['unified_process_events','replay_events'])]
    av=[]
    for name,tbs in streams:
        found=None; count=None
        for tb in tbs:
            if table_exists(db,tb): found=tb; count=len(read_sql_table_or_empty(db,tb)); break
        av.append({'stream':name,'available':bool(found),'record_count':count or 0,'source_table_or_file':found or '', 'caveat':'' if found else 'Stream not detected; absence does not mean no off-platform work occurred.'})
    tables.append(table_from_rows('stream_availability_summary','Stream availability summary','Availability and record counts for expected observatory streams.','data_origins',av,columns=['stream','available','record_count','source_table_or_file','caveat']))
    return tables
