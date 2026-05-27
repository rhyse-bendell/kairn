from kairn.core.ingestion.service import ingest_root
from kairn.core.maintenance.rebuild_participants import rebuild
from kairn.core.storage.repositories import fetchall

def test_participants(tmp_path):
    root=tmp_path/'root'; root.mkdir(); db=tmp_path/'k.db'
    (root/'changelog.txt').write_text('Alice, created Unit X')
    ingest_root(str(root),str(db),str(tmp_path/'snap'))
    rebuild(str(db))
    p=fetchall(str(db),'participants')
    assert p and p[0]['pid_label'].startswith('PID')
