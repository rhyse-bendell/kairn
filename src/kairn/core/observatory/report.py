from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import re, sqlite3, csv
from .schemas import ObservatoryReport

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
    for t in tables:
        if t.caveat: warnings.append(f'{t.table_id}: {t.caveat}')
    snippets=[]
    for t in tables:
        if 'snippet' in t.table_id: snippets.extend(t.rows[:25])
    return ObservatoryReport(project.get('project_id'),project.get('name'),project.get('project_root'),run_id,datetime.now(timezone.utc).isoformat(),{'team':team,'activity':activity,'bin_minutes':bin_minutes},tables,build_chart_specs(tables),snippets,warnings,GLOBAL_CAVEATS)
