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
1. Use Dashboard as the home/project launcher to start or load a project and open the workspace folder.
2. Import Folder or Import File(s) from the Project Hub.
3. Click Generate Metrics Package to process registered sources, compute observatory metrics, and export CSV/JSON/Markdown outputs. If the same source is imported more than once, Generate Metrics Package skips duplicate registered sources based on their original path so repeated imports do not double-count events.
4. Open Metrics Folder or View Metrics in Analysis.
5. Advanced/manual processing controls remain available under Advanced source controls when you need to inspect or process one source manually.



## Windows launcher scripts

Kairn separates first-time setup/update work from normal day-to-day launch behavior.

First-time setup, or setup after pulling Codex/GitHub changes:

```powershell
.\setup_kairn.bat
```

Normal launch:

```powershell
.\launch_kairn_gui.bat
```

The normal launcher uses the existing `.venv\Scripts\python.exe`, runs a lightweight import check, and starts the GUI with `python -m kairn.apps.desktop.main`. It does not install packages, upgrade pip, modify the virtual environment, create `kairn_workspace`, or call the generated `kairn-gui` console entry point. Keeping launch separate from setup makes startup faster, clearer, and less likely to trigger antivirus reputation checks.

To run tests through the setup script:

```powershell
.\setup_kairn.bat --test
```

Or run pytest directly from the virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Local GUI Workflow
1. `pip install -e ".[gui]"`
2. `kairn-gui`
3. Start or load a project from Dashboard, or open the workspace with Open Project Files.
4. Select source files/folders, inspect sources, extract archives, build catalogs, parse known sources, and run ingestion from Sources.
5. Inspect parsed-data tables and process operations in Process Data.
6. Play back event timelines in Replay.
7. Export compiled JSON, JSONL, compact and prompt chunks from Exports.
8. Run health checks, counts, warnings, and maintenance actions in Diagnostics.

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

## Projects

Kairn projects are durable local containers for a collaboration and its analysis outputs. In the desktop app, use **Dashboard → Start New Project** to create a project, **Load Project** to activate an existing one, and **Open Project Files** to open the active project folder in the OS file browser. After Dashboard creates or loads a project, the **Project** tab becomes the active project hub and the Project Explorer is rooted at that active project folder. If no project is loaded, the Project tab intentionally shows an empty state instead of browsing the full filesystem.

By default, Kairn creates projects in:

- Windows: `%USERPROFILE%\Documents\Kairn`
- macOS/Linux with `~/Documents`: `~/Documents/Kairn`
- Fallback: `~/.kairn`

Set `KAIRN_HOME` to override the project home for testing or custom storage locations. Each project has its own `kairn.db`, so intake, parsing, replay, analysis, exports, diagnostics, and source registries stay scoped to the active project.

A project folder contains:

```text
<ProjectRoot>/
  kairn_project.json
  kairn.db
  data/
    original/
    extracted/
    linked_sources/
    staging/
  catalog/
  parsed/
    tldraw/
    drive/
    documents/
    process/
  runs/
  exports/
    manual_exports/
  logs/
  settings/
    project_settings.json
    profile_settings.json
    source_registry.json
    participant_map.json
```

Sources can be linked in place or copied into `data/original/`. Linking preserves the original file location and records it in `settings/source_registry.json`; copying stores a project-local copy for portability. Archive extraction is project-scoped under `data/extracted/`, and run outputs are written under `runs/`.

Project CLI commands:

```bash
kairn projects create NAME --description "..." --home PATH --profile problem_framing_workshop
kairn projects list --home PATH
kairn projects show PROJECT_PATH_OR_NAME
kairn projects open PROJECT_PATH_OR_NAME
kairn projects register-source PROJECT_PATH SOURCE_PATH --copy --source-type TYPE
kairn projects new-run PROJECT_PATH --label LABEL
```

## Desktop GUI workflow structure

Kairn's desktop GUI is organized around five top-level workflow tabs:

- **Dashboard**: start a new project, load an existing project, open project files, and review the current project summary.
- **Project**: the project hub for the project explorer, import/link source actions, source registry summary, Sources / Intake, Files & History, Parsed Data, Agents, Categories / Metadata, and Diagnostics / Warnings.
- **Replay**: event playback, filters, contribution summaries, TLDraw event details, and the former Timeline / Sessions tools for timeline tables and visualizations.
- **Analysis**: metrics, indicators, participation/activity summaries, and trace-based interpretation notes.
- **Exports**: data products, reports, replay/diagnostics packages, run outputs, and generated file access.

The former top-level Sources, Agents, Artifacts, Categories, Process Data, and Diagnostics functionality remains available inside **Project**. The former Timeline functionality remains available inside **Replay**.


## Using Kairn

1. **Dashboard**: start or load a project.
2. **Project → Import Data Into Project**: copy folders/files into `data/original` or link external sources.
3. **Project → Sources / Intake**: inspect, extract, parse, and build the artifact catalog.
4. **Project → Files & History**: select cataloged files and view event history.
5. **Replay**: load events and scrub through the collaboration timeline.
6. **Analysis**: compute descriptive indicators.
7. **Exports**: write data products and reports.

Import means Kairn copies data into the project. Link means Kairn tracks an external path without copying it.

## Importing data into a project

1. Use **Dashboard** to start a new project or load an existing Kairn project.
2. Open **Project → Import Data Into Project** to choose whether to import a folder, import files, or link an external source.
3. Imported folders and files are copied into the active project under:

   ```text
   <ProjectRoot>/data/original/
   ```

4. Linked sources are registered in the project source registry but remain outside the project at their original paths.
5. After importing or linking data, use **Sources / Intake** to inspect sources, extract archives, build catalogs, or parse supported files.

## Observatory Metrics Workflow

Kairn can compute and export an Observatory Metrics package from a processed project. The workflow is:

1. Import data into a project.
2. Process imported sources.
3. Open **Analysis**.
4. Compute **Observatory Metrics**.
5. Review Data Origins, TLDraw, Drive, Documents, Case Study, Transcript Availability, and Caveats.
6. Export the Observatory Metrics Package.

CLI usage:

```bash
kairn observatory report PROJECT_PATH_OR_MANIFEST --team "Team 2" --activity "problem framing"
```

The package includes `kairn_observatory_report.md`, `output_table_inventory.csv`, `tables/*.csv`, `tables/*.json`, `charts/*.json`, and `report_manifest.json`.

Observatory metrics are descriptive trace indicators only. Activity counts are not performance, quality, effort, creativity, or cognition scores. Transcript metrics require transcript/audio-derived inputs and are reported unavailable otherwise. Source streams can be absent; Kairn reports availability and caveats instead of failing.
