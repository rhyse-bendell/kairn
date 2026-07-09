import csv
from pathlib import Path
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QTableWidget,QLabel,QLineEdit,QComboBox,QTextEdit,QListWidget
from kairn.core.analysis.metrics import compute_metrics
from kairn.core.observatory import build_observatory_report, export_observatory_report, table_to_dataframe, report_summary
from ..workers import TaskWorker
from ..widgets import set_table_rows,open_path,append_log,page_header,primary_action_button,secondary_action_button
class AnalysisTab(QWidget):
    def __init__(self,state,log):
        super().__init__(); self.state=state; self.log=log; self.worker=None
        l=QVBoxLayout(self); l.addWidget(page_header('Analysis','Compute descriptive metrics and trace-based indicators from the active project. Indicators are descriptive traces, not direct cognition or performance measures.','Compute Metrics')); l.addWidget(QLabel('Activity Indicators'))
        r=QHBoxLayout(); b1=primary_action_button('Compute Metrics'); b1.clicked.connect(self.run); b2=secondary_action_button('Open Metrics CSV'); b2.clicked.connect(self.open)
        r.addWidget(b1); r.addWidget(b2); l.addLayout(r); self.t=QTableWidget(); l.addWidget(self.t)
        l.addWidget(QLabel('Observatory Metrics'))
        o=QHBoxLayout(); self.obs_team=QLineEdit(); self.obs_team.setPlaceholderText('Team filter (optional)'); self.obs_activity=QLineEdit(); self.obs_activity.setPlaceholderText('Activity filter (optional)'); self.obs_bin=QComboBox(); self.obs_bin.addItems(['15','30','60'])
        cb=primary_action_button('Compute Observatory Metrics'); cb.clicked.connect(self.compute_observatory); eb=secondary_action_button('Export Observatory Report'); eb.clicked.connect(self.export_observatory); ob=secondary_action_button('Open Metrics Folder'); ob.clicked.connect(self.open_observatory)
        for w in [self.obs_team,self.obs_activity,self.obs_bin,cb,eb,ob]: o.addWidget(w)
        l.addLayout(o); self.obs_summary=QLabel('No observatory metrics computed.'); l.addWidget(self.obs_summary); self.obs_tables=QListWidget(); self.obs_tables.currentRowChanged.connect(self.show_observatory_table); l.addWidget(self.obs_tables); self.obs_detail=QTableWidget(); l.addWidget(self.obs_detail); self.obs_notes=QTextEdit(); self.obs_notes.setReadOnly(True); l.addWidget(self.obs_notes)
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
    def _project(self): return {'project_id':self.state.active_project_id,'name':self.state.active_project_name,'project_root':self.state.active_project_root or self.state.workspace_dir,'manifest_path':self.state.active_project_manifest_path,'db_path':self.state.db_path}
    def compute_observatory(self):
        self.worker=TaskWorker('observatory', build_observatory_report, self._project(), self.state.db_path, self.state.last_run_id, self.obs_team.text() or None, self.obs_activity.text() or None, int(self.obs_bin.currentText()))
        self.worker.finished_task.connect(self._observatory_done); self.worker.failed_task.connect(lambda e: append_log(self.log,e)); self.worker.start()
    def _observatory_done(self, report):
        self.state.last_observatory_report=report; self.state.last_observatory_tables=report.tables; self.state.last_observatory_warnings=report.warnings; self.state.last_observatory_chart_specs=report.charts
        self.obs_summary.setText(f"Tables: {len(report.tables)} | Warnings: {len(report.warnings)} | Streams available: {sum(1 for t in report.tables if t.rows)}")
        self.obs_tables.clear(); [self.obs_tables.addItem(t.table_id) for t in report.tables]
        self.obs_notes.setPlainText('\n'.join(report.caveats + report.warnings)); append_log(self.log,'Observatory metrics computed')
    def show_observatory_table(self, idx):
        if idx < 0 or not self.state.last_observatory_report: return
        t=self.state.last_observatory_report.tables[idx]; set_table_rows(self.obs_detail, t.rows, t.columns)
    def export_observatory(self):
        if not self.state.last_observatory_report: self.compute_observatory(); return
        out=str(Path(self.state.active_run_reports_dir or self.state.outputs_dir)/'observatory_metrics')
        paths=export_observatory_report(self.state.last_observatory_report,out); self.state.last_observatory_output_dir=paths['out_dir']; append_log(self.log,f"Observatory report at {paths['out_dir']}"); self.obs_summary.setText(self.obs_summary.text()+f" | Output: {paths['out_dir']}")
    def open_observatory(self):
        if self.state.last_observatory_output_dir: open_path(self.state.last_observatory_output_dir)
