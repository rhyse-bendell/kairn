from pathlib import Path
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QTableWidget
from kairn.core.export.compiled_json import export_compiled
from kairn.core.export.jsonl import export_jsonl
from kairn.core.export.csv import export_timeline_csv
from kairn.core.export.workshop import export_workshop_data
from kairn.core.observatory import build_observatory_report, export_observatory_report
from ..workers import TaskWorker
from ..widgets import set_table_rows,open_path,append_log,page_header,primary_action_button,secondary_action_button
class ExportsTab(QWidget):
    def __init__(self,state,log):
        super().__init__(); self.state=state; self.log=log; self.files=[]
        l=QVBoxLayout(self); l.addWidget(page_header('Exports','Write project data products, replay packages, timelines, diagnostics, and analysis outputs.','Export Workshop Data Products')); r=QHBoxLayout()
        for txt,fn in [('Export Compiled JSON',self.comp),('Export JSONL',self.jsonl),('Export Timeline CSV',self.csv),('Export Workshop Data',self.workshop),('Export Observatory Metrics Package',self.observatory),('Open Output Folder',self.open)]:
            b=primary_action_button(txt) if txt == 'Export Workshop Data' else secondary_action_button(txt); b.clicked.connect(fn); r.addWidget(b)
        l.addLayout(r); self.t=QTableWidget(); l.addWidget(self.t)
    def _add(self,p): self.files.append({'path':p}); self.state.last_output_dir=self.state.outputs_dir; set_table_rows(self.t,self.files,['path']); append_log(self.log,p)
    def comp(self): p=str(Path(self.state.outputs_dir)/'compiled.json'); export_compiled(self.state.db_path,p); self._add(p)
    def jsonl(self): p=str(Path(self.state.outputs_dir)/'events.jsonl'); export_jsonl(self.state.db_path,p,str(Path(self.state.outputs_dir)/'events.compact.jsonl.gz')); self._add(p)
    def csv(self): p=str(Path(self.state.outputs_dir)/'timeline.csv'); export_timeline_csv(self.state.db_path,p); self.state.last_timeline_csv_path=p; self._add(p)
    def workshop(self):
        r=export_workshop_data(self.state.db_path,self.state.outputs_dir); self._add(r['out_dir'])
    def observatory(self):
        report=getattr(self.state,'last_observatory_report',None)
        if report is None:
            project={'project_id':self.state.active_project_id,'name':self.state.active_project_name,'project_root':self.state.active_project_root or self.state.workspace_dir,'manifest_path':self.state.active_project_manifest_path,'db_path':self.state.db_path}
            report=build_observatory_report(project,self.state.db_path,run_id=self.state.last_run_id)
            self.state.last_observatory_report=report
        out=str(Path(self.state.active_run_reports_dir or self.state.outputs_dir)/'observatory_metrics')
        paths=export_observatory_report(report,out); self.state.last_observatory_output_dir=paths['out_dir']; self._add(paths['out_dir'])
    def open(self): open_path(self.state.outputs_dir)
