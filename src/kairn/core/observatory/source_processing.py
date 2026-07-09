from __future__ import annotations

import csv
import json
import re
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path

from kairn.core.observatory.report import infer_team_from_path_or_room, infer_activity_keyword

_SKIP_DISCOVERY_NAMES = {"kairn.db", "kairn_project.json"}
_SKIP_DISCOVERY_DIRS = {"settings", "runs", "exports", "logs", "parsed", "catalog", "__pycache__"}
_ARTIFACT_EXTS = {".docx", ".pptx", ".html", ".pdf", ".txt"}
_AUDIO_EXTS = {".m4a", ".mp3", ".wav"}


def _is_probably_tldraw_db(path: Path) -> bool:
    if path.name.lower() == "kairn.db":
        return False
    try:
        with sqlite3.connect(path) as conn:
            names = [r[0].lower() for r in conn.execute("select name from sqlite_master where type='table'").fetchall()]
        hay = " ".join(names) + " " + path.name.lower()
        return any(token in hay for token in ("tldraw", "shape", "room", "snapshot", "record", "event"))
    except Exception:
        return False


def _classify_observatory_file(path: Path) -> tuple[str, str]:
    name = path.name.lower()
    ext = path.suffix.lower()
    if name == "kairn.db":
        return "unknown_file", "Kairn project database skipped as an observatory source."
    if name == "dailylog.csv":
        return "drive_daily_log", "Google Drive daily activity log."
    if name == "changelog.txt" or name.endswith("_changelog.txt"):
        return "document_changelog", "Document changelog text file."
    if ext == ".db":
        if _is_probably_tldraw_db(path):
            return "tldraw_sqlite_db", "SQLite database that appears to contain TLDraw-like logs."
        return "unknown_file", "SQLite database did not look like TLDraw logs."
    if ext == ".srt":
        return "transcript_srt", "SRT transcript file."
    if ext in _AUDIO_EXTS:
        return "audio_file", "Audio artifact recorded for inventory only; Kairn does not transcribe audio."
    if ext in _ARTIFACT_EXTS:
        return "document_artifact", "Document/export artifact recorded for inventory/provenance."
    return "unknown_file", "Unrecognized file type recorded for folder inventory."


def _infer_area(path_text: str) -> tuple[str, str]:
    return infer_team_from_path_or_room(path_text) or "unknown", infer_activity_keyword(path_text) or "unknown"


def discover_observatory_sources(source_path: str | Path) -> list[dict]:
    """Recursively discover supported observatory sources under a file, folder, or zip archive."""
    root = Path(source_path).expanduser()
    if not root.exists():
        return [{"source_kind": "unknown_file", "path": str(root), "relative_path": root.name, "inferred_team": "unknown", "inferred_activity": "unknown", "size_bytes": 0, "mtime": None, "reason": "Path does not exist."}]
    temp_extract = None
    if root.is_file() and root.suffix.lower() == ".zip":
        temp_extract = root.parent / f".{root.stem}_observatory_extract"
        temp_extract.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(root) as zf:
                zf.extractall(temp_extract)
            root = temp_extract
        except Exception as exc:
            return [{"source_kind": "unknown_file", "path": str(root), "relative_path": root.name, "inferred_team": "unknown", "inferred_activity": "unknown", "size_bytes": root.stat().st_size if root.exists() else 0, "mtime": None, "reason": f"Zip extraction failed: {exc}"}]
    files = []
    if root.is_dir():
        for p in root.rglob("*"):
            if any(part in _SKIP_DISCOVERY_DIRS for part in p.parts) or p.name in _SKIP_DISCOVERY_NAMES:
                continue
            if p.is_file():
                files.append(p)
    else:
        files = [root]
    rows=[]
    for p in sorted(files):
        kind, reason = _classify_observatory_file(p)
        try: rel = str(p.relative_to(root if root.is_dir() else root.parent))
        except Exception: rel = p.name
        team, activity = _infer_area(str(p))
        try: st=p.stat(); size=st.st_size; mtime=datetime.fromtimestamp(st.st_mtime).isoformat()
        except Exception: size=0; mtime=None
        rows.append({"source_kind": kind, "path": str(p), "relative_path": rel, "inferred_team": team, "inferred_activity": activity, "size_bytes": size, "mtime": mtime, "reason": reason})
    return rows


