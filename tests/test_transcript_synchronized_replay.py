import sqlite3
from datetime import datetime, timezone

from kairn.core.transcripts import parse_srt_transcript, inspect_srt_transcript
from kairn.core.sources import detect_compatible_source
from kairn.core.replay import load_replay_events
from kairn.core.replay.models import ReplayEvent
from kairn.core.process.unified_events import build_unified_process_events
from kairn.core.replay.synchronized import (
    transcript_context,
    board_state_from_events,
    document_state_from_events,
    events_near_cursor,
)


def _srt_text():
    return """1
00:00:01,000 --> 00:00:03,000
Alex: We could think about
nature-based solutions.

2
00:00:04,000 --> 00:00:06,500
Blair: Maybe greenspace could help reduce heat.

3
00:00:07,000 --> 00:00:08,000
What about tree planting?

BAD BLOCK
no timestamp here
"""


def test_srt_detection_inspection_and_parse(tmp_path):
    srt = tmp_path / "Team 2 transcript.srt"
    srt.write_text(_srt_text(), encoding="utf-8")
    detected = detect_compatible_source(str(srt))
    assert detected["compatible"] is True
    assert detected["source_type"] == "clean_transcript"
    assert detected["detected_handlers"][0]["handler"] == "transcript_srt"

    inspected = inspect_srt_transcript(srt)
    assert inspected["valid_timed_blocks"] == 3
    assert inspected["malformed_blocks"] == 1
    assert inspected["explicit_speakers"] == ["Alex", "Blair"]

    db = tmp_path / "kairn.db"
    result = parse_srt_transcript(
        srt,
        db,
        collection_id="c1",
        run_id="r1",
        team_id="Team 2",
        anchor_utc="2026-06-11T13:00:00Z",
    )
    assert result["inserted"] == 3
    assert any("no valid SRT timestamp" in w for w in result["warnings"])

    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    rows = c.execute("select * from transcript_utterances order by source_block_index").fetchall()
    c.close()
    assert len(rows) == 3
    assert rows[0]["speaker"] == "Alex"
    assert rows[0]["content_text"] == "We could think about\nnature-based solutions."
    assert rows[0]["verbatim_text"].startswith("Alex:")
    assert rows[0]["timestamp_utc"] == "2026-06-11T13:00:01Z"
    assert rows[0]["timestamp_end_utc"] == "2026-06-11T13:00:03Z"
    assert rows[2]["speaker"] is None


def test_unanchored_srt_is_preserved_but_not_given_fake_absolute_time(tmp_path):
    srt = tmp_path / "transcript.srt"
    srt.write_text(_srt_text(), encoding="utf-8")
    db = tmp_path / "kairn.db"
    result = parse_srt_transcript(srt, db, collection_id="c1")
    assert result["inserted"] == 3
    assert any("without an absolute anchor" in w for w in result["warnings"])

    c = sqlite3.connect(db)
    row = c.execute("select timestamp_utc,start_offset_s from transcript_utterances order by id limit 1").fetchone()
    c.close()
    assert row[0] is None
    assert row[1] == 1.0


def test_transcript_rows_load_as_replay_events(tmp_path):
    srt = tmp_path / "transcript.srt"
    srt.write_text(_srt_text(), encoding="utf-8")
    db = tmp_path / "kairn.db"
    parse_srt_transcript(
        srt,
        db,
        collection_id="c1",
        team_id="Team 2",
        anchor_utc="2026-06-11T13:00:00Z",
    )
    events = load_replay_events(db, collection_id="c1", sources=["transcript"])
    assert len(events) == 3
    assert events[0].source == "transcript"
    assert events[0].actor_label == "Alex"
    assert events[0].timestamp_end_utc == "2026-06-11T13:00:03Z"
    assert events[0].action == "spoke"


