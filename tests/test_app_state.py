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