def _ensure_table(conn, name, columns):
    conn.execute(f'create table if not exists "{name}" ({", ".join([c+" text" for c in columns])})')


def _insert_rows(conn, table, columns, rows):
    if not rows: return 0
    _ensure_table(conn, table, columns)
    conn.executemany(f'insert into "{table}" ({", ".join(columns)}) values ({", ".join(["?" for _ in columns])})', [[str(r.get(c, "")) for c in columns] for r in rows])
    return len(rows)


def _parse_srt_time(value):
    h,m,rest=value.strip().replace('.', ',').split(':',2); s,ms=(rest.split(',',1)+['0'])[:2]
    return int(h)*3600+int(m)*60+int(s)+int(ms[:3].ljust(3,'0'))/1000


def _split_speaker(text):
    t=" ".join(text.split())
    m=re.match(r'^\[([^\]]{1,80})\]\s*(.*)$', t)
    if m: return m.group(1).strip(), m.group(2).strip()
    m=re.match(r'^([A-Za-z][\w .\-]{0,79}):\s*(.*)$', t)
    if m: return m.group(1).strip(), m.group(2).strip()
    return "unknown", t


def _parse_srt_file(path, team):
    text=Path(path).read_text(encoding='utf-8', errors='ignore').replace('\r\n','\n')
    rows=[]
    for block in re.split(r'\n\s*\n', text.strip()):
        lines=[x.strip() for x in block.split('\n') if x.strip()]
        if not lines: continue
        idx=lines[0] if lines[0].isdigit() else str(len(rows)+1)
        time_line=next((x for x in lines if '-->' in x), '')
        if not time_line: continue
        body=lines[lines.index(time_line)+1:]
        start,end=[x.strip().split()[0] for x in time_line.split('-->')[:2]]
        speaker, utter=_split_speaker(' '.join(body))
        ss,ee=_parse_srt_time(start),_parse_srt_time(end)
        rows.append({'source_path':str(path),'team_or_session':team or 'unknown','speaker':speaker,'start_time':start,'end_time':end,'start_seconds':ss,'end_seconds':ee,'duration_seconds':round(max(0,ee-ss),3),'text':utter,'word_count':len(re.findall(r"\b\w+\b", utter)),'turn_index':idx})
    return rows


