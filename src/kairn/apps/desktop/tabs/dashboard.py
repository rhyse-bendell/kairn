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

from kairn.core.projects import create_project, load_project, list_projects
from kairn.core.projects.paths import get_default_kairn_home
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
    def __init__(self, projects, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Load Project")
        layout = QVBoxLayout(self)
        self.collaborations = QComboBox()
        for project in projects:
            label = f"{project.get('name') or 'Untitled'} — {project.get('project_root')}"
            self.collaborations.addItem(label, project)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(QLabel("Choose a project / collaboration to load."))
        layout.addWidget(self.collaborations)
        layout.addWidget(buttons)

    def selected_project(self):
        return self.collaborations.currentData()


class DashboardTab(QWidget):
    def __init__(self, state, log, on_project_loaded=None):
        super().__init__()
        self.state = state
        self.log = log
        self.on_project_loaded = on_project_loaded

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

    def refresh_project_display(self):
        summary = self.state.project_display_summary()
        if not summary.get("loaded"):
            self.project_name.setText("No project loaded.")
            self.project_path.setText(f"Project home: {summary.get('project_home')}")
            self.project_collaboration.setText("Start or load a project to begin.")
            self.project_run.setText("")
            self.next_step.setText(summary.get("next_step", "Start or load a project to begin."))
            return
        self.project_name.setText(f"Project: {summary.get('name')}")
        self.project_path.setText(f"Location: {summary.get('project_root')}")
        self.project_collaboration.setText(f"Profile: {summary.get('profile')} | Database: {summary.get('db_path')}")
        rid = self._short_id(summary.get("active_run_id"))
        self.project_run.setText(f"Active run: {rid}" if rid else "")
        self.next_step.setText("Next step: Open Project to add or validate data.")

    def start_new_project(self):
        dialog = NewProjectDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        name, description = dialog.values()
        project = create_project(name or "Untitled Project", description)
        self.state.set_active_project(project)
        append_log(self.log, f"Created project at {project['project_root']}")
        self.refresh_project_display()
        if self.on_project_loaded:
            self.on_project_loaded(project)

    def load_project(self):
        projects = list_projects()
        if not projects:
            home = get_default_kairn_home()
            show_info(self, "No projects", f"No Kairn projects found in {home}. Create a new project first.")
            return
        dialog = LoadProjectDialog(projects, self)
        if dialog.exec() != QDialog.Accepted:
            return
        selected = dialog.selected_project()
        if not selected:
            return
        project = load_project(selected.get("manifest_path") or selected.get("project_root"))
        self.state.set_active_project(project)
        append_log(self.log, f"Loaded project at {project['project_root']}")
        self.refresh_project_display()
        if self.on_project_loaded:
            self.on_project_loaded(project)

    def open_project_files(self):
        path = self.state.active_project_root or self.state.project_home
        open_path(path)
        append_log(self.log, f"Opened project files: {path}")
