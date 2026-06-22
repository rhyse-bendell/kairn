from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QTableWidget,QFileDialog,QComboBox
from kairn.core.storage import repositories as repo
from kairn.core.ingestion.service import ingest_root
from kairn.core.profiles import list_builtin_profiles
from kairn.core.catalog.artifact_catalog import build_artifact_catalog, export_artifact_catalog
from ..workers import TaskWorker
from ..widgets import set_table_rows,append_log
class SourcesTab(QWidget):
    def __init__(self,state,log):
        super().__init__(); self.state=state; self.log=log; self.worker=None
        l=QVBoxLayout(self); r=QHBoxLayout();
        bsel=QPushButton('Select Folder'); bsel.clicked.connect(self.select)
        bing=QPushButton('Run Ingestion'); bing.clicked.connect(self.ingest)
        bref=QPushButton('Refresh'); bref.clicked.connect(self.refresh)
        self.profile=QComboBox(); [self.profile.addItem(p['name']) for p in list_builtin_profiles()]; self.profile.setCurrentText(self.state.active_profile_name); self.profile.currentTextChanged.connect(lambda v:setattr(self.state,'active_profile_name',v))
        bcat=QPushButton('Build/Refresh Artifact Catalog'); bcat.clicked.connect(self.build_catalog)
        [r.addWidget(x) for x in [bsel,bing,bref,self.profile,bcat]]; l.addLayout(r)
        self.art=QTableWidget(); self.warn=QTableWidget(); l.addWidget(self.art); l.addWidget(self.warn)
    def select(self):
        d=QFileDialog.getExistingDirectory(self,'Select root folder')
        if d: self.state.active_root_path=d; append_log(self.log,f'Selected root {d}')
    def ingest(self):
        if not self.state.active_collaboration_id or not self.state.active_root_path: return
        self.worker=TaskWorker('ingest', ingest_root, self.state.active_root_path,self.state.db_path,self.state.snapshots_dir,None,self.state.active_collaboration_id)
        self.worker.finished_task.connect(lambda o:(setattr(self.state,'active_collection_id',o['collection_id']),setattr(self.state,'last_run_id',o['run_id']),append_log(self.log,f"Ingested {o['run_id']}"),self.refresh()))
        self.worker.start()
    def refresh(self):
        rows = getattr(self, '_catalog_rows', None) or repo.list_artifacts(self.state.db_path, self.state.active_collection_id)
        cols = ['rel_path','kind','source_type','artifact_role','team_hint','participant_hint','source_confidence','role_confidence','warnings'] if getattr(self, '_catalog_rows', None) else ['rel_path','kind','size_bytes','modified_at','event_count']
        set_table_rows(self.art, rows, cols)
        set_table_rows(self.warn, repo.list_warnings(self.state.db_path), ['run_id','rel_path','warning'])
    def build_catalog(self):
        if not self.state.active_collection_id:
            append_log(self.log,'No active collection; ingest a folder before building an artifact catalog')
            return
        out_dir = self.state.active_run_reports_dir or self.state.last_output_dir or self.state.outputs_dir
        paths = export_artifact_catalog(self.state.db_path, out_dir, collection_id=self.state.active_collection_id, profile_name_or_path=self.state.active_profile_name)
        self.state.last_artifact_catalog_paths = paths
        self._catalog_rows = build_artifact_catalog(self.state.db_path, collection_id=self.state.active_collection_id, profile_name_or_path=self.state.active_profile_name)
        append_log(self.log, f"Artifact catalog written to {paths['catalog_csv']}")
        self.refresh()
