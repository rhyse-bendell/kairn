from __future__ import annotations
import csv,json,sqlite3
from pathlib import Path
TABLES=['raw_tldraw_events','parsed_tldraw_events','drive_activity_events','document_edit_events','unified_process_events','board_snapshots']
def _exists(c,t): return c.execute("select 1 from sqlite_master where type='table' and name=?",(t,)).fetchone()
def export_workshop_data(db_path,out_dir):
 out=Path(out_dir); out.mkdir(parents=True,exist_ok=True); c=sqlite3.connect(str(db_path)); c.row_factory=sqlite3.Row; summary={}
 for t in TABLES:
  if not _exists(c,t): summary[t]=0; continue
  rows=[dict(r) for r in c.execute(f'select * from {t}')]; summary[t]=len(rows)
  if rows:
   with (out/f'{t}.csv').open('w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
   suffix='json' if t=='board_snapshots' else 'jsonl'
   with (out/f'{t}.{suffix}').open('w',encoding='utf-8') as f:
    if suffix=='json': json.dump(rows,f,indent=2)
    else:
     for r in rows: f.write(json.dumps(r)+'\n')
 (out/'workshop_data_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
 (out/'workshop_data_summary.txt').write_text('\n'.join(f'{k}: {v}' for k,v in summary.items())+'\n',encoding='utf-8')
 c.close(); return {'out_dir':str(out),'summary':summary}
