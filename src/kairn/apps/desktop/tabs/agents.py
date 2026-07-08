from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QTableWidget
from kairn.core.storage import repositories as repo
from kairn.core.maintenance.rebuild_participants import rebuild
from ..widgets import set_table_rows,append_log,page_header
class AgentsTab(QWidget):
    def __init__(self,state,log):
        super().__init__(); self.state=state; self.log=log
        l=QVBoxLayout(self); l.addWidget(page_header('Agents','Review participants, operators, and system agents found in project traces.','Rebuild Participants')); r=QHBoxLayout();
        b1=QPushButton('Rebuild Participants'); b1.clicked.connect(self.rebuild)
        b2=QPushButton('Refresh'); b2.clicked.connect(self.refresh)
        r.addWidget(b1); r.addWidget(b2); l.addLayout(r)
        self.t=QTableWidget(); l.addWidget(self.t)
    def rebuild(self): rebuild(self.state.db_path); append_log(self.log,'participants rebuilt'); self.refresh()
    def refresh(self): set_table_rows(self.t, repo.list_participants_with_counts(self.state.db_path), ['pid_label','actor_id','display_name','first_seen_ts','event_count'])
