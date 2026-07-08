from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QTableWidget,QFileDialog
from kairn.core.tldraw.sqlite_parser import inspect_tldraw_db, parse_tldraw_audit_logs
from kairn.core.drive.activity_parser import parse_drive_activity_csv
from kairn.core.documents.changelog_parser import parse_all_changelogs_under_root
from kairn.core.process.unified_events import build_unified_process_events
from kairn.core.process.snapshots import create_board_snapshots
from ..widgets import set_table_rows,append_log,page_header
import sqlite3,json
class ProcessDataTab(QWidget):
    def __init__(self,state,log):
        super().__init__(); self.state=state; self.log=log; l=QVBoxLayout(self); l.addWidget(page_header('Parsed Data','Inspect TLDraw, Drive, document, and unified event tables.','Build Unified Process Events')); r=QHBoxLayout()
        for txt,fn in [('Inspect TLDraw DB',self.inspect),('Parse TLDraw Logs',self.parse_tldraw),('Parse Drive Activity',self.parse_drive),('Parse Document Changelogs',self.parse_docs),('Build Unified Process Events',self.unified),('Create Board Snapshots',self.snapshots),('Refresh Summary',self.refresh)]:
            b=QPushButton(txt); b.clicked.connect(fn); r.addWidget(b)
        l.addLayout(r); self.t=QTableWidget(); l.addWidget(self.t)
    def _file(self,caption,filter='All Files (*)'): return QFileDialog.getOpenFileName(self,caption,'',filter)[0]
    def inspect(self):
        p=self._file('Select TLDraw SQLite DB','SQLite (*.db *.sqlite *.sqlite3);;All Files (*)')
        if p: append_log(self.log,json.dumps(inspect_tldraw_db(p),indent=2)); self.refresh()
    def parse_tldraw(self):
        p=self._file('Select TLDraw SQLite DB','SQLite (*.db *.sqlite *.sqlite3);;All Files (*)')
        if p: append_log(self.log,str(parse_tldraw_audit_logs(p,self.state.db_path,self.state.active_collection_id,self.state.last_run_id))); self.refresh()
    def parse_drive(self):
        p=self._file('Select dailyLog.csv','CSV (*.csv);;All Files (*)')
        if p: append_log(self.log,str(parse_drive_activity_csv(p,self.state.db_path,self.state.active_collection_id,self.state.last_run_id))); self.refresh()
    def parse_docs(self):
        d=QFileDialog.getExistingDirectory(self,'Select changelog root')
        if d: append_log(self.log,str(parse_all_changelogs_under_root(d,self.state.db_path,self.state.active_collection_id,self.state.last_run_id))); self.refresh()
    def unified(self): append_log(self.log,str(build_unified_process_events(self.state.db_path,self.state.active_collection_id,self.state.last_run_id))); self.refresh()
    def snapshots(self): append_log(self.log,str(create_board_snapshots(self.state.db_path,self.state.active_collection_id,self.state.last_run_id))); self.refresh()
    def refresh(self):
        conn=sqlite3.connect(self.state.db_path); rows=[]
        for t in ['raw_tldraw_events','parsed_tldraw_events','drive_activity_events','document_edit_events','unified_process_events','board_snapshots']:
            exists=conn.execute("select 1 from sqlite_master where type='table' and name=?",(t,)).fetchone(); rows.append({'table':t,'count':conn.execute(f'select count(*) from {t}').fetchone()[0] if exists else 0})
        conn.close(); set_table_rows(self.t,rows,['table','count'])