def _process_discovered_sources(discovered, db_path):
    summary=[]; warnings=[]
    with sqlite3.connect(db_path) as conn:
        for i,src in enumerate(discovered,1):
            kind=src['source_kind']; path=Path(src['path']); records=0; action='inventory_only'; warn=''
            try:
                if kind=='drive_daily_log':
                    rows=list(csv.DictReader(open(path,newline='',encoding='utf-8-sig',errors='ignore')))
                    cols=['timestamp_utc','actor_id_or_user','action','file_id','file_name','mime_type','parent_folder','source_path','inferred_team','activity_keyword','raw_json']
                    out=[]
                    for r in rows:
                        low={k.lower():k for k in r}
                        pick=lambda *ns: next((r[low[n.lower()]] for n in ns if n.lower() in low), '')
                        out.append({'timestamp_utc':pick('timestamp_utc','time','timestamp','created_at'),'actor_id_or_user':pick('actor_id_or_user','user','actor','email'),'action':pick('action','event_action','type'),'file_id':pick('file_id','fileid','file id'),'file_name':pick('file_name','file name','name','title'),'mime_type':pick('mime_type','mimetype','mime type'),'parent_folder':pick('parent_folder','parent folder','path','folder'),'source_path':str(path),'inferred_team':src['inferred_team'],'activity_keyword':src['inferred_activity'],'raw_json':json.dumps(r,default=str)})
                    records=_insert_rows(conn,'drive_activity_events',cols,out); action='parsed_drive_daily_log'
                elif kind=='document_changelog':
                    lines=path.read_text(encoding='utf-8',errors='ignore').splitlines(); out=[]
                    for n,line in enumerate(lines,1):
                        if not line.strip(): continue
                        action='delete' if re.search('delete|remove|replace',line,re.I) else 'edit'
                        actor='unknown'; m=re.search(r'\bby\s+([^\[\]\(\):]{1,60})',line,re.I)
                        if m: actor=m.group(1).strip()
                        out.append({'timestamp_utc':'','actor_label':actor,'action':action,'document_name':path.stem.replace('_changelog',''),'text_snippet':line[:500],'source_path':str(path),'inferred_team':src['inferred_team'],'activity_keyword':src['inferred_activity'],'line_number':n})
                    records=_insert_rows(conn,'document_edit_events',['timestamp_utc','actor_label','action','document_name','text_snippet','source_path','inferred_team','activity_keyword','line_number'],out); action='parsed_document_changelog'
                elif kind=='transcript_srt':
                    rows=_parse_srt_file(path, src['inferred_team'] if src['inferred_team']!='unknown' else Path(src['relative_path']).parent.name)
                    records=_insert_rows(conn,'transcript_turn_events',['source_path','team_or_session','speaker','start_time','end_time','start_seconds','end_seconds','duration_seconds','text','word_count','turn_index'],rows); action='parsed_transcript_srt'
                elif kind=='tldraw_sqlite_db':
                    try:
                        with sqlite3.connect(path) as sc:
                            sc.row_factory=sqlite3.Row; tables=[r[0] for r in sc.execute("select name from sqlite_master where type='table'")]
                            table=next((t for t in tables if any(x in t.lower() for x in ('event','record','shape','tldraw'))), None)
                            if not table: raise ValueError('No TLDraw-like event table found')
                            data=[dict(r) for r in sc.execute(f'select * from "{table}" limit 10000')]
                        out=[]
                        for r in data:
                            raw=json.dumps(r,default=str); low={k.lower():k for k in r}; pick=lambda *ns: next((r[low[n.lower()]] for n in ns if n.lower() in low), '')
                            out.append({'timestamp_utc':pick('timestamp_utc','timestamp','time','created_at','ts'),'team_or_room':pick('team_or_room','room','room_id') or src['inferred_team'],'actor_label':pick('actor_label','actor','user','user_id','session_id') or 'unknown','action':pick('action','event_type','op','type') or 'event','object_id':pick('object_id','shape_id','record_id','id'),'object_type':pick('object_type','shape_type','record_type','type'),'source':'user','origin':str(path),'text_snippet':pick('text','plain_text','content','label'),'raw_json':raw})
                        records=_insert_rows(conn,'parsed_tldraw_events',['timestamp_utc','team_or_room','actor_label','action','object_id','object_type','source','origin','text_snippet','raw_json'],out); action='parsed_tldraw_sqlite_db'
                    except Exception as exc:
                        warn=f'TLDraw DB structure unfamiliar: {exc}'; warnings.append(f'{path}: {warn}'); action='skipped_tldraw_warning'
                else:
                    action='inventory_only'
            except Exception as exc:
                warn=str(exc); warnings.append(f'{path}: {warn}')
            summary.append({'source_id':str(i),'source_kind':kind,'path':str(path),'action_taken':action,'processed':str(records>0 or kind in ('audio_file','document_artifact','unknown_file')),'records_written':str(records),'skipped_reason':'' if records or action=='inventory_only' else warn,'warnings':warn})
        _insert_rows(conn,'source_processing_summary',['source_id','source_kind','path','action_taken','processed','records_written','skipped_reason','warnings'],summary)
        _insert_rows(conn,'folder_inventory_sources',['source_kind','path','relative_path','inferred_team','inferred_activity','size_bytes','mtime','reason'],discovered)
        conn.commit()
    return summary,warnings
