from __future__ import annotations
import csv, re, sqlite3, zipfile
from pathlib import Path
from .registry import handler
TL_COLS={'id','entity','action','entity_id','entity_type','payload','performed_by_id','performed_by_name','source','room_id','ts'}
DRIVE_COLS={'time','user','action','fileID','file name','mimeType','parent folder'}
CHANGELOG_PATTERNS=[re.compile(r'\[(EDIT|DELETE)\]',re.I), re.compile(r'\b(edited|created|deleted|renamed|moved)\b.*\b(file|document)\b',re.I)]
def _base(path, kind='unknown'):
 return {'path':str(path),'kind':kind,'compatible':False,'confidence':0.0,'detected_handlers':[],'warnings':[]}
def _sqlite(p:Path):
 out=_base(p,'sqlite')
 try:
  c=sqlite3.connect(str(p)); cols=[r[1] for r in c.execute('pragma table_info(audit_logs)').fetchall()]; c.close()
  if TL_COLS.issubset(set(cols)):
   out.update(compatible=True,confidence=.95,detected_handlers=[handler('tldraw_sqlite',.95)])
  else: out['warnings'].append('SQLite database does not contain audit_logs with expected TLDraw columns.')
 except Exception as e: out['warnings'].append(f'Could not inspect SQLite database: {e}')
 return out
def _csv(p:Path):
 out=_base(p,'csv')
 try:
  with p.open(newline='',encoding='utf-8-sig',errors='replace') as f: cols=set(next(csv.DictReader(f)).keys() if False else (csv.DictReader(f).fieldnames or []))
  if DRIVE_COLS.issubset(cols): out.update(compatible=True,confidence=.9,detected_handlers=[handler('drive_activity_csv',.9)])
  else: out['warnings'].append('CSV headers do not match Drive activity columns.')
 except Exception as e: out['warnings'].append(f'Could not inspect CSV: {e}')
 return out
def _txt(p:Path):
 out=_base(p,'doc_changelog')
 try:
  text=p.read_text(encoding='utf-8',errors='replace')[:20000]
  hits=sum(1 for line in text.splitlines() if any(rx.search(line) for rx in CHANGELOG_PATTERNS))
  if hits: out.update(compatible=True,confidence=min(.85,.45+hits*.1),detected_handlers=[handler('document_changelog',min(.85,.45+hits*.1))])
  else: out['warnings'].append('Text file does not look like a supported changelog.')
 except Exception as e: out['warnings'].append(f'Could not inspect text file: {e}')
 return out
def _folder(p:Path):
 out=_base(p,'folder'); names={x.name.lower() for x in p.iterdir()}; handlers=[]; conf=0.0
 if 'dailylog.csv' in names: handlers.append(handler('drive_activity_csv',.8)); conf=max(conf,.8)
 if 'tldraw logs.db' in names or any(x.suffix.lower() in ('.db','.sqlite','.sqlite3') for x in p.iterdir()): handlers.append(handler('tldraw_sqlite',.55)); conf=max(conf,.55)
 if any('changelog' in n or n.endswith('.txt') for n in names): handlers.append(handler('document_changelog',.55)); conf=max(conf,.55)
 if handlers or any(x.is_dir() for x in p.iterdir()): handlers.insert(0,handler('workshop_folder',max(.6,conf))) ; conf=max(conf,.6)
 out.update(compatible=bool(handlers),confidence=conf,detected_handlers=handlers)
 if not handlers: out['warnings'].append('Folder does not contain known workshop files or catalogable artifacts.')
 return out
def detect_compatible_source(path: str) -> dict:
 p=Path(path); 
 if not p.exists():
  out=_base(p); out['warnings'].append('Path does not exist.'); return out
 if p.is_dir(): return _folder(p)
 s=p.suffix.lower()
 if s in ('.db','.sqlite','.sqlite3'): return _sqlite(p)
 if s=='.csv': return _csv(p)
 if s in ('.txt','.log','.md'): return _txt(p)
 if s=='.zip':
  out=_base(p,'zip'); ok=zipfile.is_zipfile(p); out.update(compatible=ok,confidence=.6 if ok else 0,detected_handlers=[handler('zip_archive',.6)] if ok else []); out['warnings'].append('ZIP archives are not auto-extracted; confirm extraction before parsing.'); return out
 out=_base(p); out['warnings'].append('Unsupported file type.'); return out
