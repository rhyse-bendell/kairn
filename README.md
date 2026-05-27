# Kairn

Kairn is a standalone digital exhaust observatory for collaborative knowledge work.

## CLI quick usage
- `kairn ingest <root_path> --db kairn.db`
- `kairn collaborations create NAME --description "..."`
- `kairn collaborations list`
- `kairn categories list --collaboration-id <id>`
- `kairn categories add --collaboration-id <id> NAME`

## GUI
Install:
```bash
pip install -e ".[gui]"
```
Launch:
```bash
kairn-gui
```

Basic local testing workflow:
1. Create collaboration.
2. Select root folder.
3. Run ingestion.
4. Inspect Sources / Artifacts / Timeline.
5. Run Metrics / Exports / Visualization.


## Local GUI Workflow
1. `pip install -e ".[gui]"`
2. `kairn-gui`
3. Create or load a collaboration in Dashboard.
4. Select source folder and run ingestion from Sources.
5. Inspect Sources/Artifacts/Agents/Timeline tabs.
6. Run Metrics + Activity Indicators in Analysis.
7. Export compiled JSON, JSONL, compact and prompt chunks from Exports.
8. Run Diagnostics and maintenance actions.
