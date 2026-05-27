from kairn.core.ingestion.service import ingest_root
from kairn.core.analysis.metrics import compute_metrics

def test_metrics(tmp_path):
    root=tmp_path/'root'; root.mkdir(); db=tmp_path/'k.db'
    (root/'changelog.txt').write_text('Alice, edited Plan')
    ingest_root(str(root),str(db),str(tmp_path/'snap'))
    out=root/'metrics.csv'; compute_metrics(str(db),str(out))
    assert out.exists() and 'actor' in out.read_text()
