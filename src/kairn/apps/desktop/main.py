from __future__ import annotations

import os


def _import_qt():
    try:
        from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget, QTextEdit
    except Exception as e:  # pragma: no cover
        raise RuntimeError('PySide6 not installed; install with pip install -e ".[gui]"') from e
    return QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget, QTextEdit


try:
    _BaseMainWindow = _import_qt()[1]
except RuntimeError:  # pragma: no cover
    _BaseMainWindow = object


class KairnMainWindow(_BaseMainWindow):
    """Main desktop shell organized around Kairn's workflow tabs."""

    TOP_LEVEL_TABS = ["Dashboard", "Project", "Replay", "Analysis", "Exports"]

    def __init__(self):
        QApplication, _QMainWindow, QWidget, QVBoxLayout, QTabWidget, QTextEdit = _import_qt()
        super().__init__()
        from .state import AppState
        from .tabs.analysis import AnalysisTab
        from .tabs.dashboard import DashboardTab
        from .tabs.exports import ExportsTab
        from .tabs.project import ProjectTab
        from .tabs.replay import ReplayTab

        self.setWindowTitle('Kairn — Collaboration Observatory')
        self.state = AppState()
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText('Status messages will appear here.')
        self.log.setMaximumHeight(120)
        self.tabs = QTabWidget()
        self._tab_indexes: dict[str, int] = {}

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self.tabs)
        layout.addWidget(self.log)
        self.setCentralWidget(central)

        self.dashboard_tab = DashboardTab(self.state, self.log, on_project_loaded=self.activate_project)
        self.project_tab = ProjectTab(self.state, self.log, navigate_to=self.switch_to_tab)
        self.replay_tab = ReplayTab(self.state, self.log)
        self.analysis_tab = AnalysisTab(self.state, self.log)
        self.exports_tab = ExportsTab(self.state, self.log)

        self._add_tab(self.dashboard_tab, "Dashboard")
        self._add_tab(self.project_tab, "Project")
        self._add_tab(self.replay_tab, "Replay")
        self._add_tab(self.analysis_tab, "Analysis")
        self._add_tab(self.exports_tab, "Exports")
        self.resize(1200, 800)

    def apply_startup_window_mode(self) -> None:
        """Show the desktop window using the configured startup mode."""
        mode = os.environ.get("KAIRN_WINDOW_MODE", "maximized").strip().lower()
        if mode == "fullscreen":
            self.showFullScreen()
            return
        if mode == "windowed":
            self._show_centered_windowed()
            return
        self.showMaximized()

    def _show_centered_windowed(self) -> None:
        QApplication = _import_qt()[0]
        screen = QApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            width = min(self.width(), available.width())
            height = min(self.height(), available.height())
            self.resize(width, height)
            x = available.x() + max((available.width() - width) // 2, 0)
            y = available.y() + max((available.height() - height) // 2, 0)
            self.move(x, y)
        self.show()

    def _add_tab(self, widget, name: str) -> None:
        self._tab_indexes[name] = self.tabs.addTab(widget, name)

    def switch_to_tab(self, name: str) -> bool:
        index = self._tab_indexes.get(name)
        if index is None:
            return False
        self.tabs.setCurrentIndex(index)
        return True

    def activate_project(self, project: dict) -> None:
        self.state.set_active_project(project)
        self.refresh_project_aware_tabs()
        self.switch_to_tab("Project")

    def refresh_project_aware_tabs(self) -> None:
        from .widgets import append_log

        for tab in (self.dashboard_tab, self.project_tab, self.replay_tab, self.analysis_tab, self.exports_tab):
            refresh = getattr(tab, "refresh", None)
            if not callable(refresh):
                continue
            try:
                refresh()
            except Exception as exc:  # pragma: no cover - defensive GUI logging
                append_log(self.log, f"Could not refresh {tab.__class__.__name__}: {exc}")
                raise

    def current_tab_name(self) -> str | None:
        index = self.tabs.currentIndex()
        if index < 0:
            return None
        return self.tabs.tabText(index)

    def tab_names(self) -> list[str]:
        return [self.tabs.tabText(i) for i in range(self.tabs.count())]


def main():
    QApplication = _import_qt()[0]
    app = QApplication.instance() or QApplication([])
    window = KairnMainWindow()
    window.apply_startup_window_mode()
    app.exec()


if __name__ == '__main__':
    main()
