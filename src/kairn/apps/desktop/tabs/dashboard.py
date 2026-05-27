from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLineEdit,QPushButton,QComboBox,QLabel
from kairn.core.storage import repositories as repo
from kairn.core.ingestion.service import ingest_root

class DashboardTab(QWidget):
    def __init__(self,state,log):
        super().__init__(); self.state=state; self.log=log
        l=QVBoxLayout(self)
        self.name=QLineEdit(); self.desc=QLineEdit(); self.collabs=QComboBox(); self.root=QLineEdit()
        bnew=QPushButton('New Collaboration'); bnew.clicked.connect(self.create)
        bref=QPushButton('Refresh'); bref.clicked.connect(self.refresh)
        bing=QPushButton('Ingest Selected Root'); bing.clicked.connect(self.ingest)
        top=QHBoxLayout(); [top.addWidget(w) for w in [self.name,self.desc,bnew,bref,self.collabs]]
        l.addLayout(top); l.addWidget(QLabel('Root path')); l.addWidget(self.root); l.addWidget(bing)
        self.stats=QLabel(''); l.addWidget(self.stats); self.refresh()
    def logmsg(self,m): self.log.append(m)
    def create(self):
        cid=repo.create_collaboration(self.state.db_path,self.name.text() or 'Untitled', self.desc.text()); self.state.active_collaboration_id=cid; self.logmsg(f'created {cid}'); self.refresh()
    def refresh(self):
        self.collabs.clear(); cs=repo.list_collaborations(self.state.db_path)
        for c in cs: self.collabs.addItem(c['name'],c['id'])
        if cs: self.state.active_collaboration_id=self.collabs.currentData()
        self.stats.setText(f"artifacts={repo.count_artifacts(self.state.db_path)} events={repo.count_events(self.state.db_path)} participants={repo.count_participants(self.state.db_path)} runs={repo.count_runs(self.state.db_path)} warnings={repo.count_warnings(self.state.db_path)}")
    def ingest(self):
        self.state.active_collaboration_id=self.collabs.currentData(); self.state.active_root_path=self.root.text().strip()
        out=ingest_root(self.state.active_root_path,self.state.db_path,'./kairn_workspace/snapshots', collaboration_id=self.state.active_collaboration_id)
        self.state.last_run_id=out['run_id']; self.state.active_collection_id=out['collection_id']; self.logmsg(f"ingested run {out['run_id']}"); self.refresh()
