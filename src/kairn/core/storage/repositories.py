from __future__ import annotations
import hashlib, uuid
from datetime import datetime, timezone
from pathlib import Path
from .sqlite import connect, init_db

now = lambda: datetime.now(timezone.utc).isoformat()
uid = lambda: str(uuid.uuid4())
DEFAULT_CATEGORIES=["Document","Dataset","Diagram","Meeting Record","Decision","Comment","Revision","Handoff","Re-entry Point","Open Issue","Evidence","Claim","Assumption","Constraint","Unknown"]

def _conn(db_path):
    conn=connect(db_path); init_db(conn); return conn

def create_collaboration(db_path,name,description="",default_root_path=None):
    conn=_conn(db_path); cid=uid(); t=now();
    conn.execute('insert into collaborations values(?,?,?,?,?,?,?,?,?)',(cid,name,description,'active',t,t,None,default_root_path,'{}')); conn.commit()
    ensure_default_categories(db_path,cid); return cid

def list_collaborations(db_path):
    conn=_conn(db_path); return [dict(r) for r in conn.execute('select * from collaborations order by created_at desc')]

def get_collaboration(db_path, collaboration_id):
    conn=_conn(db_path); r=conn.execute('select * from collaborations where id=?',(collaboration_id,)).fetchone(); return dict(r) if r else None

def update_collaboration(db_path, collaboration_id, **fields):
    if not fields: return
    cols=[]; vals=[]
    for k,v in fields.items(): cols.append(f"{k}=?"); vals.append(v)
    cols.append('updated_at=?'); vals.append(now()); vals.append(collaboration_id)
    conn=_conn(db_path); conn.execute(f"update collaborations set {', '.join(cols)} where id=?",vals); conn.commit()

def set_active_collection(db_path, collaboration_id, collection_id): update_collaboration(db_path, collaboration_id, active_collection_id=collection_id)

def ensure_collection(db_path, root_path, collaboration_id=None):
    conn=_conn(db_path)
    row=conn.execute('select * from collections where root_path=?',(str(root_path),)).fetchone()
    if row:
        if collaboration_id: conn.execute('update collections set collaboration_id=? where id=?',(collaboration_id,row['id'])); conn.commit()
        return row['id']
    cid=uid(); conn.execute('insert into collections(id,collaboration_id,root_path,label,created_at) values(?,?,?,?,?)',(cid,collaboration_id,str(root_path),Path(root_path).name,now())); conn.commit(); return cid

def start_run(db_path, collection_id, root_path, collaboration_id=None):
    conn=_conn(db_path); rid=uid(); conn.execute('insert into runs(id,collection_id,collaboration_id,root_path,started_at) values(?,?,?,?,?)',(rid,collection_id,collaboration_id,str(root_path),now())); conn.commit(); return rid
# existing funcs

def upsert_artifact(db_path, collection_id, c, content_hash=None):
    conn=_conn(db_path); row=conn.execute('select id from artifacts where rel_path=?',(c.rel_path,)).fetchone()
    if row:
        aid=row['id']; conn.execute('update artifacts set size_bytes=?, modified_at=?, kind=?, content_hash=?, collection_id=? where id=?',(c.size_bytes,c.modified_at,c.guessed_kind,content_hash,collection_id,aid)); conn.commit(); return aid
    aid=uid(); conn.execute('insert into artifacts values(?,?,?,?,?,?,?,?,?,?)',(aid,collection_id,c.rel_path,c.path,c.name,c.extension,c.guessed_kind,c.size_bytes,c.modified_at,content_hash)); conn.commit(); return aid

def add_version(db_path, artifact_id, content_hash, snapshot_path=None):
    conn=_conn(db_path); vid=uid(); conn.execute('insert into versions values(?,?,?,?,?)',(vid,artifact_id,content_hash,now(),snapshot_path)); conn.commit(); return vid

def last_version_hash(db_path, artifact_id):
    conn=_conn(db_path); r=conn.execute('select content_hash from versions where artifact_id=? order by created_at desc limit 1',(artifact_id,)).fetchone(); return r['content_hash'] if r else None

def add_event(db_path, collection_id, action, ts, artifact_id=None, actor=None, mentioned_unit=None, summary=None, raw_row=None):
    conn=_conn(db_path); eid=uid(); conn.execute('insert into events values(?,?,?,?,?,?,?,?,?)',(eid,collection_id,artifact_id,action,actor,ts,mentioned_unit,summary,raw_row)); conn.commit(); return eid

def add_delta(db_path, event_id, delta_type, payload): conn=_conn(db_path); did=uid(); conn.execute('insert into deltas values(?,?,?,?)',(did,event_id,delta_type,payload)); conn.commit(); return did

def add_representation(db_path, artifact_id, rep_type, payload): conn=_conn(db_path); conn.execute('insert into artifact_representations(artifact_id,rep_type,payload) values(?,?,?)',(artifact_id,rep_type,payload)); conn.commit()
def add_warning(db_path, run_id, rel_path, warning): conn=_conn(db_path); conn.execute('insert into ingestion_warnings(run_id,rel_path,warning) values(?,?,?)',(run_id,rel_path,warning)); conn.commit()
def fetchall(db_path, table): conn=_conn(db_path); return [dict(r) for r in conn.execute(f'select * from {table}').fetchall()]
def hash_bytes(b:bytes): return hashlib.sha256(b).hexdigest()

