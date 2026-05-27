from kairn.core.ingestion.service import ingest_root
from kairn.core.storage.repositories import fetchall

def test_nontext_registration(tmp_path):
    root=tmp_path/'root'; root.mkdir(); db=tmp_path/'k.db'
    for n in ['a.pdf','b.docx','c.png','d.pptx','e.bin']:
        (root/n).write_bytes(b'123')
    ingest_root(str(root),str(db),str(tmp_path/'snap'))
    arts=fetchall(str(db),'artifacts')
    assert len(arts)==5
    assert fetchall(str(db),'ingestion_warnings')
