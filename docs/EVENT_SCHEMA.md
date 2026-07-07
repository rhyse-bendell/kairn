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

## `ReplayEvent`

`ReplayEvent` is an in-memory normalized view used by the replay backend and desktop workbench. It is derived preferentially from `unified_process_events`; when that table is unavailable or empty, Kairn falls back to `parsed_tldraw_events`, `drive_activity_events`, `document_edit_events`, and the generic `events` table.

Fields include `replay_event_id`, `source`, `source_table`, `source_event_id`, `timestamp_utc`, `relative_time_s`, `sequence_index`, `team_id`, `participant_id`, `participant_name`, `actor_label`, `action`, `object_type`, `artifact_stream`, `artifact_ref`, `content_text`, `summary`, `callout_title`, `callout_body`, optional geometry (`x`, `y`, `width`, `height`), and `metadata` containing source provenance. Replay events do not replace stored process-event tables; they provide a chronological, UI-friendly projection with generated callouts and contribution summaries.

## Source Detection Result Schema

`detect_compatible_source(path)` returns a dictionary with:

- `path`: inspected path.
- `kind`: broad container type such as `archive`, `folder`, `sqlite`, `csv`, `text`, `html`, `document`, or `slides`.
- `source_type`: dataset-specific type such as `workshop_archive`, `workshop_root_folder`, `tldraw_sqlite_log`, `drive_activity_log`, `document_changelog`, `drive_folder_changelog`, `mixed_changelog`, `google_doc_html_export`, `static_workshop_material`, or `nested_team_archive`.
- `compatible`: boolean indicating whether Kairn has a useful workflow for the source.
- `confidence`: numeric confidence from 0 to 1.
- `available_actions`: action identifiers exposed by CLI/GUI workflows.
- `suggested_next_action`: recommended first action.
- `warnings`: non-fatal issues.
- Optional summaries such as `archive_inspection` or folder hints.

## Parsed Workshop Data Products

Run-scoped workshop exports include:

- `artifact_catalog.csv`, `artifact_catalog.json`, `artifact_catalog_summary.json`, and `artifact_catalog_summary.txt`.
- `raw_tldraw_events.csv` and `raw_tldraw_events.jsonl`.
- `parsed_tldraw_events.csv` and `parsed_tldraw_events.jsonl`.
- `drive_activity_events.csv` and `drive_activity_events.jsonl`.
- `document_edit_events.csv` and `document_edit_events.jsonl`.
- `unified_process_events.csv` and `unified_process_events.jsonl`.
- `replay_events.csv` and `replay_events.json`.
- `replay_summary.json`.
- `workshop_intake_summary.json` and `workshop_intake_summary.txt`.

## Replay Event Schema

Replay events are loaded from `unified_process_events` when available and otherwise fall back to parsed source tables. Each replay event includes:

- Identity/provenance: replay id, source, source table, source event id, metadata/provenance JSON.
- Time/order: `timestamp_utc`, relative time seconds, sequence index.
- Actor context: team id, participant id, participant name, actor label.
- Action context: action, object type, artifact stream, artifact reference, content text, summary.
- Display fields: callout title and callout body.
- TLDraw geometry when available: `x`, `y`, `width`, `height`, plus room/entity/source/arrow/binding details in metadata.
