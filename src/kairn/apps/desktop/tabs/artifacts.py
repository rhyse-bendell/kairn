from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QComboBox

from kairn.core.storage import repositories as repo
from ..widgets import append_log, muted_help_label, page_header, primary_action_button, set_table_rows


class ArtifactsTab(QWidget):
    def __init__(self, state, log):
        super().__init__()
        self.state = state
        self.log = log
        layout = QVBoxLayout(self)
        layout.addWidget(page_header('Files & History', 'Select a cataloged file or artifact to view its event history.', 'Refresh Files'))
        row = QHBoxLayout()
        self.kind = QComboBox()
        self.kind.currentTextChanged.connect(self.refresh)
        button = primary_action_button('Refresh Files')
        button.clicked.connect(self.refresh)
        row.addWidget(self.kind)
        row.addWidget(button)
        layout.addLayout(row)
        self.empty_label = muted_help_label('No cataloged files yet. Open Sources / Intake, prepare/parse data, and build the artifact catalog.')
        layout.addWidget(self.empty_label)
        layout.addWidget(QLabel('Cataloged Files'))
        self.a = QTableWidget()
        layout.addWidget(self.a)
        layout.addWidget(QLabel('Selected File Event History'))
        self.e = QTableWidget()
        self.a.itemSelectionChanged.connect(self.events_for_selected)
        layout.addWidget(self.e)

    def refresh(self):
        rows = repo.list_artifacts(self.state.db_path, self.state.active_collection_id)
        kinds = ['All'] + sorted({r.get('kind') or 'unknown' for r in rows})
        if self.kind.count() == 0:
            self.kind.addItems(kinds)
        if self.kind.currentText() not in ('', 'All'):
            rows = [r for r in rows if (r.get('kind') or 'unknown') == self.kind.currentText()]
        self.empty_label.setVisible(len(rows) == 0)
        if not rows:
            append_log(self.log, 'No cataloged files yet. Open Sources / Intake, prepare/parse data, and build the artifact catalog.')
        set_table_rows(self.a, rows, ['id', 'rel_path', 'kind', 'name', 'size_bytes', 'modified_at', 'event_count'])

    def events_for_selected(self):
        row = self.a.currentRow()
        if row < 0:
            return
        aid = self.a.item(row, 0).text()
        set_table_rows(self.e, repo.list_events(self.state.db_path, self.state.active_collection_id, aid), ['ts', 'action', 'actor', 'mentioned_unit', 'summary'])

    def select_artifact_by_path(self, path: str) -> bool:
        self.refresh()
        wanted = Path(path)
        wanted_name = wanted.name
        candidates = {str(wanted), wanted_name}
        try:
            root = Path(self.state.active_project_root)
            candidates.add(str(wanted.relative_to(root)))
        except Exception:
            pass
        for row in range(self.a.rowCount()):
            rel_item = self.a.item(row, 1)
            name_item = self.a.item(row, 3)
            values = {rel_item.text() if rel_item else '', name_item.text() if name_item else ''}
            if candidates & values:
                self.a.selectRow(row)
                self.events_for_selected()
                return True
        return False
