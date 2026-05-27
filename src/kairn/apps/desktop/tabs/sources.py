from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QTableWidget,QFileDialog
from kairn.core.storage import repositories as repo
from kairn.core.ingestion.service import ingest_root
from ..workers import TaskWorker
from ..widgets import set_table_rows,append_log
class SourcesTab(QWidget):
    def __init__(self,state,log):
        super().__init__(); self.state=state; self.log=log; self.worker=None
        l=QVBoxLayout(self); r=QHBoxLayout();
        bsel=QPushButton('Select Folder'); bsel.clicked.connect(self.select)
        bing=QPushButton('Run Ingestion'); bing.clicked.connect(self.ingest)
        bref=QPushButton('Refresh'); bref.clicked.connect(self.refresh)
        [r.addWidget(x) for x in [bsel,bing,bref]]; l.addLayout(r)
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
        set_table_rows(self.art, repo.list_artifacts(self.state.db_path, self.state.active_collection_id), ['rel_path','kind','size_bytes','modified_at','event_count'])
        set_table_rows(self.warn, repo.list_warnings(self.state.db_path), ['run_id','rel_path','warning'])
