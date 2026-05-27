from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AppState:
    workspace_dir: str = "./kairn_workspace"
    db_path: str = "./kairn_workspace/kairn.db"
    active_collaboration_id: str | None = None
    active_collection_id: str | None = None
    active_root_path: str | None = None
    last_run_id: str | None = None
    last_output_dir: str | None = None
    last_visualization_path: str | None = None
    last_metrics_path: str | None = None
    last_timeline_csv_path: str | None = None
    snapshots_dir: str = field(default="./kairn_workspace/snapshots")
    outputs_dir: str = field(default="./kairn_workspace/outputs")
    active_run_dir: str | None = None
    active_run_json_dir: str | None = None
    active_run_csv_dir: str | None = None
    active_run_viz_dir: str | None = None
    active_run_prompt_dir: str | None = None

    def __post_init__(self) -> None:
        workspace = Path(self.workspace_dir)
        workspace.mkdir(parents=True, exist_ok=True)
        Path(self.snapshots_dir).mkdir(parents=True, exist_ok=True)
        Path(self.outputs_dir).mkdir(parents=True, exist_ok=True)
        self.workspace_dir = str(workspace)
        self.db_path = str(Path(self.db_path))
        self.snapshots_dir = str(Path(self.snapshots_dir))
        self.outputs_dir = str(Path(self.outputs_dir))
        self.last_output_dir = self.outputs_dir
