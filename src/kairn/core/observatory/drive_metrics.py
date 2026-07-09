import csv
from pathlib import Path
from dateutil.parser import parse
from .schemas import table_from_rows
from .report import read_sql_table_or_empty, normalize_timestamp_column, infer_team_from_path_or_room, infer_activity_keyword, safe_group_count

def _load(db, project):
    rows=read_sql_table_or_empty(db,'drive_activity_events')
    if rows: return rows
    if project and project.get('project_root'):
        for p in Path(project['project_root']).rglob('dailyLog.csv'):
            with open(p,newline='',encoding='utf-8') as f: return list(csv.DictReader(f))
    return []
def _pick(rows,*names):
    keys=set().union(*(r.keys() for r in rows)) if rows else set(); low={k.lower():k for k in keys}
    for n in names:
        if n in keys: return n
        if n.lower() in low: return low[n.lower()]
    return None
def compute_drive_metrics(db_path, project=None):
    rows=_load(db_path,project); cols=['total_events','unique_users','unique_files','unique_mime_types','first_timestamp_utc','last_timestamp_utc']
    if not rows: return [table_from_rows('drive_overall_counts','Drive overall counts','No Google Drive activity table or dailyLog.csv detected.','drive',[],columns=cols,caveat='Drive stream unavailable; metrics skipped without failing.')]
    rows=normalize_timestamp_column(rows,['timestamp_utc','time','timestamp','created_at']); user=_pick(rows,'actor_id_or_user','user','actor','email'); action=_pick(rows,'action','event_action'); fid=_pick(rows,'file_id','fileID','fileId'); fname=_pick(rows,'file_name','file name','name'); mime=_pick(rows,'mime_type','mimeType'); parent=_pick(rows,'parent folder','parent_folder','path')
    norm=[]
    for r in rows:
        name=str(r.get(fname,'') if fname else ''); path=name+' '+str(r.get(parent,'') if parent else ''); rr=dict(r, actor_id_or_user=str(r.get(user,'unknown') if user else 'unknown'), action=str(r.get(action,'') if action else ''), file_id=str(r.get(fid,'') if fid else ''), file_name=name, mime_type=str(r.get(mime,'') if mime else ''), inferred_team=infer_team_from_path_or_room(path) or '', activity_keyword=infer_activity_keyword(path) or ''); norm.append(rr)
    tabs=[table_from_rows('drive_overall_counts','Drive overall counts','Google Drive event totals.','drive',[{'total_events':len(norm),'unique_users':len({r['actor_id_or_user'] for r in norm}),'unique_files':len({r['file_id'] for r in norm if r['file_id']}),'unique_mime_types':len({r['mime_type'] for r in norm if r['mime_type']}),'first_timestamp_utc':min([r.get('timestamp_utc','') for r in norm] or ['']),'last_timestamp_utc':max([r.get('timestamp_utc','') for r in norm] or [''])}],columns=cols)]
    for tid,gcols in [('drive_action_counts',['action']),('drive_action_mimetype_counts',['action','mime_type']),('drive_user_action_counts',['actor_id_or_user','action']),('drive_team_action_counts',['inferred_team','action']),('drive_activity_keyword_counts',['activity_keyword'])]: tabs.append(table_from_rows(tid,tid.replace('_',' ').title(),'', 'drive',safe_group_count(norm,gcols,'event_count'),columns=gcols+['event_count']))
    hourly=[]
    for r in norm:
        rr=dict(r)
        try: rr['hour_utc']=parse(r.get('timestamp_utc','')).replace(minute=0,second=0,microsecond=0).strftime('%Y-%m-%dT%H:00:00Z')
        except Exception: rr['hour_utc']=''
        hourly.append(rr)
    tabs.append(table_from_rows('drive_events_by_hour','Drive events by hour','Hourly Drive event counts.','drive',safe_group_count(hourly,['hour_utc'],'event_count'),columns=['hour_utc','event_count']))
    files={}
    for r in norm:
        f=files.setdefault(r['file_id'],{'file_id':r['file_id'],'file_name':r['file_name'],'mime_type':r['mime_type'],'create_count':0,'edit_count':0,'rename_count':0,'move_count':0,'delete_count':0,'permission_change_count':0,'first_timestamp_utc':r.get('timestamp_utc',''),'last_timestamp_utc':r.get('timestamp_utc','')}); a=r['action'].lower(); f['create_count']+=('create' in a or 'upload' in a); f['edit_count']+=('edit' in a or 'modify' in a or 'update' in a); f['rename_count']+='rename' in a; f['move_count']+='move' in a; f['delete_count']+=('delete' in a or 'trash' in a); f['permission_change_count']+=('permission' in a or 'share' in a); f['first_timestamp_utc']=min(f['first_timestamp_utc'],r.get('timestamp_utc','')); f['last_timestamp_utc']=max(f['last_timestamp_utc'],r.get('timestamp_utc',''))
    tabs.append(table_from_rows('drive_file_lifecycle_summary','Drive file lifecycle summary','Counts of observable file lifecycle actions.','drive',list(files.values()),columns=['file_id','file_name','mime_type','create_count','edit_count','rename_count','move_count','delete_count','permission_change_count','first_timestamp_utc','last_timestamp_utc']))
    return tabs
