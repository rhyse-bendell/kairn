from kairn.core.ingestion.service import ingest_root
from kairn.core.storage.repositories import fetchall

def test_changelog_and_bracket(tmp_path):
    root=tmp_path/'root'; root.mkdir(); db=tmp_path/'k.db'
    (root/'changelog.txt').write_text('Alice, edited Project Plan\n[EDIT] Bob (• 2:14 PM, Aug 19 (MDT)): updated section')
    ingest_root(str(root),str(db),str(tmp_path/'snap'))
    events=fetchall(str(db),'events')
    assert any(e['actor']=='Alice' and e['mentioned_unit'] for e in events)
    assert any(e['actor']=='Bob' and e['action']=='edit' for e in events)
    assert any('updated section' in d['payload'] for d in fetchall(str(db),'deltas'))
