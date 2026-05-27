import csv
from pathlib import Path
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QTableWidget,QLabel
from kairn.core.analysis.metrics import compute_metrics
from ..workers import TaskWorker
from ..widgets import set_table_rows,open_path,append_log
class AnalysisTab(QWidget):
    def __init__(self,state,log):
        super().__init__(); self.state=state; self.log=log; self.worker=None
        l=QVBoxLayout(self); l.addWidget(QLabel('Activity Indicators'))
        r=QHBoxLayout(); b1=QPushButton('Compute Metrics'); b1.clicked.connect(self.run); b2=QPushButton('Open Metrics CSV'); b2.clicked.connect(self.open)
        r.addWidget(b1); r.addWidget(b2); l.addLayout(r); self.t=QTableWidget(); l.addWidget(self.t)
    def run(self):
        out=str(Path(self.state.outputs_dir)/'metrics.csv')
        self.worker=TaskWorker('metrics',compute_metrics,self.state.db_path,out)
        self.worker.finished_task.connect(lambda _:(setattr(self.state,'last_metrics_path',out),append_log(self.log,f'Metrics at {out}'),self.load()))
        self.worker.start()
    def load(self):
        if not self.state.last_metrics_path: return
        with open(self.state.last_metrics_path,newline='',encoding='utf-8') as f: rows=list(csv.DictReader(f))
        set_table_rows(self.t,rows,['actor','total_events','words_added','first_ts','last_ts'])
    def open(self):
        if self.state.last_metrics_path: open_path(self.state.last_metrics_path)
