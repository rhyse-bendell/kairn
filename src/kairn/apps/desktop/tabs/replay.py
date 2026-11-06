from __future__ import annotations
import json

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTextEdit,
    QComboBox,
    QLineEdit,
    QSlider,
    QLabel,
    QSplitter,
    QFileDialog,
    QGroupBox,
    QTabWidget,
)

from kairn.core.replay import load_replay_events, get_replay_summary
from kairn.core.replay.summaries import event_density
from kairn.core.sources import detect_compatible_source
from ..widgets import (
    set_table_rows,
    append_log,
    page_header,
    primary_action_button,
    secondary_action_button,
)
from ..synchronized_replay import SynchronizedReplayView
from .timeline import TimelineTab


class ReplayTab(QWidget):
    def __init__(self, state, log):
        super().__init__()
        self.state = state
        self.log = log
        self.events = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._timer_tick)

        l = QVBoxLayout(self)
        l.addWidget(
            page_header(
                "Replay",
                "Replay parsed collaboration events or inspect synchronized speech, diagram, document, and activity spaces.",
                "Load Replay Events",
            )
        )

        top = QHBoxLayout()
        self.source = QComboBox()
        self.source.addItems(["All", "unified", "tldraw", "drive", "document", "transcript", "generic"])
        self.team = QLineEdit()
        self.team.setPlaceholderText("Team filter")
        self.part = QLineEdit()
        self.part.setPlaceholderText("Participant filter")
        for txt, fn in [
            ("Select File or Folder", self.select_source),
            ("Load Events", self.load),
            ("Play", self.play),
            ("Pause", self.pause),
            ("Step Back", self.step_back),
            ("Step Forward", self.step_forward),
        ]:
            b = primary_action_button(txt) if txt == "Load Events" else secondary_action_button(txt)
            b.clicked.connect(fn)
            top.addWidget(b)
        self.speed = QComboBox()
        self.speed.addItems(["slow", "normal", "fast"])
        top.addWidget(QLabel("Source"))
        top.addWidget(self.source)
        top.addWidget(self.team)
        top.addWidget(self.part)
        top.addWidget(self.speed)
        l.addLayout(top)

        self.views = QTabWidget()
        self.views.addTab(self._build_event_inspector(), "Event Inspector")
        self.sync = SynchronizedReplayView(state, log)
        self.views.addTab(self.sync, "Synchronized Workspaces")
        l.addWidget(self.views)
        self._empty()

    def _build_event_inspector(self):
        page = QWidget()
        l = QVBoxLayout(page)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.valueChanged.connect(self.show_index)
        l.addWidget(self.slider)

        lab = QHBoxLayout()
        self.ts = QLabel("Timestamp: —")
        self.idx = QLabel("Event: 0/0")
        lab.addWidget(self.ts)
        lab.addWidget(self.idx)
        l.addLayout(lab)

        split = QSplitter(Qt.Vertical)
        self.table = QTableWidget()
        self.table.itemSelectionChanged.connect(self.table_selected)
        split.addWidget(self.table)

        lower = QSplitter(Qt.Horizontal)
        self.callout = QTextEdit()
        self.callout.setReadOnly(True)
        self.detect = QTextEdit()
        self.detect.setReadOnly(True)
        lower.addWidget(self.callout)

        self.actor = QTableWidget()
        self.src = QTableWidget()
        self.action = QTableWidget()
        self.obj = QTableWidget()
        self.density = QTableWidget()
        sums = QSplitter(Qt.Vertical)
        for w in [self.actor, self.src, self.action, self.obj, self.density]:
            sums.addWidget(w)
        lower.addWidget(sums)
        lower.addWidget(self.detect)
        split.addWidget(lower)

        timeline_box = QGroupBox("Timeline / Sessions")
        timeline_layout = QVBoxLayout(timeline_box)
        self.timeline = TimelineTab(self.state, self.log)
        timeline_layout.addWidget(self.timeline)
        split.addWidget(timeline_box)

        l.addWidget(split)
        return page

    def _empty(self):
        set_table_rows(
            self.table,
            [],
            [
                "sequence_index",
                "timestamp_utc",
                "team_id",
                "actor_label",
                "source",
                "action",
                "object_type",
                "artifact_ref",
                "summary",
            ],
        )
        self.callout.setText("Load replay events to begin.")

    def _dialog_start_dir(self):
        from pathlib import Path

        if self.state.has_active_project():
            return str(Path(self.state.active_project_root) / "data" / "original")
        return getattr(self.state, "last_import_dir", None) or self.state.project_home

    def select_source(self):
        p = (
            QFileDialog.getOpenFileName(
                self, "Select compatible file", self._dialog_start_dir(), "All Files (*)"
            )[0]
            or QFileDialog.getExistingDirectory(
                self, "Select compatible folder", self._dialog_start_dir()
            )
        )
        if p:
            res = detect_compatible_source(p)
            self.detect.setText(json.dumps(res, indent=2))
            append_log(self.log, "Source detection: " + json.dumps(res))

    def load(self):
        src = None if self.source.currentText() in ("All", "unified") else [self.source.currentText()]
        self.events = load_replay_events(
            self.state.db_path,
            self.state.active_collection_id,
            self.state.last_run_id,
            src,
            self.team.text() or None,
            self.part.text() or None,
        )
        rows = [e.to_dict() for e in self.events]
        set_table_rows(
            self.table,
            rows,
            [
                "sequence_index",
                "timestamp_utc",
                "team_id",
                "actor_label",
                "source",
                "action",
                "object_type",
                "artifact_ref",
                "summary",
            ],
        )
        self.slider.setRange(0, max(0, len(self.events) - 1))
        self.slider.setValue(0)
        self._summaries()
        self.sync.set_events(self.events)
        self.show_index(0)
        append_log(self.log, f"Loaded {len(self.events)} replay events")

    def _kv(self, t, d):
        set_table_rows(t, [{"key": k, "count": v} for k, v in d.items()], ["key", "count"])

    def _summaries(self):
        s = get_replay_summary(self.events)
        self._kv(self.actor, s["counts_by_actor"])
        self._kv(self.src, s["counts_by_source"])
        self._kv(self.action, s["counts_by_action"])
        self._kv(self.obj, s["counts_by_object_type"])
        set_table_rows(
            self.density,
            event_density(self.events),
            ["bin_index", "start_offset_minutes", "count"],
        )

    def show_index(self, i):
        if not self.events:
            self._empty()
            self.idx.setText("Event: 0/0")
            return
        i = max(0, min(i, len(self.events) - 1))
        e = self.events[i]
        self.ts.setText(f"Timestamp: {e.timestamp_utc or '—'}")
        self.idx.setText(f"Event: {i + 1}/{len(self.events)}")
        meta = json.dumps(e.metadata, indent=2, default=str)
        tl = ""
        if e.source == "tldraw":
            tl = (
                f"\n\nTLDraw Object Info"
                f"\nroom/team: {e.metadata.get('room_id') or e.team_id}"
                f"\nentity/action/type: {e.metadata.get('entity')}/{e.action}/"
                f"{e.metadata.get('entity_type') or e.object_type}"
                f"\nsource: {e.metadata.get('source')}"
                f"\nshape text: {e.content_text}"
                f"\nx/y/w/h: {e.x}/{e.y}/{e.width}/{e.height}"
                f"\nApproximation: At x={e.x}, y={e.y}, {e.actor_label} {e.action} "
                f"a {e.object_type} containing {e.content_text!r}."
            )
        self.callout.setText(
            f"{e.callout_title}\n\n{e.callout_body}\n\n"
            f"Content: {e.content_text or ''}\n\nMetadata/provenance:\n{meta}{tl}"
        )
        if e.timestamp_utc:
            self.sync.set_cursor_timestamp(e.timestamp_utc)

    def table_selected(self):
        r = self.table.currentRow()
        if r >= 0 and r != self.slider.value():
            self.slider.setValue(r)

    def _sync_mode(self):
        return self.views.currentWidget() is self.sync

    def play(self):
        if self._sync_mode():
            interval = {"slow": 1000, "normal": 250, "fast": 100}.get(
                self.speed.currentText(), 250
            )
        else:
            interval = {"slow": 1500, "normal": 700, "fast": 200}.get(
                self.speed.currentText(), 700
            )
        self.timer.start(interval)

    def pause(self):
        self.timer.stop()

    def step_back(self):
        if self._sync_mode():
            self.sync.step_time(-1)
        else:
            self.slider.setValue(max(0, self.slider.value() - 1))

    def step_forward(self):
        if self._sync_mode():
            if not self.sync.step_time(1):
                self.pause()
        else:
            if self.slider.value() >= len(self.events) - 1:
                self.pause()
                return
            self.slider.setValue(self.slider.value() + 1)

    def _timer_tick(self):
        if self._sync_mode():
            seconds = {"slow": 1, "normal": 2, "fast": 10}.get(self.speed.currentText(), 2)
            if not self.sync.step_time(seconds) or self.sync.at_end():
                self.pause()
        else:
            self.step_forward()
