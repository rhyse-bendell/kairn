from __future__ import annotations

def main():
    try:
        from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget, QTextEdit
    except Exception as e:
        raise RuntimeError('PySide6 not installed; install with pip install -e ".[gui]"') from e
    from .state import AppState
    from .tabs.dashboard import DashboardTab
    app=QApplication([])
    w=QMainWindow(); w.setWindowTitle('Kairn — Collaboration Observatory')
    c=QWidget(); l=QVBoxLayout(c)
    tabs=QTabWidget(); log=QTextEdit(); log.setReadOnly(True); log.setMaximumHeight(180)
    state=AppState()
    tabs.addTab(DashboardTab(state,log), 'Dashboard')
    for t in ['Sources','Agents','Artifacts','Timeline','Categories','Analysis','Exports','Diagnostics']:
        from PySide6.QtWidgets import QWidget
        tabs.addTab(QWidget(), t)
    l.addWidget(tabs); l.addWidget(log); w.setCentralWidget(c); w.resize(1200,800); w.show(); app.exec()

if __name__=='__main__':
    main()
