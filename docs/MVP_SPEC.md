# MVP Spec
- Accepts folder-based input.
- Recursively registers all artifacts.
- Extracts/parses text, changelogs, PDFs, DOCX, images, diagram JSONs at basic levels.
- Produces timelines, exports, metrics, and visualizations.
- Preserves Ailys KS behavior for text/changelog inputs.

## GUI Workbench (MVP)
Current MVP includes a functional desktop workbench shell:
- Dashboard: collaboration create/load, root selection, ingestion, summary counts.
- Sources: artifact/warning inspection and ingestion trigger.
- Agents: participant rebuild and participant listing.
- Artifacts: artifact registry + per-artifact event inspection.
- Timeline: event table filters + visualization generation/open.
- Categories: category listing and add-category flow.
- Analysis: activity indicator metrics generation and table preview.
- Exports: compiled JSON/JSONL/timeline CSV and output folder access.
- Diagnostics: DB count summary, warning inspection, maintenance actions.


## MVP status (current)
- collaboration creation/loading
- modular ingestion
- artifact registry
- participant/agent registry
- timeline/session reconstruction
- exports/prompt chunks
- diagnostics/maintenance
- trace-based indicators
- desktop GUI workbenches

## Run scoped output layout
- json/compiled.json
- json/events.jsonl
- json/events.compact.jsonl.gz
- json/prompt_chunks/
- csv/timeline.csv + sessions.csv + metrics.csv
- viz/global_timeline.html (+ viz/units/*.html when generated)
- reports/diagnostics.json + diagnostics.txt + indicators.json

## Profile-driven artifact catalog

Kairn now includes a profile-driven artifact catalog layer for the first MVP slice. Profiles keep workshop-specific interpretation outside the generalized ingestion service and storage layer. The first built-in profile is `problem_framing_workshop`, which defines expected source types, artifact roles, phase labels, and simple regex-style role rules.

### CLI workflow

List built-in profiles:

```bash
kairn profiles list
```

Show a profile definition:

```bash
kairn profiles show problem_framing_workshop
```

Build and export an artifact catalog for an ingested collection:

```bash
kairn catalog build --db kairn.db --collection-id <collection-id> --profile problem_framing_workshop --out-dir <run-or-output-dir>
```

`--collaboration-id` can be used instead of `--collection-id` when cataloging all collections linked to a collaboration. The command requires one of those identifiers so it does not silently guess and produce misleading output.

### Outputs

The catalog export writes these files into the requested output directory, which may be an existing run-scoped reports/output directory created by Kairn:

* `artifact_catalog.csv`
* `artifact_catalog.json`
* `artifact_catalog_summary.json`
* `artifact_catalog_summary.txt`

Catalog rows include source type, artifact role, team and participant hints, confidence scores, reasons, event counts, and warnings. The summary reports counts by source type, role, team, and participant, plus expected source coverage from the selected profile and low-confidence mappings.

### Current scope and non-goals

This catalog slice detects source/role hints from artifact paths, names, broad kinds, and a lightweight optional SQLite `audit_logs` table check. It does **not** parse TLDraw audit rows, reconstruct boards, extract nodes/edges, compute whiteboard/process metrics, parse Drive CSV rows into workflow events, upgrade changelog timestamps, ingest transcript content, run LLM scoring, perform outcome scoring, or add dashboard indicator visualizations. Those capabilities remain follow-up work.

## Workshop Data Product Checklist

Implemented for the first real-data foundation layer:

- [x] `artifact_catalog` profile-driven source and role detection for workshop folders.
- [x] `raw_tldraw_events` preserving SQLite `audit_logs` rows.
- [x] `parsed_tldraw_events` with normalized TLDraw payload fields and provenance links.
- [x] `drive_activity_events` from `dailyLog.csv`.
- [x] `document_edit_events` from bracketed and Drive-style changelogs.
- [x] `unified_process_events` combining TLDraw, Drive, and document streams.
- [x] `board_snapshots` minimal board-state reconstruction counts.
- [ ] `outcome_scores` remains future work.

## Replay Workbench MVP

- [x] Generic replay backend normalizes `unified_process_events` and fallback parsed event tables into `ReplayEvent` records.
- [x] Desktop Replay tab supports loading events, source/team/participant filtering, timeline scrubbing, step/play/pause controls, event callouts, contribution summary tables, and density bins.
- [x] Source detection identifies TLDraw SQLite audit logs, Drive activity CSVs, document changelogs, ZIP archives, and folders containing known workshop sources.
- [x] Replay export writes normalized event CSV/JSON and summary JSON.
- [ ] Source-specific visual replay remains future work. In particular, full TLDraw canvas reconstruction is deferred; the MVP only shows TLDraw object metadata and textual approximations.
