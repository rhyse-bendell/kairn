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
