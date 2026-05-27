import os
from kairn.core.ingestion.service import ingest_root
from kairn.core.storage.repositories import fetchall

def test_binary_safe_ingestion(tmp_path):
    root=tmp_path/'root'; root.mkdir(); db=tmp_path/'k.db'
    for ext in ['bin','pdf','png','docx','pptx']:
        (root/f'a.{ext}').write_bytes(os.urandom(64))
    ingest_root(str(root),str(db),str(tmp_path/'snap'))
    arts=fetchall(str(db),'artifacts')
    warns=fetchall(str(db),'ingestion_warnings')
    assert len(arts)==5
    assert len(warns)>=1
