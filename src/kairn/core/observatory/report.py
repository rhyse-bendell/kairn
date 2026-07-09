from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import re, sqlite3, csv
from .schemas import ObservatoryReport, table_from_rows

GLOBAL_CAVEATS=["Digital traces are partial records of platform-mediated activity.","Activity counts are not quality, effort, creativity, or performance scores.","Absence of trace is not absence of work.","Actor names/IDs depend on platform logs and may require participant reconciliation.","Remote/sync events should be preserved for provenance but filtered from contribution-facing summaries where appropriate."]

def table_exists(db_path, table_name):
    if not db_path or not Path(db_path).exists(): return False
    with sqlite3.connect(db_path) as c:
        return c.execute("select name from sqlite_master where type='table' and name=?",(table_name,)).fetchone() is not None

def read_sql_table_or_empty(db_path, table_name):
    if not table_exists(db_path, table_name): return []
    with sqlite3.connect(db_path) as c:
        c.row_factory=sqlite3.Row
        return [dict(r) for r in c.execute(f'select * from "{table_name}"')]

def normalize_timestamp_column(rows, candidates):
    from dateutil.parser import parse
    out=[dict(r) for r in rows]
    for r in out:
        for c in candidates:
            if r.get(c):
                try: r['timestamp_utc']=parse(str(r[c])).strftime('%Y-%m-%dT%H:%M:%SZ')
                except Exception: r['timestamp_utc']=str(r[c])
                break
    return out

def safe_group_count(rows, group_cols, count_name='count'):
    if not rows: return []
    counts={}
    for r in rows:
        key=tuple(r.get(c,'') or '' for c in group_cols); counts[key]=counts.get(key,0)+1
    return [{**{c:key[i] for i,c in enumerate(group_cols)}, count_name:v} for key,v in sorted(counts.items())]

