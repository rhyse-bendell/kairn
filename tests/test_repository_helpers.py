from pathlib import Path
from kairn.core.ingestion.service import ingest_root
from kairn.core.storage import repositories as repo


def test_repository_query_helpers(tmp_path):
    root = tmp_path / 'src'; root.mkdir(); (root / 'a.txt').write_text('hello')
    db = tmp_path / 'kairn.db'
    cid = repo.create_collaboration(str(db), 'C1', 'd')
    out = ingest_root(str(root), str(db), str(tmp_path / 'snaps'), collaboration_id=cid)
    assert repo.count_collaborations(str(db)) == 1
    assert repo.count_collections(str(db), cid) == 1
    assert repo.count_artifacts(str(db), out['collection_id']) >= 1
    assert repo.count_events(str(db), out['collection_id']) >= 1
    assert repo.count_runs(str(db), collaboration_id=cid, collection_id=out['collection_id']) == 1
    assert isinstance(repo.list_artifacts(str(db), out['collection_id']), list)
    assert isinstance(repo.list_events(str(db), out['collection_id']), list)
    assert isinstance(repo.list_warnings(str(db), out['run_id']), list)
    assert repo.get_latest_run(str(db), out['collection_id'])['id'] == out['run_id']
    assert isinstance(repo.list_event_actors(str(db)), list)
    assert isinstance(repo.list_event_actions(str(db)), list)
