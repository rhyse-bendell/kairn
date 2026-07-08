from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from kairn.core.storage import repositories as repo
from ..widgets import (
    append_log,
    dashboard_description_label,
    dashboard_title_label,
    landing_button,
    open_path,
    show_info,
)


class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Start New Project")
        layout = QVBoxLayout(self)
        self.name = QLineEdit()
        self.name.setPlaceholderText("Project / collaboration name")
        self.description = QTextEdit()
        self.description.setPlaceholderText("Optional description")
        self.description.setFixedHeight(90)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(QLabel("Project / collaboration name"))
        layout.addWidget(self.name)
        layout.addWidget(QLabel("Description (optional)"))
        layout.addWidget(self.description)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, str]:
        return self.name.text().strip(), self.description.toPlainText().strip()


class LoadProjectDialog(QDialog):
    def __init__(self, collaborations, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Load Project")
        layout = QVBoxLayout(self)
        self.collaborations = QComboBox()
        for collab in collaborations:
            label = collab.get("name") or "Untitled"
            self.collaborations.addItem(label, collab)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(QLabel("Choose a project / collaboration to load."))
        layout.addWidget(self.collaborations)
        layout.addWidget(buttons)

    def selected_collaboration(self):
        return self.collaborations.currentData()


class DashboardTab(QWidget):
    def __init__(self, state, log):
        super().__init__()
        self.state = state
        self.log = log

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        layout.setSpacing(0)
        layout.setContentsMargins(48, 48, 48, 28)

        content = QFrame()
        content.setMaximumWidth(950)
        content_layout = QVBoxLayout(content)
        content_layout.setAlignment(Qt.AlignTop)
        content_layout.setSpacing(24)
        content_layout.setContentsMargins(0, 0, 0, 0)

        title = dashboard_title_label("Kairn")
        title.setObjectName("dashboardTitle")
        description = dashboard_description_label(
            "Kairn helps you turn workshop files, TLDraw logs, document changelogs, "
            "Drive activity, and other collaboration traces into replayable event timelines, "
            "artifact catalogs, and analysis-ready data products."
        )

        actions = QFrame()
        action_layout = QHBoxLayout(actions)
        action_layout.setContentsMargins(0, 10, 0, 4)
        action_layout.setSpacing(18)
        self.start_button = landing_button("Start New Project")
        self.load_button = landing_button("Load Project")
        self.open_button = landing_button("Open Project Files")
        for button in (self.start_button, self.load_button, self.open_button):
            action_layout.addWidget(button)
        action_layout.addStretch(1)
        self.start_button.clicked.connect(self.start_new_project)
        self.load_button.clicked.connect(self.load_project)
        self.open_button.clicked.connect(self.open_project_files)

        project_box = QGroupBox("Current Project")
        project_box.setMaximumWidth(900)
        project_box.setStyleSheet(
            "QGroupBox { font-size: 16px; font-weight: 700; color: #1f2937; margin-top: 12px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }"
        )
        project_layout = QVBoxLayout(project_box)
        project_layout.setContentsMargins(18, 22, 18, 18)
        project_layout.setSpacing(8)
        self.project_name = QLabel()
        self.project_path = QLabel()
        self.project_collaboration = QLabel()
        self.project_run = QLabel()
        self.next_step = QLabel()
        self.next_step.setWordWrap(True)
        for widget in (
            self.project_name,
            self.project_path,
            self.project_collaboration,
            self.project_run,
            self.next_step,
        ):
            widget.setTextInteractionFlags(Qt.TextSelectableByMouse)
            widget.setStyleSheet("font-size: 15px; color: #374151;")
            project_layout.addWidget(widget)

        content_layout.addWidget(title)
        content_layout.addWidget(description)
        content_layout.addWidget(actions)
        content_layout.addWidget(project_box)
        content_layout.addStretch(1)
        layout.addWidget(content)
        layout.addStretch(1)
        self.refresh_project_display()

    def _short_id(self, value: str | None) -> str:
        return value[:8] if value else ""

    def _active_collaboration(self):
        if not self.state.active_collaboration_id:
            return None
        return repo.get_collaboration(self.state.db_path, self.state.active_collaboration_id)

    def refresh_project_display(self):
        collab = self._active_collaboration()
        if not collab:
            self.project_name.setText("No project loaded")
            self.project_path.setText(f"Workspace: {Path(self.state.workspace_dir).name}")
            self.project_collaboration.setText("")
            self.project_run.setText("")
            self.next_step.setText("Start or load a project to begin.")
            return
        self.project_name.setText(collab.get("name") or "Untitled")
        workspace = collab.get("default_root_path") or self.state.active_root_path or self.state.workspace_dir
        self.project_path.setText(f"Project folder: {workspace}")
        self.project_collaboration.setText(f"Active collaboration: {self._short_id(collab.get('id'))}")
        self.project_run.setText(f"Active run: {self._short_id(self.state.last_run_id)}" if self.state.last_run_id else "")
        self.next_step.setText("Open Sources to add workshop files or folders.")

    def start_new_project(self):
        dialog = NewProjectDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        name, description = dialog.values()
        cid = repo.create_collaboration(self.state.db_path, name or "Untitled", description)
        self.state.active_collaboration_id = cid
        collab = repo.get_collaboration(self.state.db_path, cid)
        self.state.active_collection_id = collab.get("active_collection_id") if collab else None
        append_log(self.log, f"Created project {cid}")
        self.refresh_project_display()

    def load_project(self):
        collaborations = repo.list_collaborations(self.state.db_path)
        if not collaborations:
            show_info(self, "No projects", "No projects have been created yet. Start a new project to begin.")
            return
        dialog = LoadProjectDialog(collaborations, self)
        if dialog.exec() != QDialog.Accepted:
            return
        collab = dialog.selected_collaboration()
        if not collab:
            return
        self.state.active_collaboration_id = collab.get("id")
        self.state.active_collection_id = collab.get("active_collection_id")
        default_root = collab.get("default_root_path")
        if default_root:
            self.state.active_root_path = default_root
        append_log(self.log, f"Loaded project {self.state.active_collaboration_id}")
        self.refresh_project_display()

    def open_project_files(self):
        collab = self._active_collaboration()
        path = None
        if collab:
            path = collab.get("default_root_path") or self.state.active_root_path
        open_path(path or self.state.workspace_dir)
        append_log(self.log, f"Opened project files: {path or self.state.workspace_dir}")
