from kairn.core.ingestion.service import ingest_root
from kairn.core.export.compiled_json import export_compiled
from kairn.core.export.jsonl import export_jsonl
import json

def test_exports(tmp_path):
    root=tmp_path/'root'; root.mkdir(); db=tmp_path/'k.db'
    (root/'note.txt').write_text('abc')
    ingest_root(str(root),str(db),str(tmp_path/'snap'))
    c=root/'compiled.json'; j=root/'events.jsonl'
    export_compiled(str(db),str(c)); export_jsonl(str(db),str(j),str(root/'events.compact.jsonl.gz'))
    data=json.loads(c.read_text())
    assert c.exists() and j.exists()
    assert 'meta' in data and 'global_events' in data and 'units' in data
