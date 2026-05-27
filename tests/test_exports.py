from kairn.core.ingestion.service import ingest_root
from kairn.core.export.compiled_json import export_compiled
from kairn.core.export.jsonl import export_jsonl
from kairn.core.export.prompt_chunks import export_prompt_chunks
import gzip
import json


def test_exports(tmp_path):
    root = tmp_path / 'root'; root.mkdir(); db = tmp_path / 'k.db'
    (root / 'note.txt').write_text('abc')
    ingest_root(str(root), str(db), str(tmp_path / 'snap'))
    c = root / 'compiled.json'; j = root / 'events.jsonl'; gz = root / 'events.compact.jsonl.gz'
    export_compiled(str(db), str(c)); export_jsonl(str(db), str(j), str(gz))
    chunk_paths = export_prompt_chunks(str(db), str(root / 'chunks'), chunk_size=10)
    data = json.loads(c.read_text())
    assert c.exists() and j.exists() and gz.exists() and chunk_paths
    for key in ('meta', 'global_events', 'units', 'actors', 'sessions', 'indicators_summary', 'deltas_summary'):
        assert key in data
    evt = json.loads(j.read_text().splitlines()[0])
    assert 'actor_label' in evt and 'artifact_rel_path' in evt and 'collection_id' in evt
    with gzip.open(gz, 'rt', encoding='utf-8') as f:
        cev = json.loads(f.readline())
    assert set(('event_id', 'ts', 'action', 'actor', 'unit')).issubset(cev)
    chunk = json.loads((root / 'chunks' / 'prompt_chunk_001.json').read_text())
    assert 'chunk_meta' in chunk and 'actor_map' in chunk and 'events' in chunk
