from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt, QDir, QModelIndex
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QFileDialog,
    QFileSystemModel,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTextEdit,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from kairn.core.projects import import_file_to_project, import_folder_to_project, open_project_path, read_source_registry, register_project_source
from kairn.core.sources import detect_compatible_source
from kairn.core.workshop.intake import inspect_workshop_path
from ..widgets import append_log, open_path, set_table_rows
from .agents import AgentsTab
from .artifacts import ArtifactsTab
from .categories import CategoriesTab
from .diagnostics import DiagnosticsTab
from .process_data import ProcessDataTab
from .sources import SourcesTab


class ProjectOverview(QWidget):
    def __init__(self, state, log, parent_tab: "ProjectTab"):
        super().__init__()
        self.state = state
        self.log = log
        self.parent_tab = parent_tab
        self.selected_project_path: str | None = None
        self.project_action_buttons: list[QPushButton] = []
        self.model = QFileSystemModel(self)
        self.model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)

        layout = QVBoxLayout(self)
        top = QSplitter(Qt.Horizontal)
        layout.addWidget(top)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextInteractionFlags(Qt.TextSelectableByMouse)
        left_layout.addWidget(self._summary_box())
        left_layout.addWidget(self._explorer_box(), 1)
        left_layout.addWidget(self._import_box())
        top.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(self._registry_box())
        right_layout.addWidget(self._tiles_box())
        self.inspect_text = QTextEdit()
        self.inspect_text.setReadOnly(True)
        self.inspect_text.setPlaceholderText("Inspect a selected source to see detection details.")
        right_layout.addWidget(self.inspect_text)
        top.addWidget(right)
        top.setSizes([520, 680])
        self.refresh()

    def _summary_box(self):
        box = QGroupBox("Current Project")
        layout = QVBoxLayout(box)
        layout.addWidget(self.summary)
        row = QHBoxLayout()
        for text, fn in [("Open Project Folder", self.open_project_folder), ("Refresh Project", self.refresh), ("Open Manifest", self.open_manifest), ("Open Database Location", self.open_database_location)]:
            button = QPushButton(text); button.clicked.connect(fn); row.addWidget(button)
            if text != "Refresh Project": self.project_action_buttons.append(button)
        layout.addLayout(row)
        return box

    def _explorer_box(self):
        box = QGroupBox("Project Explorer")
        layout = QVBoxLayout(box)
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.clicked.connect(self._selected_index)
        layout.addWidget(self.tree)
        row = QHBoxLayout()
        for text, fn in [("Open Selected", self.open_selected), ("Reveal Selected in Explorer", self.reveal_selected), ("Copy Selected Path", self.copy_selected), ("Refresh Explorer", self.refresh)]:
            button = QPushButton(text); button.clicked.connect(fn); row.addWidget(button)
            if text != "Refresh Explorer": self.project_action_buttons.append(button)
        layout.addLayout(row)
        return box

    def _import_box(self):
        box = QGroupBox("Import / Link Data")
        row = QHBoxLayout(box)
        for text, fn in [("Import File(s)", self.import_files), ("Import Folder", self.import_folder), ("Link External Source", self.link_external_source), ("Inspect Selected Source", self.inspect_selected_source)]:
            button = QPushButton(text); button.clicked.connect(fn); row.addWidget(button); self.project_action_buttons.append(button)
        return box

    def _registry_box(self):
        box = QGroupBox("Source Registry Summary")
        layout = QVBoxLayout(box)
        self.registry_table = QTableWidget()
        layout.addWidget(self.registry_table)
        row = QHBoxLayout()
        for text, fn in [("Refresh Sources", self.refresh_registry), ("Inspect Selected Source", self.inspect_registry_selection), ("Open Source Location", self.open_registry_selection)]:
            button = QPushButton(text); button.clicked.connect(fn); row.addWidget(button)
            if text != "Refresh Sources": self.project_action_buttons.append(button)
        layout.addLayout(row)
        return box

    def _tiles_box(self):
        box = QGroupBox("Workflow Tiles")
        row = QHBoxLayout(box)
        for name in ["Sources / Intake", "Artifacts / Catalog", "Parsed Data", "Agents", "Categories / Metadata", "Diagnostics / Warnings", "Replay", "Analysis", "Exports"]:
            button = QPushButton(name); button.clicked.connect(lambda _=False, n=name: self.parent_tab.navigate_tile(n)); row.addWidget(button)
        return box

    def _project(self):
        if not self.state.has_active_project():
            return None
        return {"project_root": self.state.active_project_root, "manifest_path": self.state.active_project_manifest_path, "db_path": self.state.db_path}

    def _default_dir(self) -> str:
        base = getattr(self.state, "last_import_dir", None) or self.state.active_project_root or self.state.project_home
        if self.state.active_project_root:
            original = Path(self.state.active_project_root) / "data" / "original"
            return str(original if original.exists() else Path(self.state.active_project_root))
        return str(base)

    def _require_project(self) -> bool:
        if self.state.has_active_project():
            return True
        QMessageBox.information(self, "No project loaded", "No project loaded. Start or load a project from Dashboard.")
        return False

    def set_project_actions_enabled(self, enabled: bool) -> None:
        for button in self.project_action_buttons:
            button.setEnabled(enabled)

    def _show_empty_state(self) -> None:
        self.selected_project_path = None
        self.summary.setText("No project loaded. Start or load a project from Dashboard.\n\nProject files will appear here after you start or load a project.")
        self.tree.setEnabled(False)
        self.tree.setRootIndex(QModelIndex())
        self.set_project_actions_enabled(False)
        self.inspect_text.setText("Inspect a selected source to see detection details.")
        self.refresh_registry()

    def refresh(self):
        if not self.state.has_active_project():
            self._show_empty_state()
            return
        root = Path(self.state.active_project_root)
        manifest = Path(self.state.active_project_manifest_path) if self.state.active_project_manifest_path else root / "kairn_project.json"
        if not root.exists() or not root.is_dir() or not manifest.exists():
            self.summary.setText("\n".join([
                "Active project folder is missing or invalid.",
                f"Project root: {root}",
                f"Manifest: {manifest}",
                "Reload or recreate the project from Dashboard.",
            ]))
            self.tree.setEnabled(False)
            self.tree.setRootIndex(QModelIndex())
            self.set_project_actions_enabled(False)
            self.refresh_registry()
            return
        self.tree.setEnabled(True)
        self.set_project_actions_enabled(True)
        self.summary.setText("\n".join([
            f"Project name: {self.state.active_project_name}", f"Project root: {root}", f"Active profile: {self.state.active_profile}", f"Database path: {self.state.db_path}", f"Active collaboration id: {self._short(self.state.active_collaboration_id)}", f"Active run id: {self._short(self.state.last_run_id)}",
        ]))
        self.model.setRootPath(str(root)); self.tree.setRootIndex(self.model.index(str(root)))
        self.refresh_registry()

    def _short(self, value):
        return value[:8] if value else "—"

    def _selected_index(self, index):
        path = self.model.filePath(index); self.selected_project_path = path; self.state.selected_project_path = path; self.state.selected_project_file = path if Path(path).is_file() else None

    def open_project_folder(self):
        if self._require_project(): open_path(self.state.active_project_root)
    def open_manifest(self):
        if self._require_project(): open_path(self.state.active_project_manifest_path)
    def open_database_location(self):
        if self._require_project(): open_path(str(Path(self.state.db_path).parent))
    def open_selected(self):
        if self.selected_project_path: open_path(self.selected_project_path)
    def reveal_selected(self):
        if self.selected_project_path: open_project_path(Path(self.selected_project_path).parent if Path(self.selected_project_path).is_file() else self.selected_project_path)
    def copy_selected(self):
        if self.selected_project_path: QGuiApplication.clipboard().setText(self.selected_project_path); append_log(self.log, f"Copied path: {self.selected_project_path}")

    def import_files(self):
        if not self._require_project(): return
        files = QFileDialog.getOpenFileNames(self, "Import file(s)", self._default_dir(), "All Files (*)")[0]
        for file_path in files:
            rec = import_file_to_project(self._project(), file_path, copy=True, metadata={"detection": detect_compatible_source(file_path)})
            self.state.last_import_dir = str(Path(file_path).parent); append_log(self.log, f"Imported source {rec['source_id']}: {file_path}")
        self.refresh()

    def import_folder(self):
        if not self._require_project(): return
        folder = QFileDialog.getExistingDirectory(self, "Import folder", self._default_dir())
        if folder:
            rec = import_folder_to_project(self._project(), folder, copy=True, metadata={"detection": detect_compatible_source(folder)})
            self.state.last_import_dir = str(Path(folder).parent); append_log(self.log, f"Imported folder source {rec['source_id']}: {folder}"); self.refresh()

    def link_external_source(self):
        if not self._require_project(): return
        path = QFileDialog.getOpenFileName(self, "Link external file", self._default_dir(), "All Files (*)")[0] or QFileDialog.getExistingDirectory(self, "Link external folder", self._default_dir())
        if path:
            rec = register_project_source(self._project(), path, copy_into_project=False, metadata={"detection": detect_compatible_source(path)})
            self.state.last_import_dir = str(Path(path).parent); append_log(self.log, f"Linked source {rec['source_id']}: {path}"); self.refresh()

    def _current_registry_record(self):
        row = self.registry_table.currentRow()
        if row < 0: return None
        sources = read_source_registry(self._project()).get("sources", []) if self._project() else []
        return sources[row] if row < len(sources) else None

    def inspect_selected_source(self):
        path = self.selected_project_path
        if not path: return
        self._inspect_path(path)

    def inspect_registry_selection(self):
        rec = self._current_registry_record()
        if rec: self._inspect_path(rec.get("project_path") or rec.get("original_path"))

    def _inspect_path(self, path):
        result = inspect_workshop_path(path) if path else {}
        self.inspect_text.setText(json.dumps(result, indent=2, default=str))
        append_log(self.log, f"Inspected source: {path}")

    def open_registry_selection(self):
        rec = self._current_registry_record()
        if rec: open_path(rec.get("project_path") or rec.get("original_path"))

    def refresh_registry(self):
        rows = []
        if self.state.has_active_project():
            for rec in read_source_registry(self._project()).get("sources", []):
                det = (rec.get("metadata") or {}).get("detection") or {}
                rows.append({"source_id": rec.get("source_id"), "source_type": rec.get("source_type") or det.get("source_type"), "copied_into_project": rec.get("copied_into_project"), "original_path": rec.get("original_path"), "project_path": rec.get("project_path"), "added_at": rec.get("added_at"), "detection_confidence": det.get("confidence")})
        set_table_rows(self.registry_table, rows, ["source_id", "source_type", "copied_into_project", "original_path", "project_path", "added_at", "detection_confidence"])


