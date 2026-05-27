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