def safe_write_csv(rows, path, columns=None):
    Path(path).parent.mkdir(parents=True, exist_ok=True); columns=columns or (list(rows[0].keys()) if rows else [])
    with open(path,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=columns, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    return str(path)

def infer_team_from_path_or_room(value):
    if not value: return None
    s=str(value); m=re.search(r'(?i)team[ _-]*(\d+)', s)
    if m: return f"Team {m.group(1)}"
    m=re.search(r'(?i)group[ _-]*(\d+)', s)
    return f"Group {m.group(1)}" if m else None

def infer_activity_keyword(value):
    s=str(value or '').lower()
    for k in ['problem framing','concept mapping','concept map','prototype','ideation','reflection','research','presentation']:
        if k in s: return k
    return None

def _diagnostic_tables(db_path):
    inv=read_sql_table_or_empty(db_path,'folder_inventory_sources')
    proc=read_sql_table_or_empty(db_path,'source_processing_summary')
    tables=[]
    if inv:
        ext={}; area={}
        for r in inv:
            e=Path(str(r.get('path',''))).suffix.lower() or '[none]'; size=int(float(r.get('size_bytes') or 0)); ext.setdefault(e,{'extension':e,'file_count':0,'total_size_bytes':0}); ext[e]['file_count']+=1; ext[e]['total_size_bytes']+=size
            k=(r.get('inferred_team') or 'unknown',r.get('inferred_activity') or 'unknown',e); area.setdefault(k,{'inferred_team':k[0],'inferred_activity':k[1],'extension':e,'file_count':0,'total_size_bytes':0}); area[k]['file_count']+=1; area[k]['total_size_bytes']+=size
        tables.append(table_from_rows('folder_inventory_summary','Folder inventory summary','File counts and sizes by extension.','diagnostics',list(ext.values()),columns=['extension','file_count','total_size_bytes']))
        tables.append(table_from_rows('folder_inventory_by_area','Folder inventory by area','File counts by inferred team/activity and extension.','diagnostics',list(area.values()),columns=['inferred_team','inferred_activity','extension','file_count','total_size_bytes']))
    if proc:
        tables.append(table_from_rows('source_processing_summary','Source processing summary','What Kairn recognized, parsed, inventoried, or skipped.','diagnostics',proc,columns=['source_id','source_kind','path','action_taken','processed','records_written','skipped_reason','warnings']))
    return tables

def _normalized_events_table(db_path):
    rows=[]; eid=1
    def add(source_stream, source_kind, team, actor, ts, start, aid, aname, otype, action, text, path, activity):
        nonlocal eid
        rows.append({'event_id':f'evt_{eid:06d}','source_stream':source_stream,'source_kind':source_kind,'team_or_session':team or '','actor':actor or '','timestamp_utc':ts or '','start_seconds':start or '','artifact_id':aid or '','artifact_name':aname or '','object_type':otype or '','action':action or '','text_snippet':(text or '')[:240],'source_path':path or '','inferred_activity':activity or ''}); eid+=1
    for r in read_sql_table_or_empty(db_path,'drive_activity_events'):
        add('drive','drive_daily_log',r.get('inferred_team'),r.get('actor_id_or_user'),r.get('timestamp_utc'),'',r.get('file_id'),r.get('file_name'),r.get('mime_type'),r.get('action'),'',r.get('source_path'),r.get('activity_keyword'))
    for r in read_sql_table_or_empty(db_path,'document_edit_events'):
        add('document_changelog','document_changelog',r.get('inferred_team'),r.get('actor_label'),r.get('timestamp_utc'),'', '',r.get('document_name'),'document',r.get('action'),r.get('text_snippet'),r.get('source_path'),r.get('activity_keyword'))
    for r in read_sql_table_or_empty(db_path,'parsed_tldraw_events') or read_sql_table_or_empty(db_path,'tldraw_events'):
        add('tldraw','tldraw_sqlite_db',r.get('team_or_room'),r.get('actor_label'),r.get('timestamp_utc'),'',r.get('object_id'),r.get('object_id'),r.get('object_type'),r.get('action'),r.get('text_snippet'),r.get('origin') or r.get('source_path'),'')
    for r in read_sql_table_or_empty(db_path,'transcript_turn_events'):
        add('transcript','transcript_srt',r.get('team_or_session'),r.get('speaker'),' ',r.get('start_seconds'),'',r.get('team_or_session'),'speech_turn','speak',r.get('text'),r.get('source_path'),'')
    return table_from_rows('normalized_observatory_events','Normalized observatory events','Cross-stream actor-time-artifact-action table; blank fields mean a stream did not provide that field.','normalized',rows,columns=['event_id','source_stream','source_kind','team_or_session','actor','timestamp_utc','start_seconds','artifact_id','artifact_name','object_type','action','text_snippet','source_path','inferred_activity'])

def _stream_counts_table(tables):
    prim={'drive':'drive_activity_events','document_changelog':'document_edit_events','tldraw':'parsed_tldraw_events','transcript':'transcript_turn_events','normalized':'normalized_observatory_events'}; rows=[]
    processing=next((t for t in tables if t.table_id=='source_processing_summary'),None)
    kind_map={'drive':'drive_daily_log','document_changelog':'document_changelog','tldraw':'tldraw_sqlite_db','transcript':'transcript_srt'}
    for stream in ['drive','document_changelog','tldraw','transcript']:
        rec=sum(len(t.rows) for t in tables if t.source_stream==stream and not t.table_id.endswith('overall_counts'))
        avail=any(t.source_stream==stream and t.rows for t in tables)
        caveat='; '.join([t.caveat for t in tables if t.source_stream==stream and t.caveat])
        detected=parsed=skipped=partial=0
        if processing:
            matches=[r for r in processing.rows if r.get('source_kind')==kind_map[stream]]
            detected=len(matches); parsed=sum(int(float(r.get('records_written') or 0))>0 for r in matches); skipped=sum(str(r.get('action_taken','')).startswith('skipped') for r in matches); partial=sum(bool(r.get('warnings')) for r in matches)
        if parsed: status='parsed_with_warnings' if partial else 'parsed'
        elif detected and skipped: status='skipped'
        elif detected: status='detected_not_parsed'
        else: status='not_detected'
        rows.append({'source_stream':stream,'status':status,'detected_sources':detected,'parsed_sources':parsed,'skipped_sources':skipped,'records':rec,'available':str(avail),'primary_table':prim[stream],'caveat':caveat})
    return table_from_rows('stream_record_counts','Stream record counts','Detection, parsing status, and descriptive record counts by stream.','diagnostics',rows,columns=['source_stream','status','detected_sources','parsed_sources','skipped_sources','records','available','primary_table','caveat'])

def _artifact_history_table(norm_table):
    d={}
    for r in norm_table.rows:
        name=r.get('artifact_name') or r.get('artifact_id') or '[unknown]'; g=d.setdefault(name,{'artifact_name':name,'artifact_type':r.get('object_type') or '','streams':set(),'first_seen':r.get('timestamp_utc') or r.get('start_seconds') or '','last_seen':r.get('timestamp_utc') or r.get('start_seconds') or '','event_count':0,'actors':set(),'actions':set()})
        g['streams'].add(r.get('source_stream','')); g['event_count']+=1
        if r.get('actor'): g['actors'].add(r['actor'])
        if r.get('action'): g['actions'].add(r['action'])
        seen=r.get('timestamp_utc') or r.get('start_seconds') or ''
        if seen: g['first_seen']=min(g['first_seen'] or seen, seen); g['last_seen']=max(g['last_seen'] or seen, seen)
    rows=[]
    for g in d.values(): rows.append({'artifact_name':g['artifact_name'],'artifact_type':g['artifact_type'],'source_streams_seen':', '.join(sorted(g['streams'])),'first_seen':g['first_seen'],'last_seen':g['last_seen'],'event_count':g['event_count'],'actor_count':len(g['actors']),'action_types':', '.join(sorted(g['actions']))})
    return table_from_rows('artifact_history_summary','Artifact history summary','Artifact-level first/last seen and cross-stream activity summary.','diagnostics',sorted(rows,key=lambda x:-x['event_count'])[:500],columns=['artifact_name','artifact_type','source_streams_seen','first_seen','last_seen','event_count','actor_count','action_types'])

def build_observatory_report(project, db_path, run_id=None, team=None, activity=None, bin_minutes=15):
    from .data_origins import compute_data_origin_inventory
    from .tldraw_metrics import compute_tldraw_metrics
    from .drive_metrics import compute_drive_metrics
    from .document_metrics import compute_document_metrics
    from .transcript_metrics import compute_transcript_metrics
    from .case_studies import compute_case_study
    from .visuals import build_chart_specs
    tables=[]; warnings=[]
    for fn,args in [(compute_data_origin_inventory,(project,)),(compute_tldraw_metrics,(db_path,team,bin_minutes)),(compute_drive_metrics,(db_path,project)),(compute_document_metrics,(db_path,project)),(compute_transcript_metrics,(project,db_path))]:
        try: tables.extend(fn(*args))
        except Exception as e: warnings.append(f'{fn.__name__} failed: {e}')
    try: tables.extend(compute_case_study(db_path, project, team=team, activity=activity, bin_minutes=bin_minutes))
    except Exception as e: warnings.append(f'case study failed: {e}')
    try: tables.extend(_diagnostic_tables(db_path))
    except Exception as e: warnings.append(f'diagnostics failed: {e}')
    try:
        norm=_normalized_events_table(db_path); tables.append(norm); tables.append(_artifact_history_table(norm))
    except Exception as e: warnings.append(f'normalized events failed: {e}')
    try: tables.append(_stream_counts_table(tables))
    except Exception as e: warnings.append(f'stream counts failed: {e}')
    for t in tables:
        if t.caveat: warnings.append(f'{t.table_id}: {t.caveat}')
    snippets=[]
    for t in tables:
        if 'snippet' in t.table_id: snippets.extend(t.rows[:25])
    return ObservatoryReport(project.get('project_id'),project.get('name'),project.get('project_root'),run_id,datetime.now(timezone.utc).isoformat(),{'team':team,'activity':activity,'bin_minutes':bin_minutes},tables,build_chart_specs(tables),snippets,warnings,GLOBAL_CAVEATS)
