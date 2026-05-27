from pathlib import Path
import gzip
import json

from kairn.core.storage.repositories import ensure_collection, start_run, add_event, upsert_participants_from_events, update_participant_display_name
from kairn.core.paths import ensure_run_dirs
from kairn.core.export.compiled_json import export_compiled
from kairn.core.export.jsonl import export_jsonl
from kairn.core.export.prompt_chunks import export_prompt_chunks
from kairn.core.analysis.sessions import build_sessions
from kairn.core.visualization.timeline_plotly import build_timeline_html
from kairn.core.maintenance.diagnose import run_diagnostics


class C:
    rel_path='a.txt'; path='a.txt'; name='a.txt'; extension='.txt'; guessed_kind='text'; size_bytes=1; modified_at='2026-01-01T00:00:00+00:00'

def test_run_dirs_and_exports(tmp_path):
    db=str(tmp_path/'k.db')
    cid=ensure_collection(db,str(tmp_path/'src'))
    run=start_run(db,cid,str(tmp_path/'src'))
    rid=ensure_run_dirs(db,collection_id=cid,run_id=run)
    assert Path(rid['json_dir']).exists()
    e1=add_event(db,cid,'edited','2026-01-01T00:00:00+00:00',actor='alice',summary='x')
    add_event(db,cid,'edited','2026-01-01T00:01:00+00:00',actor='bob',summary='y')
    upsert_participants_from_events(db)
    update_participant_display_name(db,'alice','Alice A.')
    compiled=tmp_path/'compiled.json'; export_compiled(db,str(compiled),collection_id=cid)
    j=json.loads(compiled.read_text())
    assert {'meta','global_events','units','sessions','actors','warnings'} <= set(j.keys())
    jsonl=tmp_path/'events.jsonl'; gz=tmp_path/'events.jsonl.gz'; export_jsonl(db,str(jsonl),compact_gz=str(gz),collection_id=cid)
    assert len(jsonl.read_text().strip().splitlines())==2
    assert gz.exists() and gzip.open(gz,'rt').read().strip()
    chunks=export_prompt_chunks(db,str(tmp_path/'chunks'),chunk_size=1,collection_id=cid)
    assert any(p.endswith('.json') for p in chunks)

def test_sessions_viz_diagnostics(tmp_path):
    db=str(tmp_path/'k.db'); cid=ensure_collection(db,str(tmp_path/'src'))
    add_event(db,cid,'edited','2026-01-01T00:00:00+00:00',actor='a')
    add_event(db,cid,'edited','2026-01-01T00:03:00+00:00',actor='a')
    add_event(db,cid,'edited','2026-01-01T00:20:00+00:00',actor='a')
    ss=build_sessions([{'ts':'2026-01-01T00:00:00+00:00','actor':'a'},{'ts':'2026-01-01T00:03:00+00:00','actor':'a'},{'ts':'2026-01-01T00:20:00+00:00','actor':'a'}],idle_minutes=10)
    assert len(ss)==2
    out=tmp_path/'t.html'; build_timeline_html(db,str(out),collection_id=cid); assert out.exists()
    d=run_diagnostics(db); assert d['collections_count']==1 and 'events_by_action' in d
