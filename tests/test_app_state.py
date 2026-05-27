from pathlib import Path
from kairn.apps.desktop.state import AppState


def test_app_state_workspace(tmp_path):
    ws = tmp_path / 'kairn_workspace'
    st = AppState(
        workspace_dir=str(ws),
        db_path=str(ws / 'kairn.db'),
        snapshots_dir=str(ws / 'snapshots'),
        outputs_dir=str(ws / 'outputs'),
    )
    assert Path(st.workspace_dir).exists()
    assert Path(st.snapshots_dir).exists()
    assert Path(st.outputs_dir).exists()
    assert st.db_path.endswith('kairn.db')


def test_set_active_run_paths(tmp_path):
    st = AppState(workspace_dir=str(tmp_path), db_path=str(tmp_path / 'kairn.db'))
    st.set_active_run_paths({
        'run_dir': 'r', 'json_dir': 'j', 'csv_dir': 'c', 'viz_dir': 'v', 'prompt_dir': 'p',
        'reports_dir': 'rep', 'chunks_dir': 'ch', 'meta_path': 'm',
    })
    assert st.active_run_dir == 'r'
    assert st.active_run_reports_dir == 'rep'
    assert st.active_run_chunks_dir == 'ch'
    assert st.active_run_meta_path == 'm'
