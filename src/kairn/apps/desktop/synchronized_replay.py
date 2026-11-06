from __future__ import annotations

from datetime import timedelta

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QPen
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QSplitter,
    QGroupBox,
    QTextEdit,
    QGraphicsView,
    QGraphicsScene,
    QTableWidget,
)

from kairn.core.replay.synchronized import (
    session_bounds,
    parse_timestamp,
    transcript_context,
    board_state_from_events,
    document_state_from_events,
    events_near_cursor,
)
from .widgets import set_table_rows


class SynchronizedReplayView(QWidget):
    """Time-synchronized inspection of speech, board state, document traces, and activity."""

    def __init__(self, state, log):
        super().__init__()
        self.state = state
        self.log = log
        self.events = []
        self.start_dt = None
        self.end_dt = None
        self._setting_cursor = False

        root = QVBoxLayout(self)
        self.status = QLabel(
            "Load replay events to inspect synchronized collaboration spaces. "
            "Each pane reports only what its source can actually reconstruct."
        )
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        clock_row = QHBoxLayout()
        self.clock = QLabel("Time: —")
        self.offset = QLabel("+0:00")
        clock_row.addWidget(self.clock)
        clock_row.addStretch(1)
        clock_row.addWidget(self.offset)
        root.addLayout(clock_row)

        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setRange(0, 0)
        self.time_slider.valueChanged.connect(self._slider_changed)
        root.addWidget(self.time_slider)

        outer = QSplitter(Qt.Vertical)
        upper = QSplitter(Qt.Horizontal)

        speech_box = QGroupBox("Speech — transcript evidence")
        speech_layout = QVBoxLayout(speech_box)
        self.speech_status = QLabel("No synchronized transcript loaded.")
        self.speech_status.setWordWrap(True)
        self.speech = QTextEdit()
        self.speech.setReadOnly(True)
        speech_layout.addWidget(self.speech_status)
        speech_layout.addWidget(self.speech)
        upper.addWidget(speech_box)

        diagram_box = QGroupBox("Diagram — reconstructed TLDraw state")
        diagram_layout = QVBoxLayout(diagram_box)
        self.diagram_status = QLabel("No diagram state reconstructed.")
        self.diagram_status.setWordWrap(True)
        self.diagram_scene = QGraphicsScene(self)
        self.diagram = QGraphicsView(self.diagram_scene)
        diagram_layout.addWidget(self.diagram_status)
        diagram_layout.addWidget(self.diagram)
        upper.addWidget(diagram_box)

        docs_box = QGroupBox("Documents — observed change traces")
        docs_layout = QVBoxLayout(docs_box)
        self.docs_status = QLabel(
            "Document changelogs generally identify changes, not complete historical document snapshots."
        )
        self.docs_status.setWordWrap(True)
        self.documents = QTextEdit()
        self.documents.setReadOnly(True)
        docs_layout.addWidget(self.docs_status)
        docs_layout.addWidget(self.documents)
        upper.addWidget(docs_box)

        outer.addWidget(upper)

        activity_box = QGroupBox("Activity near the current time (±30 seconds)")
        activity_layout = QVBoxLayout(activity_box)
        self.activity = QTableWidget()
        activity_layout.addWidget(self.activity)
        outer.addWidget(activity_box)
        root.addWidget(outer)

    def set_events(self, events):
        self.events = list(events)
        self.start_dt, self.end_dt = session_bounds(self.events)
        if self.start_dt is None or self.end_dt is None:
            self.time_slider.setRange(0, 0)
            self.status.setText(
                "No absolute timestamps are available for synchronized replay. "
                "An SRT transcript needs an absolute anchor before it can align with other streams."
            )
            self.refresh()
            return
        duration = max(0, int((self.end_dt - self.start_dt).total_seconds()))
        self.time_slider.setRange(0, duration)
        self.time_slider.setValue(0)
        self.status.setText(
            "Synchronized view: speech, TLDraw state, document/file activity, and nearby events share one clock. "
            "Absence of activity means only that no event is present in the available trace."
        )
        self.refresh()

    def cursor_datetime(self):
        if self.start_dt is None:
            return None
        return self.start_dt + timedelta(seconds=self.time_slider.value())

    def set_cursor_timestamp(self, timestamp_utc):
        ts = parse_timestamp(timestamp_utc)
        if ts is None or self.start_dt is None or self.end_dt is None:
            return
        seconds = int((ts - self.start_dt).total_seconds())
        seconds = max(0, min(seconds, self.time_slider.maximum()))
        self._setting_cursor = True
        self.time_slider.setValue(seconds)
        self._setting_cursor = False
        self.refresh()

    def step_time(self, seconds=1):
        if self.time_slider.maximum() <= 0:
            return False
        old = self.time_slider.value()
        new = max(0, min(self.time_slider.maximum(), old + int(seconds)))
        self.time_slider.setValue(new)
        return new != old

    def at_end(self):
        return self.time_slider.value() >= self.time_slider.maximum()

    def _slider_changed(self, _value):
        if not self._setting_cursor:
            self.refresh()

    def refresh(self):
        cursor = self.cursor_datetime()
        if cursor is None:
            self.clock.setText("Time: —")
            self.offset.setText("+0:00")
            self.speech.clear()
            self.documents.clear()
            self.diagram_scene.clear()
            set_table_rows(
                self.activity,
                [],
                ["timestamp_utc", "source", "actor_label", "action", "artifact_ref", "content_text"],
            )
            return

        self.clock.setText(f"Time: {cursor.isoformat()}")
        seconds = self.time_slider.value()
        self.offset.setText(f"+{seconds // 60}:{seconds % 60:02d}")
        self._refresh_speech(cursor)
        self._refresh_diagram(cursor)
        self._refresh_documents(cursor)
        self._refresh_activity(cursor)

    def _refresh_speech(self, cursor):
        transcript_events = [e for e in self.events if e.source == "transcript"]
        anchored = [e for e in transcript_events if parse_timestamp(e.timestamp_utc)]
        unanchored = len(transcript_events) - len(anchored)
        active, context = transcript_context(self.events, cursor, before=2, after=2)
        if not transcript_events:
            self.speech_status.setText("No transcript events are loaded for this replay.")
            self.speech.setText("No observed speech stream.")
            return
        if not anchored:
            self.speech_status.setText(
                "Transcript is present but has no absolute anchor, so it cannot be aligned to this clock."
            )
            self.speech.setText("Parse/reparse the SRT with the recording start time as --anchor-utc.")
            return
        suffix = f" ({unanchored} unanchored utterances omitted)" if unanchored else ""
        if active is None:
            self.speech_status.setText("No speech turn is active at this moment." + suffix)
        else:
            self.speech_status.setText(
                f"Current observed speaker: {active.actor_label or 'Unknown speaker'}" + suffix
            )
        lines = []
        for event in context:
            marker = "▶" if active and event.replay_event_id == active.replay_event_id else " "
            ts = event.timestamp_utc or "—"
            speaker = event.actor_label or "Unknown"
            text = event.content_text or ""
            lines.append(f"{marker} {ts}  {speaker}: {text}")
        self.speech.setText("\n\n".join(lines) if lines else "No transcript context at this time.")

    def _refresh_diagram(self, cursor):
        state = board_state_from_events(self.events, cursor)
        self.diagram_scene.clear()
        if not state:
            self.diagram_status.setText("No TLDraw objects are reconstructable at this time.")
            self.diagram_scene.addText("No reconstructed diagram state")
            return

        positioned = 0
        unpositioned = []
        for event in state[:400]:
            x, y = event.x, event.y
            w = event.width if event.width not in (None, 0) else 140.0
            h = event.height if event.height not in (None, 0) else 50.0
            label = (event.content_text or event.object_type or "object").strip()
            if x is None or y is None:
                unpositioned.append(label)
                continue
            kind = str(event.object_type or "").lower()
            if "arrow" in kind or "line" in kind:
                self.diagram_scene.addLine(float(x), float(y), float(x) + float(w), float(y) + float(h), QPen())
            else:
                self.diagram_scene.addRect(float(x), float(y), float(w), float(h), QPen(), QBrush())
                text_item = self.diagram_scene.addText(label[:120])
                text_item.setPos(float(x) + 4, float(y) + 4)
            positioned += 1

        if positioned == 0:
            self.diagram_scene.addText("\n".join(unpositioned[:20]) or "Objects lack drawable geometry.")
        rect = self.diagram_scene.itemsBoundingRect()
        if rect.isValid() and not rect.isEmpty():
            self.diagram.fitInView(rect, Qt.KeepAspectRatio)
        extra = f"; {len(unpositioned)} objects lack drawable geometry" if unpositioned else ""
        self.diagram_status.setText(
            f"Reconstructed from {len(state)} extant TLDraw objects at the cursor{extra}."
        )

    def _refresh_documents(self, cursor):
        docs = document_state_from_events(self.events, cursor, recent_per_document=3)
        if not docs:
            self.documents.setText("No document or Drive activity observed before this time.")
            return
        chunks = []
        for row in docs[:20]:
            latest = row["latest"]
            chunks.append(
                f"{row['artifact_ref']}\n"
                f"  Observability: {row['observability']}\n"
                f"  Last observed change: {latest.timestamp_utc or '—'} — "
                f"{latest.actor_label or 'Unknown'} — {latest.action or 'activity'}\n"
                f"  Latest observed content/snippet: {latest.content_text or '(content unavailable)'}"
            )
            if len(row["recent"]) > 1:
                chunks.append("  Recent trace:")
                for event in row["recent"]:
                    chunks.append(
                        f"    • {event.timestamp_utc or '—'} | {event.actor_label or 'Unknown'} | "
                        f"{event.action or 'activity'} | {event.content_text or '(content unavailable)'}"
                    )
        self.documents.setText("\n".join(chunks))

    def _refresh_activity(self, cursor):
        events = events_near_cursor(self.events, cursor, window_seconds=30)
        rows = [
            {
                "timestamp_utc": e.timestamp_utc,
                "source": e.source,
                "actor_label": e.actor_label,
                "action": e.action,
                "artifact_ref": e.artifact_ref,
                "content_text": e.content_text,
            }
            for e in events
        ]
        set_table_rows(
            self.activity,
            rows,
            ["timestamp_utc", "source", "actor_label", "action", "artifact_ref", "content_text"],
        )