def test_synchronized_helpers_reconstruct_observable_spaces():
    events = [
        ReplayEvent(
            replay_event_id="tr:1",
            source="transcript",
            timestamp_utc="2026-06-11T13:00:01Z",
            timestamp_end_utc="2026-06-11T13:00:03Z",
            actor_label="Alex",
            content_text="Nature-based solutions",
        ),
        ReplayEvent(
            replay_event_id="tl:1",
            source="tldraw",
            source_event_id="1",
            timestamp_utc="2026-06-11T13:00:02Z",
            action="create",
            artifact_ref="shape-1",
            object_type="text",
            content_text="Greenspace",
            x=10,
            y=20,
            width=100,
            height=40,
        ),
        ReplayEvent(
            replay_event_id="doc:1",
            source="document",
            timestamp_utc="2026-06-11T13:00:02Z",
            actor_label="Blair",
            action="EDIT",
            artifact_ref="Team Framing",
            content_text="tree canopy",
        ),
        ReplayEvent(
            replay_event_id="tl:2",
            source="tldraw",
            source_event_id="2",
            timestamp_utc="2026-06-11T13:00:05Z",
            action="delete",
            artifact_ref="shape-1",
            object_type="text",
        ),
    ]

    cursor = datetime(2026, 6, 11, 13, 0, 2, tzinfo=timezone.utc)
    active, context = transcript_context(events, cursor)
    assert active is not None
    assert active.actor_label == "Alex"
    assert context[0].content_text == "Nature-based solutions"

    gap_cursor = datetime(2026, 6, 11, 13, 0, 4, tzinfo=timezone.utc)
    gap_active, gap_context = transcript_context(events, gap_cursor)
    assert gap_active is None
    assert gap_context

    board = board_state_from_events(events, cursor)
    assert len(board) == 1
    assert board[0].content_text == "Greenspace"

    docs = document_state_from_events(events, cursor)
    assert len(docs) == 1
    assert docs[0]["observability"] == "change trace only"
    assert docs[0]["latest"].content_text == "tree canopy"

    near = events_near_cursor(events, cursor, window_seconds=1)
    assert {e.source for e in near} == {"transcript", "tldraw", "document"}

    after_delete = datetime(2026, 6, 11, 13, 0, 6, tzinfo=timezone.utc)
    assert board_state_from_events(events, after_delete) == []


def test_reparse_clears_stale_unified_transcript_rows(tmp_path):
    srt = tmp_path / "transcript.srt"
    srt.write_text(_srt_text(), encoding="utf-8")
    db = tmp_path / "kairn.db"
    parse_srt_transcript(
        srt,
        db,
        collection_id="c1",
        anchor_utc="2026-06-11T13:00:00Z",
    )

    c = sqlite3.connect(db)
    c.execute(
        """create table unified_process_events(
        id integer primary key autoincrement, collection_id text, source_table text,
        source_event_id text, event_source text
        )"""
    )
    utterance_id = c.execute("select id from transcript_utterances order by id limit 1").fetchone()[0]
    c.execute(
        "insert into unified_process_events(collection_id,source_table,source_event_id,event_source) values(?,?,?,?)",
        ("c1", "transcript_utterances", str(utterance_id), "transcript"),
    )
    c.commit()
    c.close()

    parse_srt_transcript(
        srt,
        db,
        collection_id="c1",
        anchor_utc="2026-06-11T14:00:00Z",
    )
    c = sqlite3.connect(db)
    stale = c.execute(
        "select count(*) from unified_process_events where source_table='transcript_utterances'"
    ).fetchone()[0]
    first_ts = c.execute(
        "select timestamp_utc from transcript_utterances order by id limit 1"
    ).fetchone()[0]
    c.close()
    assert stale == 0
    assert first_ts == "2026-06-11T14:00:01Z"


def test_unified_process_events_include_transcript_end_time(tmp_path):
    srt = tmp_path / "transcript.srt"
    srt.write_text(_srt_text(), encoding="utf-8")
    db = tmp_path / "kairn.db"
    parse_srt_transcript(
        srt,
        db,
        collection_id="c1",
        run_id="r1",
        team_id="Team 2",
        anchor_utc="2026-06-11T13:00:00Z",
    )
    result = build_unified_process_events(db, collection_id="c1", run_id="r1")
    assert result["count"] == 3

    c = sqlite3.connect(db)
    rows = c.execute(
        "select event_source,timestamp_utc,timestamp_end_utc,participant_name,content_text "
        "from unified_process_events order by timestamp_utc"
    ).fetchall()
    c.close()
    assert rows[0][0] == "transcript"
    assert rows[0][1] == "2026-06-11T13:00:01Z"
    assert rows[0][2] == "2026-06-11T13:00:03Z"
    assert rows[0][3] == "Alex"
    assert "nature-based solutions" in rows[0][4]
