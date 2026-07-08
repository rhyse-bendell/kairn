from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QTextEdit,QTableWidget
from kairn.core.storage import repositories as repo
from kairn.core.maintenance.rebuild_participants import rebuild
from ..widgets import set_table_rows,page_header
class DiagnosticsTab(QWidget):
    def __init__(self,state,log):
        super().__init__(); self.state=state
        l=QVBoxLayout(self); l.addWidget(page_header('Diagnostics / Warnings','Check project health, warnings, and repair utilities.','Run Diagnostics')); r=QHBoxLayout()
        for txt,fn in [('Run Diagnostics',self.diag),('Rebuild Participants',self.rb),('Fix Changelog Timestamps',self.fix),('Refresh Warnings',self.warns)]:
            b=QPushButton(txt); b.clicked.connect(fn); r.addWidget(b)
        l.addLayout(r); self.out=QTextEdit(); self.w=QTableWidget(); l.addWidget(self.out); l.addWidget(self.w)
    def diag(self):
        s={'collaborations':repo.count_collaborations(self.state.db_path),'collections':repo.count_collections(self.state.db_path),'artifacts':repo.count_artifacts(self.state.db_path),'events':repo.count_events(self.state.db_path),'participants':repo.count_participants(self.state.db_path),'runs':repo.count_runs(self.state.db_path),'warnings':repo.count_warnings(self.state.db_path)}
        self.out.setPlainText('\n'.join(f"{k}: {v}" for k,v in s.items()))
    def rb(self): rebuild(self.state.db_path); self.diag()
    def fix(self): self.out.append('Timestamp fix not yet implemented in backend.')
    def warns(self): set_table_rows(self.w,repo.list_warnings(self.state.db_path),['run_id','rel_path','warning'])
