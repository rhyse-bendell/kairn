from __future__ import annotations
import csv, re, sqlite3
from pathlib import Path
from .registry import handler
from .archive import inspect_zip_archive
TL_COLS={'id','entity','action','entity_id','entity_type','payload','performed_by_id','performed_by_name','source','room_id','ts'}
DRIVE_COLS={'time','user','action','fileID','file name','mimeType','parent folder'}
BRACKET=re.compile(r'^\s*\[(EDIT|DELETE|CREATE|INSERT)\]',re.I)
DRIVE_STYLE=re.compile(r'^\d{4}-\d{2}-\d{2}T[^ ]+\s+-\s+.+\s+(created|edited|renamed|moved|deleted|restored)\b',re.I)
def _base(path, kind='unknown', source_type='unknown'):
 return {'path':str(path),'kind':kind,'source_type':source_type,'compatible':False,'confidence':0.0,'available_actions':[],'suggested_next_action':None,'detected_handlers':[],'warnings':[]}
def _finish(o,actions,next_action,conf,stype=None):
 o.update(compatible=True,confidence=conf,available_actions=actions,suggested_next_action=next_action)
 if stype: o['source_type']=stype
 return o
def _sqlite(p):
 out=_base(p,'sqlite','sqlite')
 try:
  c=sqlite3.connect(str(p)); cols=[r[1] for r in c.execute('pragma table_info(audit_logs)').fetchall()]; c.close()
  if TL_COLS.issubset(set(cols)): return _finish(out,['inspect_tldraw','parse_tldraw','build_unified_events','load_replay'],'inspect_tldraw',.98,'tldraw_sqlite_log') | {'detected_handlers':[handler('tldraw_sqlite',.98)]}
  out['warnings'].append('SQLite database does not contain audit_logs with expected TLDraw columns.')
 except Exception as e: out['warnings'].append(f'Could not inspect SQLite database: {e}')
 return out
def _csv(p):
 out=_base(p,'csv','csv')
 try:
  with p.open(newline='',encoding='utf-8-sig',errors='replace') as f: cols=set(csv.DictReader(f).fieldnames or [])
  if DRIVE_COLS.issubset(cols): return _finish(out,['parse_drive_activity','build_unified_events','load_replay'],'parse_drive_activity',.95,'drive_activity_log') | {'detected_handlers':[handler('drive_activity_csv',.95)]}
  out['warnings'].append('CSV headers do not match Drive activity columns.')
 except Exception as e: out['warnings'].append(f'Could not inspect CSV: {e}')
 return out
def _txt(p):
 out=_base(p,'text','text')
 try:
  lines=p.read_text(encoding='utf-8',errors='replace').splitlines()[:500]
  b=any(BRACKET.search(x) for x in lines); d=any(DRIVE_STYLE.search(x) for x in lines)
  if b or d:
   st='mixed_changelog' if b and d else 'document_changelog' if b else 'drive_folder_changelog'
   return _finish(out,['parse_document_changelog','build_unified_events','load_replay'],'parse_document_changelog',.9 if b and d else .84,st) | {'detected_handlers':[handler('document_changelog',.9)]}
  out['warnings'].append('Text file does not look like a supported changelog.')
 except Exception as e: out['warnings'].append(f'Could not inspect text file: {e}')
 return out
def _folder(p):
 out=_base(p,'folder','folder')
 kids=list(p.iterdir()); names={x.name.lower() for x in kids}; has_daily='dailylog.csv' in names; teams=[x for x in kids if x.is_dir() and x.name.lower().startswith('team ')]; parts=[x for x in kids if x.is_dir() and x.name.lower().startswith('participant ')]
 if has_daily and (teams or parts):
  out.update(summary={'dailyLog.csv':str(p/'dailyLog.csv'),'team_folders':[x.name for x in teams],'participant_folders':[x.name for x in parts]})
  return _finish(out,['build_artifact_catalog','parse_drive_activity','parse_document_changelogs','parse_known_sources','build_unified_events','load_replay'],'build_artifact_catalog',.96,'workshop_root_folder') | {'detected_handlers':[handler('workshop_folder',.96)]}
 if has_daily: return _finish(out,['parse_drive_activity','build_unified_events','load_replay'],'parse_drive_activity',.75,'workshop_folder')
 out['warnings'].append('Folder does not contain dailyLog.csv plus Team/Participant folders.'); return out
def _zip(p):
 out=_base(p,'archive','zip_archive'); insp=inspect_zip_archive(p); out['archive_inspection']=insp
 roots=set(insp.get('root_folders',[])); has_root='Teams [124PG]' in roots; has_daily=bool(insp['important_files']['dailyLog.csv']); has_team=bool(insp['team_folders'])
 if p.name=='Team 2 [1poyK].zip' or (p.name.lower().startswith('team ') and has_daily): return _finish(out,['inspect_archive','extract_to_workspace','catalog_after_extract'],'inspect_archive',.9,'nested_team_archive')
 if has_root and has_daily and has_team: return _finish(out,['inspect_archive','extract_to_workspace','build_artifact_catalog_after_extract','parse_known_sources_after_extract'],'inspect_archive',.98,'workshop_archive') | {'detected_handlers':[handler('zip_archive',.98)]}
 if insp['entry_count']: out.update(compatible=True,confidence=.55,available_actions=['inspect_archive','extract_to_workspace'],suggested_next_action='inspect_archive'); out['warnings'].append('ZIP is valid but not the known Teams [124PG] workshop archive.')
 else: out['warnings']+=insp['warnings']
 return out
def detect_compatible_source(path:str)->dict:
 p=Path(path)
 if not p.exists():
  out=_base(p); out['warnings'].append('Path does not exist.'); return out
 if p.is_dir(): return _folder(p)
 s=p.suffix.lower()
 if s in ('.db','.sqlite','.sqlite3'): return _sqlite(p)
 if s=='.csv': return _csv(p)
 if s=='.txt': return _txt(p)
 if s=='.html' and p.name.lower().startswith('email_export'): return _finish(_base(p,'html','google_doc_html_export'),['catalog','extract_text_basic','link_to_changelog'],'catalog',.86)
 if s=='.docx': return _finish(_base(p,'document','static_workshop_material'),['catalog','register_artifact','extract_text_if_dependency_available'],'catalog',.75)
 if s=='.pptx': return _finish(_base(p,'slides','static_workshop_material'),['catalog','register_artifact','extract_text_if_dependency_available'],'catalog',.75)
 if s=='.zip': return _zip(p)
 out=_base(p); out['warnings'].append('Unsupported file type.'); return out
