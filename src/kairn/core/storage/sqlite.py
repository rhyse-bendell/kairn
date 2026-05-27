from __future__ import annotations
import sqlite3


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        '''
    create table if not exists collections(id text primary key, collaboration_id text, root_path text, label text, created_at text);
    create table if not exists collaborations(id text primary key, name text not null, description text, status text, created_at text, updated_at text, active_collection_id text, default_root_path text, metadata_json text);
    create table if not exists runs(id text primary key, collection_id text, collaboration_id text, root_path text, started_at text);
    create table if not exists artifacts(id text primary key, collection_id text, rel_path text, path text, name text, extension text, kind text, size_bytes int, modified_at text, content_hash text);
    create table if not exists versions(id text primary key, artifact_id text, content_hash text, created_at text, snapshot_path text);
    create table if not exists events(id text primary key, collection_id text, artifact_id text, action text, actor text, ts text, mentioned_unit text, summary text, raw_row text);
    create table if not exists deltas(id text primary key, event_id text, delta_type text, payload text);
    create table if not exists participants(actor_id text primary key, pid_label text, display_name text, first_seen_ts text);
    create table if not exists artifact_representations(id integer primary key autoincrement, artifact_id text, rep_type text, payload text);
    create table if not exists ingestion_warnings(id integer primary key autoincrement, run_id text, rel_path text, warning text);
    create table if not exists categories(id text primary key, collaboration_id text, name text not null, description text, applies_to text, color text, is_default integer, created_at text);
    create table if not exists artifact_categories(artifact_id text, category_id text, primary key(artifact_id, category_id));
    create table if not exists event_categories(event_id text, category_id text, primary key(event_id, category_id));
    '''
    )

    cols = {r['name'] for r in conn.execute("pragma table_info(collections)").fetchall()}
    if 'collaboration_id' not in cols:
        conn.execute('alter table collections add column collaboration_id text')
    run_cols = {r['name'] for r in conn.execute("pragma table_info(runs)").fetchall()}
    if 'collaboration_id' not in run_cols:
        conn.execute('alter table runs add column collaboration_id text')
    conn.commit()

    participant_cols = {r['name'] for r in conn.execute("pragma table_info(participants)").fetchall()}
    if 'role' not in participant_cols:
        conn.execute('alter table participants add column role text')
    if 'notes' not in participant_cols:
        conn.execute('alter table participants add column notes text')
    if 'is_ai_agent' not in participant_cols:
        conn.execute('alter table participants add column is_ai_agent integer default 0')

    conn.execute('create unique index if not exists idx_artifacts_collection_rel_path on artifacts(collection_id, rel_path)')
