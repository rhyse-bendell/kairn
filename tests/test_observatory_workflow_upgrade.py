import sqlite3
from pathlib import Path

from kairn.core.observatory.source_processing import discover_observatory_sources, _process_discovered_sources
from kairn.core.observatory.report import build_observatory_report
from kairn.core.observatory.transcript_metrics import compute_transcript_metrics
from kairn.core.observatory.export import export_observatory_report
from kairn.core.observatory.schemas import ObservatoryReport, table_from_rows


def test_source_discovery(tmp_path):
    (tmp_path / "dailyLog.csv").write_text("time,user,action\n2024-01-01,Alice,create\n")
    team = tmp_path / "Team 1"; team.mkdir()
    (team / "foo_changelog.txt").write_text("Alice added text")
    (team / "labeledTranscriptions.srt").write_text("1\n00:00:01,000 --> 00:00:02,000\nAlice: hi\n")
    (tmp_path / "artifact.docx").write_text("fake")
    db = tmp_path / "TLDraw Logs.db"
    with sqlite3.connect(db) as c:
        c.execute("create table events (id text, timestamp text, actor text, action text)")
    kinds = {r["source_kind"] for r in discover_observatory_sources(tmp_path)}
    assert "drive_daily_log" in kinds
    assert "document_changelog" in kinds
    assert "tldraw_sqlite_db" in kinds or "unknown_file" in kinds
    assert "transcript_srt" in kinds
    assert "document_artifact" in kinds


def test_srt_processing_and_metrics(tmp_path):
    srt = tmp_path / "Team 1" / "labeledTranscriptions.srt"; srt.parent.mkdir()
    srt.write_text("""1
00:00:01,000 --> 00:00:04,000
Alice: We need to define the problem.

2
00:00:05,000 --> 00:00:07,500
Bob: The infrastructure issue matters.
""")
    db = tmp_path / "kairn.db"
    discovered = discover_observatory_sources(tmp_path)
    summary, warnings = _process_discovered_sources(discovered, str(db))
    assert not warnings
    with sqlite3.connect(db) as c:
        rows = c.execute("select speaker,duration_seconds,word_count from transcript_turn_events order by turn_index").fetchall()
    assert len(rows) == 2
    assert rows[0][0] == "Alice" and float(rows[0][1]) == 3.0
    assert rows[1][0] == "Bob" and int(rows[1][2]) == 4
    tables = compute_transcript_metrics({"project_root": str(tmp_path)}, str(db))
    ids = {t.table_id for t in tables}
    assert {"transcript_overall_counts", "transcript_speaker_summary", "transcript_team_summary", "transcript_turns_by_time_bin", "transcript_representative_snippets", "transcript_keyword_counts"} <= ids
    overall = next(t for t in tables if t.table_id == "transcript_overall_counts").rows[0]
    assert overall["total_turns"] == 2
    assert overall["unique_speakers"] == 2


def test_normalized_events_and_visualization_export(tmp_path):
    db = tmp_path / "kairn.db"
    with sqlite3.connect(db) as c:
        c.execute("create table drive_activity_events (timestamp_utc text, actor_id_or_user text, action text, file_id text, file_name text, mime_type text, source_path text)")
        c.execute("insert into drive_activity_events values ('2024-01-01T00:00:00Z','Alice','create','f1','doc','text/plain','dailyLog.csv')")
        c.execute("create table transcript_turn_events (source_path text, team_or_session text, speaker text, start_time text, end_time text, start_seconds text, end_seconds text, duration_seconds text, text text, word_count text, turn_index text)")
        c.execute("insert into transcript_turn_events values ('x.srt','Team 1','Bob','00:00:01,000','00:00:02,000','1','2','1','problem data','2','1')")
    report = build_observatory_report({"project_id":"p","name":"P","project_root":str(tmp_path)}, str(db))
    norm = next(t for t in report.tables if t.table_id == "normalized_observatory_events")
    assert {"drive", "transcript"} <= {r["source_stream"] for r in norm.rows}
    assert "event_id" in norm.columns and "source_kind" in norm.columns
    paths = export_observatory_report(report, tmp_path / "out")
    html = Path(paths["out_dir"]) / "visualizations" / "trace_ecology_overview.html"
    assert html.exists()
    text = html.read_text()
    assert "Trace Ecology Overview" in text
    assert "folder_inventory_summary" in text or "stream_record_counts" in text
    assert "http://" not in text and "https://" not in text
