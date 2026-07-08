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



## Windows GUI launcher

For easy local GUI testing on Windows:

- Double-click `launch_kairn_gui.bat`
- Or run from CMD/PowerShell:
  ```powershell
  .\launch_kairn_gui.bat
  ```

The launcher creates or reuses `.venv`, installs Kairn with GUI extras via `pip install -e ".[gui]"`, creates `kairn_workspace`, runs a lightweight import check, and launches `kairn-gui`.

## Local GUI Workflow
1. `pip install -e ".[gui]"`
2. `kairn-gui`
3. Create or load a collaboration in Dashboard.
4. Select source folder and run ingestion from Sources.
5. Inspect Sources/Artifacts/Agents/Timeline tabs.
6. Run Metrics + Activity Indicators in Analysis.
7. Export compiled JSON, JSONL, compact and prompt chunks from Exports.
8. Run Diagnostics and maintenance actions.

## Run-scoped outputs (MVP)

Kairn now writes exports under collaboration run folders:
`collaborations/<collaboration>/runs/<run_id>/{json,csv,viz,reports}` with prompt chunks under `json/prompt_chunks`.


## Profile-driven artifact catalog

Kairn supports a profile-driven artifact catalog for ingested collections. Profiles describe expected source types and artifact roles without hardcoding workshop assumptions into the core ingestion system. The first built-in profile is `problem_framing_workshop`.

```bash
kairn profiles list
kairn profiles show problem_framing_workshop
kairn catalog build --db kairn.db --collection-id <collection-id> --profile problem_framing_workshop --out-dir <output-or-run-dir>
```

The catalog command writes `artifact_catalog.csv`, `artifact_catalog.json`, `artifact_catalog_summary.json`, and `artifact_catalog_summary.txt` to the selected output directory. The desktop Sources tab can also build/refresh the catalog for the active collection and shows source type, artifact role, team/participant hints, confidence, and warnings.

This MVP slice is intentionally limited to cataloging and detection. It does not implement TLDraw audit-log parsing, board reconstruction, metrics, LLM scoring, outcome scoring, Drive event parsing, or transcript/MITM coding.

## Working with Workshop Data

Kairn includes a foundation ingestion layer for problem-framing workshop datasets. The workflow preserves provenance and parses source logs into normalized data products without AI/LLM analysis.

Typical commands:

```bash
kairn catalog build --db kairn.db --collection-id COLLECTION_ID --profile problem_framing_workshop --out-dir outputs/catalog
kairn tldraw inspect "TLDraw Logs.db"
kairn tldraw parse "TLDraw Logs.db" --db kairn.db --collection-id COLLECTION_ID
kairn drive parse dailyLog.csv --db kairn.db --collection-id COLLECTION_ID
kairn documents parse-changelogs "Teams [124PG]" --db kairn.db --collection-id COLLECTION_ID
kairn process build-unified --db kairn.db --collection-id COLLECTION_ID
kairn process snapshots --db kairn.db --collection-id COLLECTION_ID
kairn export workshop --db kairn.db --out-dir outputs/workshop
```

Implemented workshop data products include `raw_tldraw_events`, `parsed_tldraw_events`, `drive_activity_events`, `document_edit_events`, `unified_process_events`, and `board_snapshots`. The artifact catalog profile recognizes TLDraw SQLite logs, Drive daily logs, changelogs, Google document HTML exports, team/participant folder hints, task modules, and bracketed human-readable file IDs.

## Replay Workbench

Kairn includes a generic Replay Workbench for temporal inspection of workshop activity. Use **Select File or Folder** in the Replay tab, or `kairn sources inspect PATH`, to detect compatible inputs such as TLDraw SQLite audit logs, Drive `dailyLog.csv` files, document changelogs, ZIP archives, and workshop folders containing known source files.

After parsing known sources and building unified process events, open `kairn-gui`, choose the **Replay** tab, and click **Load Events**. The workbench loads `unified_process_events` when available and falls back to parsed TLDraw, Drive activity, document edit, or generic event tables. You can scrub the timeline slider, step backward/forward, play/pause with speed presets, filter by source/team/participant, and inspect per-event callouts with provenance metadata. Summary tables show contribution counts by actor, source, action, object type, and timeline density bins.

Replay events can also be exported with `kairn replay export --collection-id COLLECTION --out-dir OUT_DIR`, which writes CSV/JSON replay events and a JSON replay summary. Full TLDraw canvas reconstruction is intentionally deferred; current TLDraw replay displays categorical event details, text, coordinates, dimensions, source, and room/team metadata.

## Mining the Workshop Data

Kairn now prioritizes the concrete workshop dataset currently being mined rather than unknown future formats. The supported intake sources are:

- `Teams [124PG].zip` workshop archive, including the preserved `Teams [124PG]/` root folder and nested `Team 2 [1poyK].zip`.
- An extracted `Teams [124PG]/` folder with `dailyLog.csv`, `Team *` folders, `Participant *` folders, changelog `.txt` files, `email_export_*.html`, and DOCX/PPTX workshop materials.
- `TLDraw Logs.db` SQLite databases with an `audit_logs` table.
- Standalone `dailyLog.csv` Drive activity logs.
- Standalone Drive-style or bracketed document changelog `.txt` files.

Recommended workflow:

1. Launch the desktop app and open the **Sources/Intake** workflow.
2. Select `Teams [124PG].zip` and click **Inspect Selected Source**. Kairn reports source type, confidence, available actions, archive counts, important files, and nested zips without extracting anything.
3. Click **Extract ZIP + Prepare** to safely extract into the workspace. Extraction refuses zip-slip path traversal and preserves the archive root folder.
4. Select the extracted `Teams [124PG]/` folder or continue from the extracted root.
5. Build the artifact catalog and parse known sources: `dailyLog.csv`, changelog `.txt` files, and any `TLDraw Logs.db` files found under the folder.
6. Build unified process events and open the **Replay** tab.
7. Use source/team/participant filters, the scrubber, Play/Pause/Step controls, the event table, current-event callout, TLDraw details, and contribution summaries.
8. Click **Export Parsed Data Products** to write run-scoped CSV/JSON/JSONL summaries, replay exports, and workshop intake summaries.

CLI inspection is also available:

```bash
kairn sources inspect "Teams [124PG].zip"
kairn sources inspect "Teams [124PG]"
kairn sources inspect "TLDraw Logs.db"
kairn sources inspect "dailyLog.csv"
kairn sources inspect "Team 1_changelog.txt"
```