class ProjectTab(QWidget):
    SUBVIEWS = ["Overview", "Sources / Intake", "Artifacts / Catalog", "Parsed Data", "Agents", "Categories / Metadata", "Diagnostics / Warnings"]

    def __init__(self, state, log, navigate_to=None):
        super().__init__(); self.state = state; self.log = log; self.navigate_to = navigate_to
        layout = QHBoxLayout(self); splitter = QSplitter(Qt.Horizontal); layout.addWidget(splitter)
        left = QFrame(); left_layout = QVBoxLayout(left)
        self.mini = QLabel(); self.mini.setWordWrap(True); left_layout.addWidget(self.mini)
        self.nav = QListWidget(); left_layout.addWidget(self.nav, 1)
        self.stack = QStackedWidget()
        self.overview = ProjectOverview(state, log, self)
        widgets = [self.overview, SourcesTab(state, log), ArtifactsTab(state, log), ProcessDataTab(state, log), AgentsTab(state, log), CategoriesTab(state, log), DiagnosticsTab(state, log)]
        for name, widget in zip(self.SUBVIEWS, widgets):
            self.nav.addItem(QListWidgetItem(name)); self.stack.addWidget(widget)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex); self.nav.currentRowChanged.connect(lambda _i: self.refresh())
        self.nav.setCurrentRow(0)
        splitter.addWidget(left); splitter.addWidget(self.stack); splitter.setSizes([260, 940])
        self.refresh()

    def refresh(self):
        if self.state.has_active_project(): self.mini.setText(f"Project: {self.state.active_project_name}\n{self.state.active_project_root}")
        else: self.mini.setText("No project loaded.\nStart or load a project from Dashboard.")
        self.overview.refresh()
        current = self.stack.currentWidget()
        current_refresh = getattr(current, "refresh", None)
        if current is not self.overview and callable(current_refresh):
            current_refresh()

    def switch_to_subview(self, name: str) -> bool:
        if name in self.SUBVIEWS:
            self.nav.setCurrentRow(self.SUBVIEWS.index(name)); return True
        return False

    def navigate_tile(self, name: str) -> None:
        if name in self.SUBVIEWS:
            self.switch_to_subview(name); return
        if self.navigate_to and self.navigate_to(name): return
        append_log(self.log, f"Open the {name} tab to continue.")
