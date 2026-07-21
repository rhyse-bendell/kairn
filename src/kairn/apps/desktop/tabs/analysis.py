import csv
from pathlib import Path
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QTableWidget,QLabel,QLineEdit,QComboBox,QTextEdit,QListWidget
from kairn.core.analysis.metrics import compute_metrics
from kairn.core.observatory import build_observatory_report, export_observatory_report, table_to_dataframe, report_summary
from kairn.core.progression import prepare_artifact_progression, generate_deterministic_progression_candidates, export_artifact_progression_package
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
        l.addLayout(o); self.obs_summary=QLabel('No observatory metrics computed.'); l.addWidget(self.obs_summary); l.addWidget(QLabel('Visualizations')); self.obs_visualizations=QListWidget(); self.obs_visualizations.itemDoubleClicked.connect(self.open_selected_visualization); l.addWidget(self.obs_visualizations); self.obs_tables=QListWidget(); self.obs_tables.currentRowChanged.connect(self.show_observatory_table); l.addWidget(self.obs_tables); self.obs_detail=QTableWidget(); l.addWidget(self.obs_detail); self.obs_notes=QTextEdit(); self.obs_notes.setReadOnly(True); l.addWidget(self.obs_notes)
        l.addWidget(QLabel('Artifact Progression Analysis'))
        pr=QHBoxLayout(); pb=primary_action_button('Prepare Artifact Progression'); pb.clicked.connect(self.prepare_progression); xb=secondary_action_button('Export Progression Package'); xb.clicked.connect(self.export_progression); obp=secondary_action_button('Open Progression Folder'); obp.clicked.connect(self.open_progression)
        for w in [pb,xb,obp]: pr.addWidget(w)
        l.addLayout(pr); self.progression_summary=QLabel('No artifact progression prepared.'); l.addWidget(self.progression_summary); self.progression_notes=QTextEdit(); self.progression_notes.setReadOnly(True); l.addWidget(self.progression_notes)
        self.load_observatory_report_from_state()
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
        self.load_observatory_report_from_state(); append_log(self.log,'Observatory metrics computed')
    def load_observatory_report_from_state(self) -> None:
        report = self.state.last_observatory_report
        if not report:
            self.obs_summary.setText('No observatory metrics computed.')
            return
        out = f" | Output: {self.state.last_observatory_output_dir}" if self.state.last_observatory_output_dir else ""
        self.obs_summary.setText(f"Tables: {len(report.tables)} | Warnings: {len(report.warnings)} | Streams available: {sum(1 for t in report.tables if t.rows)}{out}")
        self.obs_visualizations.clear()
        out_dir = Path(self.state.last_observatory_output_dir) if self.state.last_observatory_output_dir else None
        labels = [('Trace ecology overview','trace_ecology_overview.html'),('Event density by stream','event_density_by_stream.html'),('Actor activity by stream','actor_activity_by_stream.html'),('Artifact history overview','artifact_history_overview.html'),('Document change activity','document_change_activity.html'),('TLDraw concept map activity','tldraw_concept_map_activity.html'),('Transcript activity','transcript_activity.html'),('Team case study','team_case_study.html')]
        for label, filename in labels:
            item_label = label if out_dir and (out_dir/'visualizations'/filename).exists() else f'{label} (export to open)'
            self.obs_visualizations.addItem(item_label)
        self.obs_tables.clear(); [self.obs_tables.addItem(t.table_id) for t in report.tables]
        self.obs_notes.setPlainText('\n'.join((report.caveats or []) + (report.warnings or [])))
        if report.tables:
            self.obs_tables.setCurrentRow(0)
            self.show_observatory_table(0)
    def refresh(self):
        self.load_observatory_report_from_state()
    def show_observatory_table(self, idx):
        if idx < 0 or not self.state.last_observatory_report: return
        t=self.state.last_observatory_report.tables[idx]; set_table_rows(self.obs_detail, t.rows, t.columns)
    def open_selected_visualization(self, item):
        out_dir = Path(self.state.last_observatory_output_dir) if self.state.last_observatory_output_dir else None
        if not out_dir: return
        names=['trace_ecology_overview.html','event_density_by_stream.html','actor_activity_by_stream.html','artifact_history_overview.html','document_change_activity.html','tldraw_concept_map_activity.html','transcript_activity.html','team_case_study.html']
        row=self.obs_visualizations.currentRow()
        if 0 <= row < len(names):
            p=out_dir/'visualizations'/names[row]
            if p.exists(): open_path(str(p))

    def export_observatory(self):
        if not self.state.last_observatory_report: self.compute_observatory(); return
        out=str(Path(self.state.active_run_reports_dir or self.state.outputs_dir)/'observatory_metrics')
        paths=export_observatory_report(self.state.last_observatory_report,out); self.state.last_observatory_output_dir=paths['out_dir']; append_log(self.log,f"Observatory report at {paths['out_dir']}"); self.obs_summary.setText(self.obs_summary.text()+f" | Output: {paths['out_dir']}")
    def open_observatory(self):
        if self.state.last_observatory_output_dir: open_path(self.state.last_observatory_output_dir)

    def prepare_progression(self):
        self.worker=TaskWorker('artifact_progression', prepare_artifact_progression, self._project(), self.state.active_collection_id, self.state.active_profile_name, False)
        self.worker.finished_task.connect(self._progression_prepared); self.worker.failed_task.connect(lambda e: append_log(self.log,e)); self.worker.start()
    def _progression_prepared(self, summary):
        cand=generate_deterministic_progression_candidates(self.state.db_path, summary['analysis_run_id']); summary['deterministic_candidate_count']=cand.get('candidate_count',0)
        self.state.last_progression_analysis_run_id=summary['analysis_run_id']; self.state.last_progression_summary=summary
        self._show_progression_summary(summary); append_log(self.log,'Artifact progression prepared')
    def _show_progression_summary(self, summary):
        self.progression_summary.setText(f"Included: {summary.get('included_artifacts',0)} | Excluded: {summary.get('excluded_artifacts',0)} | Requires review: {summary.get('requires_review_artifacts',0)} | Evidence units: {summary.get('evidence_unit_count',0)} | Candidates: {summary.get('deterministic_candidate_count',0)}")
        self.progression_notes.setPlainText('\n'.join(summary.get('warnings') or []))
    def export_progression(self):
        rid=getattr(self.state,'last_progression_analysis_run_id',None)
        if not rid: self.prepare_progression(); return
        out=str(Path(self.state.active_run_reports_dir or self.state.outputs_dir)/'artifact_progression')
        res=export_artifact_progression_package(self.state.db_path, rid, out); self.state.last_progression_output_dir=res.get('out_dir'); append_log(self.log,f"Progression package at {res.get('out_dir')}")
    def open_progression(self):
        out=getattr(self.state,'last_progression_output_dir',None)
        if out: open_path(out)
