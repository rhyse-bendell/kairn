from __future__ import annotations
import csv, sqlite3, re
from pathlib import Path
from datetime import datetime, timezone
TASK_MODULES=['Individual Synthesis','Team Synthesis','Framing Elements & Terms','Problem Framing Statement','Map & Statement Questions & Feedback','Reflection & Building Motivation','Pre-Workshop Introduction Template','TLDraw Whiteboard Tutorial']
def ensure_tables(c):
 c.executescript('''create table if not exists drive_activity_events(id integer primary key autoincrement, collection_id text, run_id text, source_csv_path text, source_row_index integer, timestamp_utc text, user text, action text, file_id text, file_name text, mime_type text, parent_folder text, old_file_name text, old_parent_folder text, inferred_team_id text, inferred_participant_id text, inferred_task_module text); create unique index if not exists idx_drive_idem on drive_activity_events(source_csv_path,source_row_index,ifnull(collection_id,''));''')
def norm_ts(s):
 if not s: return None
 try: return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(timezone.utc).isoformat().replace('+00:00','Z')
 except Exception: return s
def infer(text):
 text=text or ''; m=re.search(r'(?i)team\s*([0-9]+)',text); p=re.search(r'(?i)(participant|people|person|p)\s*[/ _-]?([0-9]+)',text)
 mod=next((x for x in TASK_MODULES if x.lower() in text.lower()), None)
 return (f'Team {int(m.group(1))}' if m else None, f'Participant {int(p.group(2))}' if p else None, mod)
def parse_drive_activity_csv(csv_path, db_path, collection_id=None, run_id=None):
 conn=sqlite3.connect(str(db_path)); conn.row_factory=sqlite3.Row; ensure_tables(conn); before=conn.execute('select count(*) from drive_activity_events').fetchone()[0]
 with open(csv_path,newline='',encoding='utf-8-sig') as f:
  rows=list(csv.DictReader(f))
 for i,r in enumerate(rows):
  combo=' / '.join([r.get('file name',''),r.get('parent folder',''),r.get('old file name',''),r.get('old parent folder','')]); team,part,mod=infer(combo)
  conn.execute('''insert or ignore into drive_activity_events(collection_id,run_id,source_csv_path,source_row_index,timestamp_utc,user,action,file_id,file_name,mime_type,parent_folder,old_file_name,old_parent_folder,inferred_team_id,inferred_participant_id,inferred_task_module) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(collection_id,run_id,str(Path(csv_path)),i,norm_ts(r.get('time')),r.get('user'),r.get('action'),r.get('fileID'),r.get('file name'),r.get('mimeType'),r.get('parent folder'),r.get('old file name'),r.get('old parent folder'),team,part,mod))
 conn.commit(); after=conn.execute('select count(*) from drive_activity_events').fetchone()[0]; conn.close(); return {'source_rows':len(rows),'inserted':after-before,'count':after}
