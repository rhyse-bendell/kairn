from pathlib import Path
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QTableWidget
from kairn.core.export.compiled_json import export_compiled
from kairn.core.export.jsonl import export_jsonl
from kairn.core.export.csv import export_timeline_csv
from kairn.core.export.workshop import export_workshop_data
from ..workers import TaskWorker
from ..widgets import set_table_rows,open_path,append_log
class ExportsTab(QWidget):
    def __init__(self,state,log):
        super().__init__(); self.state=state; self.log=log; self.files=[]
        l=QVBoxLayout(self); r=QHBoxLayout()
        for txt,fn in [('Export Compiled JSON',self.comp),('Export JSONL',self.jsonl),('Export Timeline CSV',self.csv),('Export Workshop Data',self.workshop),('Open Output Folder',self.open)]:
            b=QPushButton(txt); b.clicked.connect(fn); r.addWidget(b)
        l.addLayout(r); self.t=QTableWidget(); l.addWidget(self.t)
    def _add(self,p): self.files.append({'path':p}); self.state.last_output_dir=self.state.outputs_dir; set_table_rows(self.t,self.files,['path']); append_log(self.log,p)
    def comp(self): p=str(Path(self.state.outputs_dir)/'compiled.json'); export_compiled(self.state.db_path,p); self._add(p)
    def jsonl(self): p=str(Path(self.state.outputs_dir)/'events.jsonl'); export_jsonl(self.state.db_path,p,str(Path(self.state.outputs_dir)/'events.compact.jsonl.gz')); self._add(p)
    def csv(self): p=str(Path(self.state.outputs_dir)/'timeline.csv'); export_timeline_csv(self.state.db_path,p); self.state.last_timeline_csv_path=p; self._add(p)
    def workshop(self):
        r=export_workshop_data(self.state.db_path,self.state.outputs_dir); self._add(r['out_dir'])
    def open(self): open_path(self.state.outputs_dir)
