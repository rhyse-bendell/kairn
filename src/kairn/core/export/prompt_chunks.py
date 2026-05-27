from __future__ import annotations

import gzip
import json
from collections import Counter
from pathlib import Path

from .records import compact_event, fetch_enriched_events


def export_prompt_chunks(db_path, out_dir, chunk_size=200, collection_id=None, run_id=None):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = fetch_enriched_events(db_path, collection_id=collection_id, run_id=run_id)
    paths = []
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i + chunk_size]
        actors = {r.get("actor_id"): r.get("actor_label") for r in chunk if r.get("actor_id")}
        units = Counter((r.get("unit") or "unknown") for r in chunk)
        warnings = sum(int(r.get("warning_count_for_artifact_or_unit") or 0) for r in chunk)
        payload = {
            "chunk_meta": {
                "chunk_index": i // chunk_size + 1,
                "chunk_size": len(chunk),
                "first_ts": chunk[0].get("ts") if chunk else None,
                "last_ts": chunk[-1].get("ts") if chunk else None,
            },
            "actor_map": actors,
            "unit_summary": dict(units),
            "warning_summary": {"warning_refs": warnings},
            "events": [compact_event(e) for e in chunk],
        }
        jpath = out / f'prompt_chunk_{i // chunk_size + 1:03d}.json'
        jpath.write_text(json.dumps(payload, indent=2), encoding='utf-8')
        gz = out / f'compact_chunk_{i // chunk_size + 1:03d}.jsonl.gz'
        with gzip.open(gz, 'wt', encoding='utf-8') as g:
            for e in chunk:
                g.write(json.dumps(compact_event(e), separators=(',', ':')) + '\n')
        paths.extend([str(jpath), str(gz)])
    return paths
