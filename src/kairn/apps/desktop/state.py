from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from kairn.core.projects.paths import get_default_kairn_home


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
    active_profile_name: str = "problem_framing_workshop"
    last_artifact_catalog_paths: dict | None = None
    snapshots_dir: str = field(default="./kairn_workspace/snapshots")
    outputs_dir: str = field(default="./kairn_workspace/outputs")
    active_run_dir: str | None = None
    active_run_json_dir: str | None = None
    active_run_csv_dir: str | None = None
    active_run_viz_dir: str | None = None
    active_run_prompt_dir: str | None = None
    active_run_reports_dir: str | None = None
    active_run_chunks_dir: str | None = None
    active_run_meta_path: str | None = None
    active_project_id: str | None = None
    active_project_name: str | None = None
    active_project_root: str | None = None
    active_project_manifest_path: str | None = None
    active_project_settings_path: str | None = None
    active_profile: str = "problem_framing_workshop"
    project_home: str = field(default_factory=lambda: str(get_default_kairn_home()))
    source_registry_path: str | None = None
    participant_map_path: str | None = None

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

    def set_active_project(self, project: dict) -> None:
        root = Path(project["project_root"])
        self.active_project_id = project.get("project_id")
        self.active_project_name = project.get("name")
        self.active_project_root = str(root)
        self.active_project_manifest_path = project.get("manifest_path") or str(root / "kairn_project.json")
        self.active_project_settings_path = str(root / "settings" / "project_settings.json")
        self.active_profile = project.get("active_profile") or "problem_framing_workshop"
        self.active_profile_name = self.active_profile
        self.project_home = str(root.parent)
        self.source_registry_path = str(root / "settings" / "source_registry.json")
        self.participant_map_path = str(root / "settings" / "participant_map.json")
        self.db_path = project.get("db_path") or str(root / "kairn.db")
        self.workspace_dir = str(root)
        self.snapshots_dir = str(root / "data" / "staging" / "snapshots")
        self.outputs_dir = str(root / "runs")
        Path(self.snapshots_dir).mkdir(parents=True, exist_ok=True)
        Path(self.outputs_dir).mkdir(parents=True, exist_ok=True)
        self.active_collaboration_id = project.get("active_collaboration_id")
        self.active_collection_id = project.get("active_collection_id")
        self.last_run_id = project.get("active_run_id")
        self.active_root_path = str(root)
        self.last_output_dir = self.outputs_dir

    def clear_active_project(self) -> None:
        self.active_project_id = self.active_project_name = self.active_project_root = None
        self.active_project_manifest_path = self.active_project_settings_path = None
        self.source_registry_path = self.participant_map_path = None
        self.active_collaboration_id = self.active_collection_id = None
        self.last_run_id = None

    def has_active_project(self) -> bool:
        return bool(self.active_project_root and self.active_project_manifest_path)

    def project_display_summary(self) -> dict:
        if not self.has_active_project():
            return {"loaded": False, "project_home": self.project_home, "next_step": "Start or load a project to begin."}
        return {"loaded": True, "name": self.active_project_name, "project_root": self.active_project_root, "profile": self.active_profile, "db_path": self.db_path, "active_collaboration_id": self.active_collaboration_id, "active_run_id": self.last_run_id, "next_step": "Open Sources to add data."}

    def set_active_run_paths(self, paths: dict) -> None:
        self.active_run_dir = paths.get("run_dir")
        self.active_run_json_dir = paths.get("json_dir")
        self.active_run_csv_dir = paths.get("csv_dir")
        self.active_run_viz_dir = paths.get("viz_dir")
        self.active_run_prompt_dir = paths.get("prompt_dir")
        self.active_run_reports_dir = paths.get("reports_dir")
        self.active_run_chunks_dir = paths.get("chunks_dir")
        self.active_run_meta_path = paths.get("meta_path")
        self.last_run_id = paths.get("run_id") or self.last_run_id
        self.last_output_dir = self.active_run_dir or self.outputs_dir
