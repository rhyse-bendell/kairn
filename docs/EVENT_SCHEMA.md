# Event Schema
Canonical records: collection, artifact, version, event, delta, representation, participant, run.
Event logic is actor-time-artifact-action with optional mentioned unit and summary.
Inferred indicators are observational activity proxies, not direct measures of cognition.


## Notes
- Artifact identity is collection-aware: `(collection_id, rel_path)`.
- Event model follows actor-time-artifact-action with optional unit/summary/raw row fields.
- Compiled exports provide global events and unit summaries.
- Indicators are trace-based cautionary signals, not direct cognition measurement.

## Enriched event export fields
Event exports include actor labels, artifact metadata, unit, delta hints, and warning counts for re-entry oriented analysis.

## Workshop Process Data Tables

### `raw_tldraw_events`
Raw normalized copy of TLDraw SQLite `audit_logs`, including source database path, source row id, collection/run ids, actor/source/room fields, millisecond timestamp, UTC timestamp, and exact payload JSON.

### `parsed_tldraw_events`
One parsed row per raw TLDraw event. Includes `raw_event_id` provenance, team/room/participant fields, sequence and relative time, shape text, geometry, style fields, binding/arrow references, user-origin flag, and raw payload excerpt.

### `drive_activity_events`
Rows parsed from workshop `dailyLog.csv`, preserving original Drive values while adding inferred team, participant, and task module hints.

### `document_edit_events`
Rows parsed from `*changelog*.txt` files. Supports ISO Drive-style rows and bracketed document edit/delete rows. Stores raw row, actor, action, timestamp text/UTC when available, text snippet, and inferred team/participant.

### `unified_process_events`
Combined chronological stream across TLDraw, Drive, and document tables. Stores source table/id provenance JSON, team/participant fields, artifact stream, timestamps, event sequence index, relative time, action, object type, content text, and summary.

### `board_snapshots`
Minimal TLDraw board-state snapshots with team/room, snapshot timestamp, event index, object/node/arrow/binding counts, and JSON payload containing reconstructed object keys.
