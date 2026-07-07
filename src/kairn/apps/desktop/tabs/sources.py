from __future__ import annotations
import json
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QTableWidget,QFileDialog,QComboBox,QTextEdit,QSplitter
from kairn.core.storage import repositories as repo
from kairn.core.ingestion.service import ingest_root
from kairn.core.profiles import list_builtin_profiles
from kairn.core.catalog.artifact_catalog import build_artifact_catalog, export_artifact_catalog
from kairn.core.workshop.intake import inspect_workshop_path, prepare_workshop_source
from ..workers import TaskWorker
from ..widgets import set_table_rows,append_log
class SourcesTab(QWidget):
    def __init__(self,state,log):
        super().__init__(); self.state=state; self.log=log; self.worker=None; self.selected_source=None; self.last_inspection=None
        l=QVBoxLayout(self); r=QHBoxLayout();
        buttons=[('Select Folder',self.select),('Select File',self.select_file),('Inspect Selected Source',self.inspect_selected),('Prepare / Parse Known Sources',self.prepare_selected),('Extract ZIP + Prepare',self.extract_prepare),('Export Parsed Data Products',self.export_products),('Run Ingestion',self.ingest),('Refresh',self.refresh)]
        for txt,fn in buttons:
            b=QPushButton(txt); b.clicked.connect(fn); r.addWidget(b)
        self.profile=QComboBox(); [self.profile.addItem(p['name']) for p in list_builtin_profiles()]; self.profile.setCurrentText(self.state.active_profile_name); self.profile.currentTextChanged.connect(lambda v:setattr(self.state,'active_profile_name',v)); r.addWidget(self.profile)
        bcat=QPushButton('Build/Refresh Artifact Catalog'); bcat.clicked.connect(self.build_catalog); r.addWidget(bcat); l.addLayout(r)
        split=QSplitter(); self.detect=QTextEdit(); self.detect.setReadOnly(True); self.actions=QTextEdit(); self.actions.setReadOnly(True); split.addWidget(self.detect); split.addWidget(self.actions); l.addWidget(split)
        self.art=QTableWidget(); self.warn=QTableWidget(); l.addWidget(self.art); l.addWidget(self.warn)
    def select(self):
        d=QFileDialog.getExistingDirectory(self,'Select root folder')
        if d: self.state.active_root_path=d; self.selected_source=d; append_log(self.log,f'Selected root {d}')
    def select_file(self):
        f=QFileDialog.getOpenFileName(self,'Select workshop source','','Workshop sources (*.zip *.db *.sqlite *.sqlite3 *.csv *.txt *.html *.docx *.pptx);;All Files (*)')[0]
        if f: self.selected_source=f; append_log(self.log,f'Selected file {f}')
    def inspect_selected(self):
        p=self.selected_source or self.state.active_root_path
        if not p: return
        self.last_inspection=inspect_workshop_path(p); self.detect.setText(json.dumps(self.last_inspection,indent=2,default=str))
        det=self.last_inspection.get('detection',{}); self.actions.setText('Available actions:\n- '+'\n- '.join(det.get('available_actions',[]))+f"\n\nSuggested next action: {det.get('suggested_next_action')}")
        append_log(self.log,f"Detected {det.get('source_type')} ({det.get('confidence')})")
    def _prepare(self,extract=False):
        p=self.selected_source or self.state.active_root_path
        if not p: return
        out=prepare_workshop_source(p,self.state.db_path,self.state.workspace_dir,collection_id=self.state.active_collection_id,run_id=self.state.last_run_id,profile=self.state.active_profile_name,extract=extract)
        self.state.active_collection_id=out.get('collection_id') or self.state.active_collection_id; self.state.last_run_id=out.get('run_id') or self.state.last_run_id; self.state.last_output_dir=(out.get('output_paths') or {}).get('out_dir',self.state.last_output_dir)
        self.actions.setText(json.dumps(out,indent=2,default=str)); append_log(self.log,'Workshop source prepared / parsed'); self.refresh()
    def prepare_selected(self): self._prepare(False)
    def extract_prepare(self): self._prepare(True)
    def export_products(self):
        from kairn.core.export.workshop import export_workshop_data
        out_dir=self.state.active_run_reports_dir or self.state.last_output_dir or self.state.outputs_dir
        res=export_workshop_data(self.state.db_path,out_dir); self.actions.setText(json.dumps(res,indent=2)); append_log(self.log,f"Exported parsed data products to {res['out_dir']}")
    def ingest(self):
        if not self.state.active_collaboration_id or not self.state.active_root_path: return
        self.worker=TaskWorker('ingest', ingest_root, self.state.active_root_path,self.state.db_path,self.state.snapshots_dir,None,self.state.active_collaboration_id)
        self.worker.finished_task.connect(lambda o:(setattr(self.state,'active_collection_id',o['collection_id']),setattr(self.state,'last_run_id',o['run_id']),append_log(self.log,f"Ingested {o['run_id']}"),self.refresh()))
        self.worker.start()
    def refresh(self):
        rows = getattr(self, '_catalog_rows', None) or repo.list_artifacts(self.state.db_path, self.state.active_collection_id)
        cols = ['rel_path','kind','source_type','artifact_role','team_hint','participant_hint','source_confidence','role_confidence','warnings'] if getattr(self, '_catalog_rows', None) else ['rel_path','kind','size_bytes','modified_at','event_count']
        set_table_rows(self.art, rows, cols); set_table_rows(self.warn, repo.list_warnings(self.state.db_path), ['run_id','rel_path','warning'])
    def build_catalog(self):
        if not self.state.active_collection_id: append_log(self.log,'No active collection; ingest/prepare a folder before building an artifact catalog'); return
        out_dir = self.state.active_run_reports_dir or self.state.last_output_dir or self.state.outputs_dir
        paths = export_artifact_catalog(self.state.db_path, out_dir, collection_id=self.state.active_collection_id, profile_name_or_path=self.state.active_profile_name)
        self.state.last_artifact_catalog_paths = paths; self._catalog_rows = build_artifact_catalog(self.state.db_path, collection_id=self.state.active_collection_id, profile_name_or_path=self.state.active_profile_name)
        append_log(self.log, f"Artifact catalog written to {paths['catalog_csv']}"); self.refresh()
