from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import sqlite3

_TIME_RE = re.compile(
    r"(?P<sh>\d{1,2}):(?P<sm>\d{2}):(?P<ss>\d{2})[,.](?P<sms>\d{3})\s*-->\s*"
    r"(?P<eh>\d{1,2}):(?P<em>\d{2}):(?P<es>\d{2})[,.](?P<ems>\d{3})"
)
_SPEAKER_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 ._'’-]{0,60})\s*:\s*(.+)$", re.S)


def ensure_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        create table if not exists transcript_utterances(
            id integer primary key autoincrement,
            collection_id text,
            run_id text,
            source_path text not null,
            source_block_index integer not null,
            srt_sequence text,
            team_id text,
            participant_id text,
            speaker text,
            anchor_utc text,
            start_offset_s real,
            end_offset_s real,
            duration_s real,
            timestamp_utc text,
            timestamp_end_utc text,
            verbatim_text text,
            content_text text,
            warning text
        );
        create unique index if not exists idx_transcript_utterance_source
            on transcript_utterances(source_path, source_block_index, ifnull(collection_id,''));
        """
    )


def _offset_seconds(parts: tuple[str, str, str, str]) -> float:
    h, m, s, ms = (int(x) for x in parts)
    return h * 3600 + m * 60 + s + ms / 1000.0


def _parse_anchor(anchor_utc: str | None) -> datetime | None:
    if not anchor_utc:
        return None
    try:
        dt = datetime.fromisoformat(str(anchor_utc).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception as exc:
        raise ValueError(f"Invalid transcript anchor_utc: {anchor_utc!r}") from exc


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _split_blocks(text: str) -> list[list[str]]:
    blocks = []
    current: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw.strip():
            current.append(raw)
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def _speaker_and_content(verbatim: str) -> tuple[str | None, str]:
    m = _SPEAKER_RE.match(verbatim)
    if not m:
        return None, verbatim.strip()
    speaker = m.group(1).strip()
    content = m.group(2).strip()
    return speaker or None, content


def inspect_srt_transcript(path: str | Path) -> dict:
    p = Path(path)
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    blocks = _split_blocks(text)
    valid = 0
    malformed = 0
    speakers: set[str] = set()
    for block in blocks:
        time_idx = next((i for i, line in enumerate(block[:3]) if _TIME_RE.search(line)), None)
        if time_idx is None:
            malformed += 1
            continue
        valid += 1
        body = "\n".join(block[time_idx + 1 :]).strip()
        speaker, _ = _speaker_and_content(body)
        if speaker:
            speakers.add(speaker)
    return {
        "path": str(p),
        "block_count": len(blocks),
        "valid_timed_blocks": valid,
        "malformed_blocks": malformed,
        "explicit_speakers": sorted(speakers),
        "requires_anchor_for_cross_stream_sync": True,
    }


def parse_srt_transcript(
    path: str | Path,
    db_path: str | Path,
    collection_id: str | None = None,
    run_id: str | None = None,
    team_id: str | None = None,
    anchor_utc: str | None = None,
) -> dict:
    p = Path(path)
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    blocks = _split_blocks(text)
    anchor = _parse_anchor(anchor_utc)
    anchor_norm = _iso(anchor)
    warnings: list[str] = []

    conn = sqlite3.connect(str(db_path))
    ensure_tables(conn)

    # Remove any unified replay rows derived from an older parse of this source before
    # replacing utterance rows. This prevents stale/duplicate transcript events when
    # an anchor or team assignment is corrected and the transcript is reparsed.
    unified_exists = conn.execute(
        "select 1 from sqlite_master where type='table' and name='unified_process_events'"
    ).fetchone()
    if unified_exists:
        old_ids = [
            str(r[0])
            for r in conn.execute(
                "select id from transcript_utterances where source_path=? and ifnull(collection_id,'')=ifnull(?,'')",
                (str(p), collection_id),
            ).fetchall()
        ]
        if old_ids:
            placeholders = ",".join("?" for _ in old_ids)
            conn.execute(
                f"delete from unified_process_events where source_table='transcript_utterances' "
                f"and source_event_id in ({placeholders})",
                old_ids,
            )
    conn.execute(
        "delete from transcript_utterances where source_path=? and ifnull(collection_id,'')=ifnull(?,'')",
        (str(p), collection_id),
    )

    inserted = 0
    for block_index, block in enumerate(blocks, 1):
        time_idx = next((i for i, line in enumerate(block[:3]) if _TIME_RE.search(line)), None)
        if time_idx is None:
            warnings.append(f"Block {block_index}: no valid SRT timestamp line")
            continue
        match = _TIME_RE.search(block[time_idx])
        if match is None:
            warnings.append(f"Block {block_index}: malformed timestamp line")
            continue

        seq = block[0].strip() if time_idx > 0 else str(block_index)
        body = "\n".join(block[time_idx + 1 :]).strip()
        if not body:
            warnings.append(f"Block {block_index}: timed block has no text")
            continue

        start = _offset_seconds(
            (match["sh"], match["sm"], match["ss"], match["sms"])
        )
        end = _offset_seconds(
            (match["eh"], match["em"], match["es"], match["ems"])
        )
        warning = None
        if end < start:
            warning = "End timestamp precedes start timestamp"
            warnings.append(f"Block {block_index}: {warning}")

        speaker, content = _speaker_and_content(body)
        start_dt = anchor + timedelta(seconds=start) if anchor else None
        end_dt = anchor + timedelta(seconds=end) if anchor else None

        conn.execute(
            """
            insert into transcript_utterances(
                collection_id,run_id,source_path,source_block_index,srt_sequence,
                team_id,participant_id,speaker,anchor_utc,start_offset_s,end_offset_s,
                duration_s,timestamp_utc,timestamp_end_utc,verbatim_text,content_text,warning
            ) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                collection_id,
                run_id,
                str(p),
                block_index,
                seq,
                team_id,
                None,
                speaker,
                anchor_norm,
                start,
                end,
                max(0.0, end - start),
                _iso(start_dt),
                _iso(end_dt),
                body,
                content,
                warning,
            ),
        )
        inserted += 1

    conn.commit()
    conn.close()
    if anchor is None:
        warnings.append(
            "Transcript parsed without an absolute anchor; it can be inspected independently "
            "but cannot be synchronized to timestamped document/TLDraw activity."
        )
    return {
        "source_path": str(p),
        "source_blocks": len(blocks),
        "inserted": inserted,
        "collection_id": collection_id,
        "run_id": run_id,
        "team_id": team_id,
        "anchor_utc": anchor_norm,
        "warnings": warnings[:200],
    }
