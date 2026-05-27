from pathlib import Path
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QTableWidget,QLineEdit
from kairn.core.storage import repositories as repo
from kairn.core.visualization.timeline_plotly import build_timeline_html
from ..workers import TaskWorker
from ..widgets import set_table_rows,open_path,append_log
class TimelineTab(QWidget):
    def __init__(self,state,log):
        super().__init__(); self.state=state; self.log=log; self.worker=None
        l=QVBoxLayout(self); r=QHBoxLayout(); self.af=QLineEdit(); self.ac=QLineEdit(); self.uf=QLineEdit()
        for w in [self.af,self.ac,self.uf]: w.setPlaceholderText('filter')
        br=QPushButton('Refresh Events'); br.clicked.connect(self.refresh); bg=QPushButton('Generate Visualization'); bg.clicked.connect(self.gen); bo=QPushButton('Open Last Visualization'); bo.clicked.connect(self.open)
        [r.addWidget(x) for x in [self.af,self.ac,self.uf,br,bg,bo]]; l.addLayout(r)
        self.t=QTableWidget(); l.addWidget(self.t)
    def refresh(self):
        rows=repo.list_events(self.state.db_path,self.state.active_collection_id)
        rows=[x for x in rows if self.af.text().lower() in (x.get('actor') or '').lower() and self.ac.text().lower() in (x.get('action') or '').lower() and self.uf.text().lower() in ((x.get('artifact_id') or '')+(x.get('mentioned_unit') or '')).lower()]
        set_table_rows(self.t,rows,['ts','action','actor','artifact_id','mentioned_unit','summary'])
    def gen(self):
        out=str(Path(self.state.outputs_dir)/'timeline.html')
        self.worker=TaskWorker('visualization', build_timeline_html,self.state.db_path,out)
        self.worker.finished_task.connect(lambda _:(setattr(self.state,'last_visualization_path',out),append_log(self.log,f'Generated {out}')))
        self.worker.start()
    def open(self):
        if self.state.last_visualization_path: open_path(self.state.last_visualization_path)
