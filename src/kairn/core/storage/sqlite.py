from __future__ import annotations
import sqlite3

def connect(db_path:str)->sqlite3.Connection:
    conn=sqlite3.connect(db_path)
    conn.row_factory=sqlite3.Row
    return conn

def init_db(conn:sqlite3.Connection)->None:
    conn.executescript('''
    create table if not exists collections(id text primary key, root_path text, label text, created_at text);
    create table if not exists runs(id text primary key, collection_id text, root_path text, started_at text);
    create table if not exists artifacts(id text primary key, collection_id text, rel_path text unique, path text, name text, extension text, kind text, size_bytes int, modified_at text, content_hash text);
    create table if not exists versions(id text primary key, artifact_id text, content_hash text, created_at text, snapshot_path text);
    create table if not exists events(id text primary key, collection_id text, artifact_id text, action text, actor text, ts text, mentioned_unit text, summary text, raw_row text);
    create table if not exists deltas(id text primary key, event_id text, delta_type text, payload text);
    create table if not exists participants(actor_id text primary key, pid_label text, display_name text, first_seen_ts text);
    create table if not exists artifact_representations(id integer primary key autoincrement, artifact_id text, rep_type text, payload text);
    create table if not exists ingestion_warnings(id integer primary key autoincrement, run_id text, rel_path text, warning text);
    ''')
    conn.commit()
