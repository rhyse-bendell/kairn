from __future__ import annotations

import json
from collections import Counter

from ..storage.repositories import _conn


def actor_label(record: dict) -> str:
    return record.get("display_name") or record.get("pid_label") or record.get("actor_id") or "unknown"


def event_unit(record: dict) -> str:
    return record.get("unit") or record.get("artifact_rel_path") or "unknown"


def compact_event(record: dict) -> dict:
    return {
        "event_id": record.get("event_id"),
        "ts": record.get("ts"),
        "action": record.get("action"),
        "actor": record.get("actor_label"),
        "unit": event_unit(record),
        "artifact": record.get("artifact_rel_path"),
        "summary": record.get("summary"),
        "delta_type": record.get("delta_type"),
    }


def fetch_enriched_events(db_path: str, collection_id: str | None = None, run_id: str | None = None) -> list[dict]:
    conn = _conn(db_path)
    q = """
    select e.id as event_id, e.ts, e.action, e.actor as actor_id,
           p.pid_label, p.display_name,
           a.id as artifact_id, a.rel_path as artifact_rel_path, a.path as artifact_path, a.kind as artifact_kind,
           coalesce(e.mentioned_unit, a.rel_path) as unit,
           e.summary, e.raw_row, e.collection_id,
           d.delta_type, d.payload as delta_payload
    from events e
    left join artifacts a on a.id = e.artifact_id
    left join participants p on p.actor_id = e.actor
    left join deltas d on d.event_id = e.id
    where 1=1
    """
    params: list[str] = []
    if collection_id:
        q += " and e.collection_id=?"
        params.append(collection_id)
    if run_id:
        q += " and exists (select 1 from ingestion_warnings w where w.run_id=? and w.rel_path=a.rel_path)"
        params.append(run_id)
    q += " order by e.ts, e.id"
    rows = [dict(r) for r in conn.execute(q, tuple(params))]
    warning_counts = Counter((r["rel_path"] or "unknown") for r in conn.execute("select rel_path from ingestion_warnings"))
    out = []
    for r in rows:
        raw_row = r.get("raw_row")
        raw_obj = None
        if raw_row:
            try:
                raw_obj = json.loads(raw_row)
            except Exception:
                raw_obj = raw_row
        delta_payload = r.get("delta_payload")
        excerpt = None
        if delta_payload:
            excerpt = delta_payload[:280]
        rec = {
            "event_id": r.get("event_id"), "ts": r.get("ts"), "action": r.get("action"),
            "actor_id": r.get("actor_id"), "pid_label": r.get("pid_label"), "display_name": r.get("display_name"),
            "actor_label": actor_label(r), "artifact_id": r.get("artifact_id"), "artifact_rel_path": r.get("artifact_rel_path"),
            "artifact_path": r.get("artifact_path"), "artifact_kind": r.get("artifact_kind"), "unit": r.get("unit"),
            "summary": r.get("summary"), "raw_row": raw_obj, "delta_type": r.get("delta_type"),
            "delta_payload_excerpt": excerpt,
            "warning_count_for_artifact_or_unit": warning_counts.get(r.get("artifact_rel_path") or r.get("unit") or "unknown", 0),
            "collection_id": r.get("collection_id"), "run_id": run_id,
        }
        out.append(rec)
    return out
