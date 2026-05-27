from __future__ import annotations

import traceback
from PySide6.QtCore import QThread, Signal


class TaskWorker(QThread):
    started_task = Signal(str)
    progress = Signal(str)
    finished_task = Signal(object)
    failed_task = Signal(str)

    def __init__(self, name: str, fn, *args, **kwargs):
        super().__init__()
        self.name = name
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        self.started_task.emit(self.name)
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.finished_task.emit(result)
        except Exception:
            self.failed_task.emit(traceback.format_exc())
