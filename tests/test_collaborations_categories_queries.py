from kairn.core.storage import repositories as repo
from kairn.core.ingestion.service import ingest_root

def test_collaboration_and_default_categories(tmp_path):
    db=tmp_path/'k.db'
    cid=repo.create_collaboration(str(db),'Team A','desc')
    assert repo.get_collaboration(str(db),cid)['name']=='Team A'
    cats=repo.list_categories(str(db),cid)
    assert len(cats)>=15

def test_category_assignment_and_counts(tmp_path):
    root=tmp_path/'root'; root.mkdir(); (root/'a.txt').write_text('hello')
    db=tmp_path/'k.db'; cid=repo.create_collaboration(str(db),'C')
    out=ingest_root(str(root),str(db),str(tmp_path/'snap'), collaboration_id=cid)
    arts=repo.list_artifacts(str(db), out['collection_id'])
    custom=repo.create_category(str(db),cid,'Custom')
    repo.assign_category_to_artifact(str(db),arts[0]['id'],custom)
    assert repo.count_artifacts(str(db), out['collection_id'])==1
    assert repo.count_events(str(db), out['collection_id'])>=1
    assert repo.count_runs(str(db), cid)>=1

def test_gui_importable():
    import kairn.apps.desktop.main  # noqa: F401
