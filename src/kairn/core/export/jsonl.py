from __future__ import annotations

import gzip
import json

from .records import compact_event, fetch_enriched_events


def export_jsonl(db_path, out_path, compact_gz=None, collection_id=None, run_id=None):
    events = fetch_enriched_events(db_path, collection_id=collection_id, run_id=run_id)
    with open(out_path, 'w', encoding='utf-8') as f:
        for e in events:
            f.write(json.dumps(e) + '\n')
    if compact_gz:
        with gzip.open(compact_gz, 'wt', encoding='utf-8') as g:
            for e in events:
                g.write(json.dumps(compact_event(e), separators=(',', ':')) + '\n')
    return out_path
