from pathlib import Path
from kairn.core.ingestion.service import ingest_root
from kairn.core.storage.repositories import fetchall

def test_text_ingestion(tmp_path):
    root=tmp_path/'root'; root.mkdir(); db=tmp_path/'k.db'
    f=root/'note.txt'; f.write_text('hello')
    ingest_root(str(root),str(db),str(tmp_path/'snap'))
    assert fetchall(str(db),'collections')
    assert fetchall(str(db),'artifacts')
    assert any(e['action']=='created' for e in fetchall(str(db),'events'))
    f.write_text('hello world')
    ingest_root(str(root),str(db),str(tmp_path/'snap'))
    assert any(e['action']=='edited' for e in fetchall(str(db),'events'))
    assert any(d['delta_type']=='text_edit' for d in fetchall(str(db),'deltas'))
