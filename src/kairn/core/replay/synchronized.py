from __future__ import annotations

from datetime import datetime
from typing import Iterable

from .models import ReplayEvent


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def session_bounds(events: Iterable[ReplayEvent]) -> tuple[datetime | None, datetime | None]:
    times = [parse_timestamp(e.timestamp_utc) for e in events]
    times = [t for t in times if t is not None]
    return (min(times), max(times)) if times else (None, None)


def events_at_or_before(
    events: Iterable[ReplayEvent],
    cursor: datetime,
    source: str | None = None,
) -> list[ReplayEvent]:
    out = []
    for event in events:
        ts = parse_timestamp(event.timestamp_utc)
        if ts is None or ts > cursor:
            continue
        if source and event.source != source:
            continue
        out.append(event)
    return out


def active_transcript_event(
    events: Iterable[ReplayEvent],
    cursor: datetime,
) -> ReplayEvent | None:
    transcript = [e for e in events if e.source == "transcript" and parse_timestamp(e.timestamp_utc)]
    transcript.sort(key=lambda e: parse_timestamp(e.timestamp_utc))
    for event in transcript:
        start = parse_timestamp(event.timestamp_utc)
        end = parse_timestamp(event.timestamp_end_utc) or start
        if start and end and start <= cursor <= end:
            return event
        if start and start > cursor:
            break
    return None


def transcript_context(
    events: Iterable[ReplayEvent],
    cursor: datetime,
    before: int = 2,
    after: int = 2,
) -> tuple[ReplayEvent | None, list[ReplayEvent]]:
    transcript = [e for e in events if e.source == "transcript" and parse_timestamp(e.timestamp_utc)]
    transcript.sort(key=lambda e: parse_timestamp(e.timestamp_utc))
    active = active_transcript_event(transcript, cursor)
    if not transcript:
        return None, []
    if active is not None:
        idx = transcript.index(active)
    else:
        idx = 0
        for i, event in enumerate(transcript):
            start = parse_timestamp(event.timestamp_utc)
            if start and start <= cursor:
                idx = i
            elif start and start > cursor:
                break
    lo = max(0, idx - max(0, before))
    hi = min(len(transcript), idx + max(0, after) + 1)
    return active, transcript[lo:hi]


def board_state_from_events(
    events: Iterable[ReplayEvent],
    cursor: datetime,
) -> list[ReplayEvent]:
    state: dict[str, ReplayEvent] = {}
    for event in events:
        if event.source != "tldraw":
            continue
        ts = parse_timestamp(event.timestamp_utc)
        if ts is None or ts > cursor:
            continue
        key = event.artifact_ref or event.source_event_id or event.replay_event_id
        if str(event.action or "").lower() in {"delete", "deleted"}:
            state.pop(key, None)
        else:
            state[key] = event
    return list(state.values())


def document_state_from_events(
    events: Iterable[ReplayEvent],
    cursor: datetime,
    recent_per_document: int = 3,
) -> list[dict]:
    grouped: dict[str, list[ReplayEvent]] = {}
    for event in events:
        if event.source not in {"document", "drive"}:
            continue
        ts = parse_timestamp(event.timestamp_utc)
        if ts is None or ts > cursor:
            continue
        key = event.artifact_ref or event.metadata.get("document_name") or event.replay_event_id
        grouped.setdefault(str(key), []).append(event)

    rows = []
    for key, changes in grouped.items():
        changes.sort(key=lambda e: parse_timestamp(e.timestamp_utc))
        latest = changes[-1]
        rows.append(
            {
                "artifact_ref": key,
                "latest": latest,
                "recent": changes[-max(1, recent_per_document) :],
                "event_count": len(changes),
                "observability": (
                    "change trace only"
                    if any(e.source == "document" for e in changes)
                    else "file activity only"
                ),
            }
        )
    rows.sort(key=lambda r: parse_timestamp(r["latest"].timestamp_utc), reverse=True)
    return rows


def events_near_cursor(
    events: Iterable[ReplayEvent],
    cursor: datetime,
    window_seconds: float = 30.0,
    limit: int = 100,
) -> list[ReplayEvent]:
    near = []
    for event in events:
        ts = parse_timestamp(event.timestamp_utc)
        if ts is None:
            continue
        delta = abs((ts - cursor).total_seconds())
        if delta <= window_seconds:
            near.append((delta, ts, event))
    near.sort(key=lambda x: (x[1], x[0]))
    return [e for _, _, e in near[:limit]]
