from __future__ import annotations

def main():
    try:
        from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QVBoxLayout,QTabWidget,QTextEdit
    except Exception as e:
        raise RuntimeError('PySide6 not installed; install with pip install -e ".[gui]"') from e
    from .state import AppState
    from .tabs.dashboard import DashboardTab
    from .tabs.sources import SourcesTab
    from .tabs.agents import AgentsTab
    from .tabs.artifacts import ArtifactsTab
    from .tabs.timeline import TimelineTab
    from .tabs.categories import CategoriesTab
    from .tabs.analysis import AnalysisTab
    from .tabs.process_data import ProcessDataTab
    from .tabs.exports import ExportsTab
    from .tabs.diagnostics import DiagnosticsTab
    from .tabs.replay import ReplayTab
    app=QApplication([]); w=QMainWindow(); w.setWindowTitle('Kairn — Collaboration Observatory')
    c=QWidget(); l=QVBoxLayout(c); tabs=QTabWidget(); log=QTextEdit(); log.setReadOnly(True); log.setPlaceholderText('Status messages will appear here.'); log.setMaximumHeight(120); state=AppState()
    tabs.addTab(DashboardTab(state,log),'Dashboard'); tabs.addTab(SourcesTab(state,log),'Sources'); tabs.addTab(ReplayTab(state,log),'Replay'); tabs.addTab(AgentsTab(state,log),'Agents'); tabs.addTab(ArtifactsTab(state,log),'Artifacts'); tabs.addTab(TimelineTab(state,log),'Timeline'); tabs.addTab(CategoriesTab(state,log),'Categories'); tabs.addTab(ProcessDataTab(state,log),'Process Data'); tabs.addTab(AnalysisTab(state,log),'Analysis'); tabs.addTab(ExportsTab(state,log),'Exports'); tabs.addTab(DiagnosticsTab(state,log),'Diagnostics')
    l.addWidget(tabs); l.addWidget(log); w.setCentralWidget(c); w.resize(1200,800); w.show(); app.exec()
if __name__=='__main__': main()
