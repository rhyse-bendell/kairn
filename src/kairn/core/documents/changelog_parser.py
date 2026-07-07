from __future__ import annotations
import re, sqlite3
from pathlib import Path
from datetime import datetime, timezone
from kairn.core.drive.activity_parser import infer

def ensure_tables(c):
 c.executescript('''create table if not exists document_edit_events(id integer primary key autoincrement, collection_id text, run_id text, source_path text, source_row_index integer, document_name text, inferred_team_id text, inferred_participant_id text, action text, actor text, timestamp_text text, timestamp_utc text, text_snippet text, raw_row text); create unique index if not exists idx_doc_idem on document_edit_events(source_path,source_row_index,ifnull(collection_id,''));''')
def norm_iso(s):
 try: return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(timezone.utc).isoformat().replace('+00:00','Z')
 except Exception: return None
def parse_line(line):
 m=re.match(r'^(\d{4}-\d{2}-\d{2}T[^ ]+)\s+-\s+(.+?)\s+(created|edited|renamed|moved|deleted)\s+(.+)$',line)
 if m: return {'timestamp_text':m.group(1),'timestamp_utc':norm_iso(m.group(1)),'actor':m.group(2),'action':m.group(3).upper(),'text_snippet':m.group(4)}
 m=re.match(r'^\[(\w+)\]\s+(.+?)\s+\(.*?([^()]+UTC)\)\):\s*(.*)$',line)
 if m: return {'action':m.group(1).upper(),'actor':m.group(2),'timestamp_text':m.group(3).strip(),'timestamp_utc':None,'text_snippet':m.group(4)}
 return {'action':None,'actor':None,'timestamp_text':None,'timestamp_utc':None,'text_snippet':line[:500]}
def parse_document_changelog(path, db_path, collection_id=None, run_id=None):
 conn=sqlite3.connect(str(db_path)); ensure_tables(conn); before=conn.execute('select count(*) from document_edit_events').fetchone()[0]; p=Path(path); lines=p.read_text(encoding='utf-8',errors='replace').splitlines(); team,part,_=infer(str(p))
 for i,line in enumerate(lines):
  if not line.strip(): continue
  d=parse_line(line.strip())
  conn.execute('''insert or ignore into document_edit_events(collection_id,run_id,source_path,source_row_index,document_name,inferred_team_id,inferred_participant_id,action,actor,timestamp_text,timestamp_utc,text_snippet,raw_row) values(?,?,?,?,?,?,?,?,?,?,?,?,?)''',(collection_id,run_id,str(p),i,p.name,team,part,d['action'],d['actor'],d['timestamp_text'],d['timestamp_utc'],d['text_snippet'],line))
 conn.commit(); after=conn.execute('select count(*) from document_edit_events').fetchone()[0]; conn.close(); return {'source_rows':len(lines),'inserted':after-before,'count':after}
def parse_all_changelogs_under_root(root_path, db_path, collection_id=None, run_id=None):
 total={'files':0,'source_rows':0,'inserted':0}
 for p in Path(root_path).rglob('*changelog*.txt'):
  r=parse_document_changelog(p,db_path,collection_id,run_id); total['files']+=1; total['source_rows']+=r['source_rows']; total['inserted']+=r['inserted']
 return total
