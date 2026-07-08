from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt, QDir, QModelIndex
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFileSystemModel,
    QFrame,
    QGroupBox,
    QGridLayout,
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
from ..widgets import append_log, muted_help_label, open_path, page_header, primary_cta_button, primary_action_button, secondary_button, secondary_action_button, section_header, set_table_rows, show_info, status_badge, workflow_card, workflow_step_label
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
        self.header = page_header("Project Hub", "Manage the active Kairn project, import source files into the project workspace, inspect registered sources, and jump to the main workflows.", "Import Data Into Project")
        layout.addWidget(self.header)
        layout.addWidget(self._workflow_strip())
        layout.addWidget(self._primary_import_card())
        self.next_step = muted_help_label("")
        layout.addWidget(self.next_step)
        actions = QHBoxLayout()
        self.import_data_button = primary_cta_button("Import Data Into Project")
        self.import_data_button.clicked.connect(self.import_data_into_project)
        actions.addWidget(self.import_data_button)
        for text, fn in [("Open Project Folder", self.open_project_folder), ("Refresh Project", self.refresh)]:
            b = secondary_action_button(text); b.clicked.connect(fn); actions.addWidget(b); self.project_action_buttons.append(b)
        actions.addStretch(1)
        layout.addLayout(actions)
        top = QSplitter(Qt.Horizontal)
        layout.addWidget(top)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextInteractionFlags(Qt.TextSelectableByMouse)
        left_layout.addWidget(self._summary_box())
        left_layout.addWidget(self._explorer_box(), 1)
        left_layout.addWidget(self._selected_item_box())
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

    def _workflow_strip(self):
        box = QGroupBox("Workflow")
        layout = QVBoxLayout(box)
        layout.addWidget(muted_help_label("Suggested workflow: import data, inspect/parse it, review file history, replay the timeline, then analyze or export."))
        self.workflow_row = QHBoxLayout(); self.workflow_steps = []
        layout.addLayout(self.workflow_row)
        self._render_workflow_steps(0)
        return box

    def _primary_import_card(self):
        box = QGroupBox("Import Data Into Project")
        box.setStyleSheet("QGroupBox { background: #eff6ff; border: 2px solid #93c5fd; border-radius: 14px; margin-top: 10px; padding: 12px; font-weight: 800; } QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; }")
        layout = QVBoxLayout(box)
        layout.addWidget(muted_help_label("Copy a folder or files into this Kairn project so they live under data/original and can be inspected, parsed, replayed, and exported."))
        layout.addWidget(muted_help_label("Import: Copies selected data into <ProjectRoot>/data/original/.\nLink: Keeps files where they are and records the original path."))
        row = QHBoxLayout()
        self.import_folder_button = primary_cta_button("Import Folder")
        self.import_files_button = primary_cta_button("Import File(s)")
        self.link_external_button = secondary_button("Link External Source (does not copy)")
        for button, fn in [(self.import_folder_button, self.import_folder), (self.import_files_button, self.import_files), (self.link_external_button, self.link_external_source)]:
            button.clicked.connect(fn); row.addWidget(button); self.project_action_buttons.append(button)
        layout.addLayout(row)
        return box

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
        self.project_files_label = muted_help_label("Project files will appear here after you start or load a project.")
        layout.addWidget(self.project_files_label)
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

    def _selected_item_box(self):
        box = QGroupBox("Selected Project Item")
        layout = QVBoxLayout(box)
        self.selected_item_details = muted_help_label("Select a file or folder in the Project Explorer to see available actions.")
        layout.addWidget(self.selected_item_details)
        self.selected_item_badge_row = QHBoxLayout(); layout.addLayout(self.selected_item_badge_row)
        row = QHBoxLayout()
        for text, fn in [("Inspect Source", self.inspect_selected_source), ("Show History", self.show_selected_history), ("Open", self.open_selected), ("Reveal in Explorer", self.reveal_selected), ("Copy Path", self.copy_selected)]:
            button = secondary_action_button(text); button.clicked.connect(fn); row.addWidget(button); self.project_action_buttons.append(button)
        layout.addLayout(row)
        return box

    def _import_box(self):
        box = QGroupBox("Import / Link Data")
        layout = QVBoxLayout(box)
        layout.addWidget(muted_help_label("Import Folder and Import File(s) copy data into this project under data/original. Link External Source does not copy files into the project. Kairn tracks the original path."))
        row = QHBoxLayout()
        for text, fn in [("Import Folder", self.import_folder), ("Import File(s)", self.import_files), ("Link External Source", self.link_external_source), ("Inspect Selected Source", self.inspect_selected_source)]:
            button = secondary_action_button(text); button.clicked.connect(fn); row.addWidget(button); self.project_action_buttons.append(button)
        layout.addLayout(row)
        return box

    def _registry_box(self):
        box = QGroupBox("Source Registry Summary")
        layout = QVBoxLayout(box)
        layout.addWidget(muted_help_label("Registered sources are files or folders Kairn knows about. Imported sources are copied into this project; linked sources remain at their original location."))
        self.registry_table = QTableWidget()
        layout.addWidget(self.registry_table)
        row = QHBoxLayout()
        for text, fn in [("Refresh Sources", self.refresh_registry), ("Inspect Selected Source", self.inspect_registry_selection), ("Open Source Location", self.open_registry_selection)]:
            button = QPushButton(text); button.clicked.connect(fn); row.addWidget(button)
            if text != "Refresh Sources": self.project_action_buttons.append(button)
        layout.addLayout(row)
        return box

    def _tiles_box(self):
        box = QGroupBox("Workflow Cards")
        grid = QGridLayout(box)
        cards = [
            ("Sources / Intake", "Inspect imported sources, extract archives, build catalogs, and parse known workshop files.", "Open Sources / Intake"),
            ("Files & History", "Select a cataloged file or artifact and view its event history.", "Open Files & History"),
            ("Parsed Data", "Inspect TLDraw, Drive, document, and unified event tables.", "Open Parsed Data"),
            ("Replay", "Scrub through the parsed collaboration timeline.", "Open Replay"),
            ("Analysis", "Compute descriptive metrics and trace-based indicators.", "Open Analysis"),
            ("Exports", "Write data products, reports, timelines, and replay packages.", "Open Exports"),
        ]
        for i, (name, desc, button_text) in enumerate(cards):
            card = workflow_card(name, desc, button_text)
            btn = card.findChild(QPushButton)
            if btn: btn.clicked.connect(lambda _=False, n=name: self.parent_tab.navigate_tile(n))
            grid.addWidget(card, i // 2, i % 2)
        return box

    def _project(self):
        if not self.state.has_active_project():
            return None
        return {"project_root": self.state.active_project_root, "manifest_path": self.state.active_project_manifest_path, "db_path": self.state.db_path}

    def _default_dir(self) -> str:
        base = getattr(self.state, "last_import_dir", None)
        if base:
            return str(base)
        docs = Path.home() / "Documents"
        if docs.exists():
            return str(docs)
        return str(self.state.project_home or Path.home())

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
        self.next_step.setText("Next step: Start or load a project from Dashboard.")
        self.project_files_label.setText("Project files will appear here after you start or load a project.")
        self.tree.setEnabled(False)
        self.tree.setRootIndex(QModelIndex())
        self.set_project_actions_enabled(False)
        self.inspect_text.setText("Inspect a selected source to see detection details.")
        self.set_selected_project_path(None)
        self.refresh_registry()
        self._update_workflow_steps(0)

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
        self.project_files_label.setText(f"Project files:\n{root}")
        source_count = len(read_source_registry(self._project()).get("sources", []))
        empty_checklist = ("No sources imported yet.\n\n"
            "Start here:\n"
            "1. Click Import Folder or Import File(s).\n"
            "2. Confirm the item appears under data/original.\n"
            "3. Open Sources / Intake to inspect and parse it.\n"
            "4. Open Files & History to review artifact events.\n"
            "5. Open Replay to inspect the timeline.")
        self.next_step.setText(empty_checklist if source_count == 0 else "Registered sources found. Next: open Sources / Intake to inspect and parse them.")
        self._update_workflow_steps(source_count)
        self.summary.setText("\n".join([
            f"Project name: {self.state.active_project_name}", f"Project root: {root}", f"Active profile: {self.state.active_profile}", f"Database path: {self.state.db_path}", f"Active collaboration id: {self._short(self.state.active_collaboration_id)}", f"Active run id: {self._short(self.state.last_run_id)}",
        ]))
        self.model.setRootPath(str(root)); self.tree.setRootIndex(self.model.index(str(root)))
        self.refresh_registry()

    def _short(self, value):
        return value[:8] if value else "—"

    def _selected_index(self, index):
        self.set_selected_project_path(self.model.filePath(index))

    def set_selected_project_path(self, path: str | None) -> None:
        self.selected_project_path = path
        self.state.selected_project_path = path
        self.state.selected_project_file = path if path and Path(path).is_file() else None
        if not hasattr(self, "selected_item_details"):
            return
        if not path:
            self.selected_item_details.setText("Select a file or folder in the Project Explorer to see available actions.")
            return
        p = Path(path); root = Path(self.state.active_project_root) if self.state.has_active_project() else None
        rel = None
        if root:
            try: rel = p.relative_to(root)
            except ValueError: rel = None
        details = [f"Relative path: {rel if rel else 'outside project'}", f"Full path: {p}", f"Type: {'folder' if p.is_dir() else 'file'}"]
        if rel and str(rel).startswith('data/original'):
            details.append("Status: Imported project data")
        if p.name in {"kairn_project.json", "kairn.db"}:
            details.append("Status: Project infrastructure file")
        self.selected_item_details.setText("\n".join(details))

    def _render_workflow_steps(self, active: int, complete_until: int = 0) -> None:
        while getattr(self, 'workflow_row', None) and self.workflow_row.count():
            item = self.workflow_row.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.workflow_steps = []
        for number, title in [(1, "Import"), (2, "Inspect / Parse"), (3, "Review History"), (4, "Replay"), (5, "Analyze / Export")]:
            step = workflow_step_label(number, title, active=(number == active), complete=(number <= complete_until))
            self.workflow_steps.append(step); self.workflow_row.addWidget(step)

    def _update_workflow_steps(self, source_count: int) -> None:
        try:
            from kairn.core.storage import repositories as repo
            artifact_count = len(repo.list_artifacts(self.state.db_path, self.state.active_collection_id)) if self.state.has_active_project() else 0
        except Exception:
            artifact_count = 0
        if not self.state.has_active_project(): self._render_workflow_steps(0); return
        if source_count == 0: self._render_workflow_steps(1, 0); return
        if artifact_count == 0: self._render_workflow_steps(2, 1); return
        self._render_workflow_steps(3, 2)

    def show_selected_history(self):
        if not self.selected_project_path:
            append_log(self.log, "Select a project file before opening Files & History."); return
        matched = False
        if hasattr(self.parent_tab, 'artifacts_tab') and hasattr(self.parent_tab.artifacts_tab, 'select_artifact_by_path'):
            self.parent_tab.switch_to_subview("Files & History")
            matched = self.parent_tab.artifacts_tab.select_artifact_by_path(self.selected_project_path)
        else:
            self.parent_tab.switch_to_subview("Files & History")
        if not matched:
            append_log(self.log, "Open Files & History and select the matching artifact after building the catalog.")

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

    def import_data_into_project(self):
        if not self._require_project(): return
        dialog = QDialog(self)
        dialog.setWindowTitle("Import Data Into Project")
        layout = QVBoxLayout(dialog)
        layout.addWidget(page_header("Import Data Into Project", "Choose how Kairn should add data:\n- Import Folder: copy an entire folder into this project under data/original.\n- Import File(s): copy selected files into this project under data/original.\n- Link External Source: keep files where they are and register their location.", "Import Folder"))
        layout.addWidget(muted_help_label("Recommended: Import Folder. This copies a workshop dataset folder into Kairn’s project environment."))
        for text, fn in [("Import Folder", self.import_folder), ("Import File(s)", self.import_files), ("Link External Source", self.link_external_source)]:
            b = primary_action_button(text) if text == "Import Folder" else secondary_action_button(text)
            b.clicked.connect(dialog.accept)
            b.clicked.connect(fn)
            layout.addWidget(b)
        dialog.exec()

    def import_files(self):
        if not self._require_project(): return
        files = QFileDialog.getOpenFileNames(self, "Import file(s)", self._default_dir(), "All Files (*)")[0]
        imported_paths = []
        for file_path in files:
            rec = import_file_to_project(self._project(), file_path, copy=True, metadata={"detection": detect_compatible_source(file_path)})
            imported_paths.append(str(rec.get("project_path")))
            self.state.last_import_dir = str(Path(file_path).parent); append_log(self.log, f"Imported file into project: {file_path} -> {rec.get('project_path')}")
        self.refresh()
        if imported_paths:
            show_info(self, "Imported into project", "Imported into project:\n" + "\n".join(imported_paths))

    def import_folder(self):
        if not self._require_project(): return
        folder = QFileDialog.getExistingDirectory(self, "Import folder", self._default_dir())
        if folder:
            rec = import_folder_to_project(self._project(), folder, copy=True, metadata={"detection": detect_compatible_source(folder)})
            self.state.last_import_dir = str(Path(folder).parent); append_log(self.log, f"Imported folder into project: {folder} -> {rec.get('project_path')}"); self.refresh(); show_info(self, "Imported into project", f"Imported into project:\n{rec.get('project_path')}")

    def link_external_source(self):
        if not self._require_project(): return
        path = QFileDialog.getOpenFileName(self, "Link external file", self._default_dir(), "All Files (*)")[0] or QFileDialog.getExistingDirectory(self, "Link external folder", self._default_dir())
        if path:
            rec = register_project_source(self._project(), path, copy_into_project=False, metadata={"detection": detect_compatible_source(path)})
            self.state.last_import_dir = str(Path(path).parent); append_log(self.log, f"Linked external source without copying: {path}"); self.refresh()

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
                rows.append({"Source ID": rec.get("source_id"), "Type": rec.get("source_type") or det.get("source_type"), "Status": "COPIED" if rec.get("copied_into_project") else "LINKED", "Original Path": rec.get("original_path"), "Project Path": rec.get("project_path"), "Added": rec.get("added_at"), "Confidence": det.get("confidence")})
        set_table_rows(self.registry_table, rows, ["Source ID", "Type", "Status", "Original Path", "Project Path", "Added", "Confidence"])


class ProjectTab(QWidget):
    SUBVIEWS = ["Overview", "Sources / Intake", "Files & History", "Parsed Data", "Agents", "Categories / Metadata", "Diagnostics / Warnings"]

    def __init__(self, state, log, navigate_to=None):
        super().__init__(); self.state = state; self.log = log; self.navigate_to = navigate_to
        layout = QHBoxLayout(self); splitter = QSplitter(Qt.Horizontal); layout.addWidget(splitter)
        left = QFrame(); left_layout = QVBoxLayout(left)
        self.mini = QLabel(); self.mini.setWordWrap(True); left_layout.addWidget(self.mini)
        left_layout.addWidget(section_header("Project Sections", "Choose a project workspace view."))
        self.nav = QListWidget(); left_layout.addWidget(self.nav, 1)
        self.stack = QStackedWidget()
        self.overview = ProjectOverview(state, log, self)
        self.sources_tab = SourcesTab(state, log)
        self.artifacts_tab = ArtifactsTab(state, log)
        self.process_data_tab = ProcessDataTab(state, log)
        self.agents_tab = AgentsTab(state, log)
        self.categories_tab = CategoriesTab(state, log)
        self.diagnostics_tab = DiagnosticsTab(state, log)
        widgets = [self.overview, self.sources_tab, self.artifacts_tab, self.process_data_tab, self.agents_tab, self.categories_tab, self.diagnostics_tab]
        for name, widget in zip(self.SUBVIEWS, widgets):
            item = QListWidgetItem(name); item.setToolTip(self._subview_tooltip(name)); self.nav.addItem(item); self.stack.addWidget(widget)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex); self.nav.currentRowChanged.connect(lambda _i: self.refresh())
        self.nav.setCurrentRow(0)
        splitter.addWidget(left); splitter.addWidget(self.stack); splitter.setSizes([260, 940])
        self.refresh()

    def _subview_tooltip(self, name: str) -> str:
        return {"Overview": "project files, imports, registry, workflow shortcuts", "Sources / Intake": "inspect sources, extract archives, build catalogs, parse known files", "Files & History": "select cataloged files and review event histories", "Parsed Data": "inspect TLDraw, Drive, document, and unified event tables", "Agents": "review participants/operators/system agents", "Categories / Metadata": "manage labels and metadata", "Diagnostics / Warnings": "check health and repair issues"}.get(name, name)

    def refresh(self):
        if self.state.has_active_project(): self.mini.setText(f"Project: {self.state.active_project_name}\n{self.state.active_project_root}")
        else: self.mini.setText("No project loaded.\nStart or load a project from Dashboard.")
        self.overview.refresh()
        current = self.stack.currentWidget()
        current_refresh = getattr(current, "refresh", None)
        if current is not self.overview and callable(current_refresh):
            current_refresh()

    def switch_to_subview(self, name: str) -> bool:
        if name == "Artifacts / Catalog": name = "Files & History"
        if name in self.SUBVIEWS:
            self.nav.setCurrentRow(self.SUBVIEWS.index(name)); return True
        return False

    def navigate_tile(self, name: str) -> None:
        if name == "Artifacts / Catalog": name = "Files & History"
        if name in self.SUBVIEWS:
            self.switch_to_subview(name); return
        if self.navigate_to and self.navigate_to(name): return
        append_log(self.log, f"Open the {name} tab to continue.")