def upsert_participants_from_events(db_path):
    conn=_conn(db_path); existing={r['actor_id']:r['pid_label'] for r in conn.execute('select actor_id,pid_label from participants')}
    actors=conn.execute("select actor,min(ts) ts from events where actor is not null and actor!='' group by actor order by actor").fetchall()
    next_num=len(existing)+1
    for r in actors:
        pid=existing.get(r['actor']) or f"PID{next_num:03d}"; next_num += 0 if r['actor'] in existing else 1
        conn.execute('insert or replace into participants(actor_id,pid_label,display_name,first_seen_ts) values(?,?,coalesce((select display_name from participants where actor_id=?),?),?)',(r['actor'],pid,r['actor'],r['actor'],r['ts']))
    conn.commit()

def ensure_default_categories(db_path, collaboration_id):
    conn=_conn(db_path)
    for name in DEFAULT_CATEGORIES:
        exists=conn.execute('select 1 from categories where collaboration_id=? and name=?',(collaboration_id,name)).fetchone()
        if not exists:
            conn.execute('insert into categories values(?,?,?,?,?,?,?,?)',(uid(),collaboration_id,name,'','artifact',None,1,now()))
    conn.commit()

def list_categories(db_path, collaboration_id): conn=_conn(db_path); return [dict(r) for r in conn.execute('select * from categories where collaboration_id=? order by is_default desc,name',(collaboration_id,))]
def create_category(db_path, collaboration_id, name, description="", applies_to="artifact"):
    conn=_conn(db_path); cid=uid(); conn.execute('insert into categories values(?,?,?,?,?,?,?,?)',(cid,collaboration_id,name,description,applies_to,None,0,now())); conn.commit(); return cid

def assign_category_to_artifact(db_path, artifact_id, category_id): conn=_conn(db_path); conn.execute('insert or ignore into artifact_categories values(?,?)',(artifact_id,category_id)); conn.commit()
def assign_category_to_event(db_path, event_id, category_id): conn=_conn(db_path); conn.execute('insert or ignore into event_categories values(?,?)',(event_id,category_id)); conn.commit()


def count_collaborations(db_path):
    conn=_conn(db_path); return conn.execute('select count(*) c from collaborations').fetchone()['c']

def count_collections(db_path, collaboration_id=None):
    conn=_conn(db_path); q='select count(*) c from collections'; p=()
    if collaboration_id: q+=' where collaboration_id=?'; p=(collaboration_id,)
    return conn.execute(q,p).fetchone()['c']
# queries
def count_artifacts(db_path, collection_id=None):
    conn=_conn(db_path); q='select count(*) c from artifacts'; p=()
    if collection_id: q+=' where collection_id=?'; p=(collection_id,)
    return conn.execute(q,p).fetchone()['c']
def count_events(db_path, collection_id=None):
    conn=_conn(db_path); q='select count(*) c from events'; p=()
    if collection_id: q+=' where collection_id=?'; p=(collection_id,)
    return conn.execute(q,p).fetchone()['c']
def count_participants(db_path): conn=_conn(db_path); return conn.execute('select count(*) c from participants').fetchone()['c']
def count_runs(db_path, collaboration_id=None, collection_id=None):
    conn=_conn(db_path); q='select count(*) c from runs where 1=1'; p=[]
    if collaboration_id: q+=' and collaboration_id=?'; p.append(collaboration_id)
    if collection_id: q+=' and collection_id=?'; p.append(collection_id)
    return conn.execute(q,tuple(p)).fetchone()['c']
def count_warnings(db_path, run_id=None):
    conn=_conn(db_path); q='select count(*) c from ingestion_warnings'; p=()
    if run_id: q+=' where run_id=?'; p=(run_id,)
    return conn.execute(q,p).fetchone()['c']
def list_artifacts(db_path, collection_id=None):
    conn=_conn(db_path); q='select a.*, (select count(*) from events e where e.artifact_id=a.id) event_count from artifacts a'; p=()
    if collection_id: q+=' where a.collection_id=?'; p=(collection_id,)
    return [dict(r) for r in conn.execute(q,p)]
def list_events(db_path, collection_id=None, artifact_id=None):
    conn=_conn(db_path); q='select * from events where 1=1'; p=[]
    if collection_id: q+=' and collection_id=?'; p.append(collection_id)
    if artifact_id: q+=' and artifact_id=?'; p.append(artifact_id)
    q+=' order by ts'
    return [dict(r) for r in conn.execute(q,tuple(p))]
def list_warnings(db_path, run_id=None):
    conn=_conn(db_path); q='select * from ingestion_warnings'; p=()
    if run_id:
        q+=' where run_id=?'; p=(run_id,)
    return [dict(r) for r in conn.execute(q,p)]
def list_participants_with_counts(db_path): conn=_conn(db_path); return [dict(r) for r in conn.execute('select p.*, (select count(*) from events e where e.actor=p.actor_id) event_count from participants p order by p.pid_label')]
def list_runs(db_path, collection_id=None, collaboration_id=None):
    conn=_conn(db_path); q='select * from runs where 1=1'; p=[]
    if collection_id: q+=' and collection_id=?'; p.append(collection_id)
    if collaboration_id: q+=' and collaboration_id=?'; p.append(collaboration_id)
    q+=' order by started_at desc'; return [dict(r) for r in conn.execute(q,tuple(p))]
def get_latest_run(db_path, collection_id=None):
    runs=list_runs(db_path,collection_id=collection_id); return runs[0] if runs else None


def list_event_actors(db_path):
    conn=_conn(db_path)
    return [r['actor'] for r in conn.execute("select distinct actor from events where actor is not null and actor!='' order by actor")]

def list_event_actions(db_path):
    conn=_conn(db_path)
    return [r['action'] for r in conn.execute("select distinct action from events where action is not null and action!='' order by action")]

def update_participant_display_name(db_path, actor_id, display_name):
    conn=_conn(db_path)
    conn.execute('update participants set display_name=? where actor_id=?',(display_name,actor_id))
    conn.commit()
