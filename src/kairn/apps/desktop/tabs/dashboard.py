from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QComboBox, QLabel, QFileDialog
from kairn.core.storage import repositories as repo
from kairn.core.ingestion.service import ingest_root
from ..workers import TaskWorker
from ..widgets import append_log, show_error


class DashboardTab(QWidget):
    def __init__(self, state, log):
        super().__init__(); self.state = state; self.log = log; self.worker = None
        l = QVBoxLayout(self)
        self.name = QLineEdit(); self.name.setPlaceholderText("Collaboration name")
        self.desc = QLineEdit(); self.desc.setPlaceholderText("Description")
        self.collabs = QComboBox(); self.root_label = QLabel("No root selected")
        bnew = QPushButton('New Collaboration'); bnew.clicked.connect(self.create)
        bref = QPushButton('Refresh Collaborations'); bref.clicked.connect(self.refresh)
        bload = QPushButton('Load Selected Collaboration'); bload.clicked.connect(self.load_selected)
        bsel = QPushButton('Select Root Folder'); bsel.clicked.connect(self.select_root)
        bing = QPushButton('Ingest Selected Root'); bing.clicked.connect(self.ingest)
        bsum = QPushButton('Refresh Summary'); bsum.clicked.connect(self.refresh_summary)
        row1 = QHBoxLayout(); [row1.addWidget(w) for w in [self.name, self.desc, bnew, bref]]
        row2 = QHBoxLayout(); [row2.addWidget(w) for w in [self.collabs, bload, bsel, bing, bsum]]
        l.addLayout(row1); l.addLayout(row2); l.addWidget(self.root_label)
        self.stats = {k: QLabel(f"{k}: 0") for k in ["artifacts", "events", "participants", "runs", "warnings", "latest_run"]}
        for v in self.stats.values(): l.addWidget(v)
        self.refresh()

    def refresh(self):
        self.collabs.clear(); cs = repo.list_collaborations(self.state.db_path)
        for c in cs: self.collabs.addItem(c['name'], c['id'])
        if cs: self.state.active_collaboration_id = self.collabs.currentData()
        append_log(self.log, f"Loaded {len(cs)} collaborations")
        self.refresh_summary()

    def refresh_summary(self):
        cid = self.state.active_collaboration_id
        self.stats['artifacts'].setText(f"artifact count: {repo.count_artifacts(self.state.db_path, self.state.active_collection_id)}")
        self.stats['events'].setText(f"event count: {repo.count_events(self.state.db_path, self.state.active_collection_id)}")
        self.stats['participants'].setText(f"participant count: {repo.count_participants(self.state.db_path)}")
        self.stats['runs'].setText(f"run count: {repo.count_runs(self.state.db_path, collaboration_id=cid, collection_id=self.state.active_collection_id)}")
        self.stats['warnings'].setText(f"warning count: {repo.count_warnings(self.state.db_path)}")
        lr = repo.get_latest_run(self.state.db_path, self.state.active_collection_id)
        self.stats['latest_run'].setText(f"latest run id: {lr['id'] if lr else 'n/a'}")

    def create(self):
        cid = repo.create_collaboration(self.state.db_path, self.name.text() or 'Untitled', self.desc.text())
        self.state.active_collaboration_id = cid; append_log(self.log, f'Created collaboration {cid}'); self.refresh()

    def load_selected(self):
        self.state.active_collaboration_id = self.collabs.currentData(); append_log(self.log, f"Active collaboration {self.state.active_collaboration_id}")

    def select_root(self):
        d = QFileDialog.getExistingDirectory(self, "Select root folder")
        if d:
            self.state.active_root_path = d; self.root_label.setText(f"Active root: {d}"); append_log(self.log, f"Selected root {d}")

    def ingest(self):
        if not self.state.active_collaboration_id or not self.state.active_root_path:
            show_error(self, "Missing setup", "Create/load collaboration and choose root folder first.")
            return
        self.worker = TaskWorker("ingest", ingest_root, self.state.active_root_path, self.state.db_path, self.state.snapshots_dir, None, self.state.active_collaboration_id)
        self.worker.started_task.connect(lambda n: append_log(self.log, f"Started {n}"))
        self.worker.finished_task.connect(self._on_ingested)
        self.worker.failed_task.connect(lambda e: append_log(self.log, e))
        self.worker.start()

    def _on_ingested(self, out):
        self.state.last_run_id = out['run_id']; self.state.active_collection_id = out['collection_id']
        append_log(self.log, f"Ingested run {out['run_id']}"); self.refresh_summary()
