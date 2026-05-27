# Kairn

Kairn is a standalone digital exhaust observatory for collaborative knowledge work.

## CLI quick usage
- `kairn ingest <root_path> --db kairn.db`
- `kairn collaborations create NAME --description "..."`
- `kairn collaborations list`
- `kairn categories list --collaboration-id <id>`
- `kairn categories add --collaboration-id <id> NAME`

## GUI
```bash
pip install -e ".[gui]"
kairn-gui
```
Current GUI is an initial shell with dashboard-first workflows and incremental workbench expansion.
