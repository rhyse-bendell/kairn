from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QTableWidget,QLineEdit,QComboBox
from kairn.core.storage import repositories as repo
from ..widgets import set_table_rows,append_log,page_header
class CategoriesTab(QWidget):
    def __init__(self,state,log):
        super().__init__(); self.state=state; self.log=log
        l=QVBoxLayout(self); l.addWidget(page_header('Categories / Metadata','Manage labels and metadata for artifacts and events.','Add Category')); r=QHBoxLayout(); b=QPushButton('Refresh Categories'); b.clicked.connect(self.refresh); r.addWidget(b); l.addLayout(r)
        self.t=QTableWidget(); l.addWidget(self.t)
        ar=QHBoxLayout(); self.n=QLineEdit(); self.a=QComboBox(); self.a.addItems(['artifact','event','both']); self.d=QLineEdit(); ba=QPushButton('Add Category'); ba.clicked.connect(self.add)
        [ar.addWidget(x) for x in [self.n,self.a,self.d,ba]]; l.addLayout(ar)
    def refresh(self):
        if not self.state.active_collaboration_id: return
        set_table_rows(self.t,repo.list_categories(self.state.db_path,self.state.active_collaboration_id),['name','applies_to','description','is_default'])
    def add(self):
        if not self.state.active_collaboration_id or not self.n.text().strip(): return
        repo.create_category(self.state.db_path,self.state.active_collaboration_id,self.n.text().strip(),self.d.text().strip(),self.a.currentText())
        append_log(self.log,'category added'); self.refresh()
