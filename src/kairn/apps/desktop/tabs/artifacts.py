from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QTableWidget,QComboBox
from kairn.core.storage import repositories as repo
from ..widgets import set_table_rows
class ArtifactsTab(QWidget):
    def __init__(self,state,log):
        super().__init__(); self.state=state
        l=QVBoxLayout(self); r=QHBoxLayout(); self.kind=QComboBox(); self.kind.currentTextChanged.connect(self.refresh)
        b=QPushButton('Refresh'); b.clicked.connect(self.refresh); r.addWidget(self.kind); r.addWidget(b); l.addLayout(r)
        self.a=QTableWidget(); self.e=QTableWidget(); self.a.itemSelectionChanged.connect(self.events_for_selected); l.addWidget(self.a); l.addWidget(self.e)
    def refresh(self):
        rows=repo.list_artifacts(self.state.db_path,self.state.active_collection_id)
        kinds=['All']+sorted({r.get('kind') or 'unknown' for r in rows})
        if self.kind.count()==0: self.kind.addItems(kinds)
        if self.kind.currentText() not in ('', 'All'): rows=[r for r in rows if (r.get('kind') or 'unknown')==self.kind.currentText()]
        set_table_rows(self.a,rows,['id','rel_path','kind','name','size_bytes','modified_at','event_count'])
    def events_for_selected(self):
        row=self.a.currentRow();
        if row<0: return
        aid=self.a.item(row,0).text()
        set_table_rows(self.e,repo.list_events(self.state.db_path,self.state.active_collection_id,aid),['ts','action','actor','mentioned_unit','summary'])
