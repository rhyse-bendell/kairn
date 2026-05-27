from __future__ import annotations
import hashlib, json, uuid
from datetime import datetime, timezone
from pathlib import Path
from .sqlite import connect, init_db

now=lambda: datetime.now(timezone.utc).isoformat()
uid=lambda: str(uuid.uuid4())

def ensure_collection(db_path, root_path):
    conn=connect(db_path); init_db(conn)
    row=conn.execute('select * from collections where root_path=?',(str(root_path),)).fetchone()
    if row: return row['id']
    cid=uid(); conn.execute('insert into collections values(?,?,?,?)',(cid,str(root_path),Path(root_path).name,now())); conn.commit(); return cid

def start_run(db_path, collection_id, root_path):
    conn=connect(db_path); rid=uid(); conn.execute('insert into runs values(?,?,?,?)',(rid,collection_id,str(root_path),now())); conn.commit(); return rid

def upsert_artifact(db_path, collection_id, c, content_hash=None):
    conn=connect(db_path)
    row=conn.execute('select id from artifacts where rel_path=?',(c.rel_path,)).fetchone()
    if row:
        aid=row['id']; conn.execute('update artifacts set size_bytes=?, modified_at=?, kind=?, content_hash=? where id=?',(c.size_bytes,c.modified_at,c.guessed_kind,content_hash,aid)); conn.commit(); return aid
    aid=uid(); conn.execute('insert into artifacts values(?,?,?,?,?,?,?,?,?,?)',(aid,collection_id,c.rel_path,c.path,c.name,c.extension,c.guessed_kind,c.size_bytes,c.modified_at,content_hash)); conn.commit(); return aid

def add_version(db_path, artifact_id, content_hash, snapshot_path=None):
    conn=connect(db_path); vid=uid(); conn.execute('insert into versions values(?,?,?,?,?)',(vid,artifact_id,content_hash,now(),snapshot_path)); conn.commit(); return vid

def last_version_hash(db_path, artifact_id):
    conn=connect(db_path); r=conn.execute('select content_hash from versions where artifact_id=? order by created_at desc limit 1',(artifact_id,)).fetchone(); return r['content_hash'] if r else None

def add_event(db_path, collection_id, action, ts, artifact_id=None, actor=None, mentioned_unit=None, summary=None, raw_row=None):
    conn=connect(db_path); eid=uid(); conn.execute('insert into events values(?,?,?,?,?,?,?,?,?)',(eid,collection_id,artifact_id,action,actor,ts,mentioned_unit,summary,raw_row)); conn.commit(); return eid

def add_delta(db_path, event_id, delta_type, payload):
    conn=connect(db_path); did=uid(); conn.execute('insert into deltas values(?,?,?,?)',(did,event_id,delta_type,payload)); conn.commit(); return did

def add_representation(db_path, artifact_id, rep_type, payload):
    conn=connect(db_path); conn.execute('insert into artifact_representations(artifact_id,rep_type,payload) values(?,?,?)',(artifact_id,rep_type,payload)); conn.commit()

def add_warning(db_path, run_id, rel_path, warning):
    conn=connect(db_path); conn.execute('insert into ingestion_warnings(run_id,rel_path,warning) values(?,?,?)',(run_id,rel_path,warning)); conn.commit()

def fetchall(db_path, table):
    conn=connect(db_path); return [dict(r) for r in conn.execute(f'select * from {table}').fetchall()]

def hash_bytes(b:bytes): return hashlib.sha256(b).hexdigest()

def upsert_participants_from_events(db_path):
    conn=connect(db_path)
    actors=conn.execute("select actor,min(ts) ts from events where actor is not null and actor!='' group by actor order by actor").fetchall()
    for idx,r in enumerate(actors,1):
        pid=f"PID{idx:03d}"
        conn.execute('insert or replace into participants(actor_id,pid_label,display_name,first_seen_ts) values(?,?,coalesce((select display_name from participants where actor_id=?),?),?)',(r['actor'],pid,r['actor'],r['actor'],r['ts']))
    conn.commit()
