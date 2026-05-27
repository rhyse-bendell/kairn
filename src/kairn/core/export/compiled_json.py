from __future__ import annotations

import json
from collections import Counter, defaultdict

from ..analysis.indicators import compute_indicators_report
from ..analysis.timelines import build_timeline
from ..storage.repositories import _conn, get_collaboration, get_latest_run
from .records import fetch_enriched_events


def export_compiled(db_path, out_path, collection_id=None, run_id=None):
    conn = _conn(db_path)
    events = fetch_enriched_events(db_path, collection_id=collection_id, run_id=run_id)
    units = defaultdict(list)
    for e in events:
        units[e.get("unit") or "unknown"].append(e)
    timeline = build_timeline(db_path, collection_id=collection_id, run_id=run_id)
    collab = None
    if collection_id:
        row = conn.execute("select collaboration_id from collections where id=?", (collection_id,)).fetchone()
        if row and row[0]:
            collab = get_collaboration(db_path, row[0])
    payload = {
        "meta": {"db_path": db_path, "collection_id": collection_id, "run_id": run_id, "event_count": len(events)},
        "collaboration": collab,
        "collection": conn.execute("select * from collections where id=?", (collection_id,)).fetchone() if collection_id else None,
        "latest_run": get_latest_run(db_path, collection_id=collection_id),
        "global_events": events,
        "units": {
            u: {
                "unit": u,
                "artifact_ids": sorted({v.get("artifact_id") for v in rows if v.get("artifact_id")}),
                "artifact_kinds": sorted({v.get("artifact_kind") for v in rows if v.get("artifact_kind")}),
                "event_count": len(rows),
                "actors": sorted({v.get("actor_label") for v in rows if v.get("actor_label")}),
                "first_ts": rows[0].get("ts"),
                "last_ts": rows[-1].get("ts"),
                "latest_summary": rows[-1].get("summary"),
                "events": rows,
            }
            for u, rows in units.items()
        },
        "actors": dict(Counter((e.get("actor_label") or "unknown") for e in events)),
        "sessions": timeline.get("sessions", []),
        "artifacts": [dict(r) for r in conn.execute("select * from artifacts where collection_id=?", (collection_id,))] if collection_id else [],
        "deltas_summary": dict(Counter((e.get("delta_type") or "none") for e in events)),
        "warnings": [dict(r) for r in conn.execute('select * from ingestion_warnings')],
        "indicators_summary": compute_indicators_report(db_path, collection_id=collection_id),
        "generated_files": [],
    }
    if payload["collection"]:
        payload["collection"] = dict(payload["collection"])
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
    return out_path
