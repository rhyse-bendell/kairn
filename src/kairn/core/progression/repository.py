from __future__ import annotations
import json, sqlite3
from kairn.core.storage.sqlite import connect, init_db

RUN_TABLE="artifact_progression_runs"
MANIFEST_TABLE="artifact_inclusion_manifest"
EVIDENCE_TABLE="artifact_evidence_units"
CANDIDATE_TABLE="artifact_progression_candidates"

def _conn(db_path: str):
    conn=connect(db_path); init_db(conn); ensure_progression_tables(db_path, conn); return conn

def ensure_progression_tables(db_path: str, conn: sqlite3.Connection | None = None) -> None:
    own=conn is None
    conn = conn or connect(db_path)
    conn.executescript('''
    create table if not exists artifact_progression_runs(analysis_run_id text primary key, project_id text, collection_id text, profile text, created_at text, settings_json text, status text, warnings_json text);
    create table if not exists artifact_inclusion_manifest(analysis_run_id text, artifact_id text, collection_id text, rel_path text, artifact_role text, stage text, stage_order text, team_id text, participant_id text, included text, inclusion_status text, inclusion_reason text, content_available text, template_only text, source_type text, source_confidence text, role_confidence text, content_hash text, review_status text, primary key(analysis_run_id, artifact_id));
    create table if not exists artifact_evidence_units(evidence_unit_id text primary key, analysis_run_id text, artifact_id text, collection_id text, stage text, stage_order text, team_id text, participant_id text, unit_index text, unit_type text, text text, normalized_text text, source_locator text, section_heading text, is_prompt text, is_response text, is_template_content text, content_hash text);
    create table if not exists artifact_progression_candidates(candidate_id text primary key, analysis_run_id text, team_id text, source_evidence_unit_id text, target_evidence_unit_id text, source_stage text, target_stage text, relation_type text, method text, similarity_score text, confidence text, rationale text, status text, created_at text, review_note text);
    ''')
    conn.commit()
    if own: conn.close()

def replace_rows(db_path: str, table: str, analysis_run_id: str, rows: list[dict], pk: str | None = None, clear_existing: bool = True):
    conn=_conn(db_path)
    if clear_existing:
        conn.execute(f"delete from {table} where analysis_run_id=?", (analysis_run_id,))
    if pk:
        for r in rows:
            cols=list(r.keys()); vals=[r[c] for c in cols]
            conn.execute(f"insert or replace into {table}({','.join(cols)}) values({','.join(['?']*len(cols))})", vals)
    else:
        if rows:
            cols=list(rows[0].keys())
            conn.executemany(f"insert into {table}({','.join(cols)}) values({','.join(['?']*len(cols))})", [[r.get(c) for c in cols] for r in rows])
    conn.commit(); conn.close()

def upsert_run(db_path: str, row: dict):
    conn=_conn(db_path); cols=list(row.keys())
    conn.execute(f"insert or replace into {RUN_TABLE}({','.join(cols)}) values({','.join(['?']*len(cols))})", [row.get(c) for c in cols]); conn.commit(); conn.close()

def fetch_rows(db_path: str, table: str, analysis_run_id: str) -> list[dict]:
    conn=_conn(db_path); rows=[dict(r) for r in conn.execute(f"select * from {table} where analysis_run_id=?", (analysis_run_id,))]; conn.close(); return rows

def fetch_run(db_path: str, analysis_run_id: str) -> dict | None:
    conn=_conn(db_path); r=conn.execute(f"select * from {RUN_TABLE} where analysis_run_id=?", (analysis_run_id,)).fetchone(); conn.close(); return dict(r) if r else None
