from pathlib import Path
import json, csv, html
from dataclasses import asdict
from .schemas import table_to_dataframe, report_summary

VISUALIZATIONS = [
 ('trace_ecology_overview.html','Trace Ecology Overview',['folder_inventory_summary','stream_record_counts','source_processing_summary']),
 ('event_density_by_stream.html','Event Density by Stream',['drive_events_by_hour','tldraw_event_density','transcript_turns_by_time_bin']),
 ('actor_activity_by_stream.html','Actor Activity by Stream',['drive_user_action_counts','document_changelog_actor_counts','tldraw_actor_summary','transcript_speaker_summary']),
 ('artifact_history_overview.html','Artifact History Overview',['artifact_history_summary']),
 ('document_change_activity.html','Document Change Activity',['document_changelog_actor_counts','document_changelog_snippets']),
 ('tldraw_concept_map_activity.html','TLDraw Concept Map Activity',['tldraw_actor_summary','tldraw_by_team_action','tldraw_text_snippets']),
 ('transcript_activity.html','Transcript Activity',['transcript_speaker_summary','transcript_turns_by_time_bin','transcript_representative_snippets']),
 ('team_case_study.html','Team Case Study',['normalized_observatory_events','transcript_representative_snippets','document_changelog_snippets','tldraw_text_snippets']),
]

def _html_table(table, limit=25):
    if not table: return '<p>No matching table was generated.</p>'
    head=''.join(f'<th>{html.escape(str(c))}</th>' for c in table.columns)
    rows=''.join('<tr>'+''.join(f'<td>{html.escape(str(r.get(c,""))[:300])}</td>' for c in table.columns)+'</tr>' for r in table.rows[:limit])
    return f'<h2>{html.escape(table.table_id)}</h2><p>{html.escape(table.description)} See <code>tables/{html.escape(table.table_id)}.csv</code>.</p><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>'

def _num(v):
    try: return float(v or 0)
    except Exception: return 0.0

def _bar_chart(title, rows, label_col, value_col, limit=12):
    data=sorted(rows or [], key=lambda r: _num(r.get(value_col)), reverse=True)[:limit]
    if not data: return f'<section><h2>{html.escape(title)}</h2><p>No chartable rows.</p></section>'
    maxv=max([_num(r.get(value_col)) for r in data] or [1]) or 1
    items=[]
    for r in data:
        label=html.escape(str(r.get(label_col,'[blank]'))); val=_num(r.get(value_col)); pct=max(2, val/maxv*100)
        items.append(f'<div class="barrow"><span>{label}</span><div class="bar"><i style="width:{pct:.1f}%"></i></div><b>{val:g}</b></div>')
    return f'<section><h2>{html.escape(title)}</h2>{"".join(items)}</section>'

def _status_cards(table):
    if not table or not table.rows: return '<p>No stream status rows.</p>'
    cards=[]
    for r in table.rows:
        status=str(r.get('status') or ('available' if r.get('available')=='True' else 'not_detected'))
        cards.append(f'<div class="card"><h3>{html.escape(str(r.get("source_stream")))}</h3><p class="status">{html.escape(status)}</p><p>{html.escape(str(r.get("records",0)))} records from {html.escape(str(r.get("detected_sources",0)))} detected source(s).</p></div>')
    return '<div class="cards">'+''.join(cards)+'</div>'

def _timeline(title, table, time_col='timestamp_utc', label_col='source_stream', limit=80):
    rows=[r for r in (table.rows if table else []) if r.get(time_col) or r.get('start_seconds')]
    rows=rows[:limit]
    if not rows: return f'<section><h2>{html.escape(title)}</h2><p>No timeline rows.</p></section>'
    lis=[]
    for r in rows:
        ts=r.get(time_col) or f"+{r.get('start_seconds')}s"
        lis.append(f'<li><time>{html.escape(str(ts))}</time><strong>{html.escape(str(r.get(label_col,"")))}</strong> {html.escape(str(r.get("actor", r.get("actor_label", ""))))}: {html.escape(str(r.get("action", "")))} <span>{html.escape(str(r.get("text_snippet", ""))[:120])}</span></li>')
    return f'<section><h2>{html.escape(title)}</h2><ol class="timeline">{"".join(lis)}</ol></section>'

def _matrix(title, rows, x_col, y_col, value_col='event_count', limit=80):
    rows=(rows or [])[:limit]
    if not rows: return f'<section><h2>{html.escape(title)}</h2><p>No matrix rows.</p></section>'
    xs=sorted({str(r.get(x_col,'')) for r in rows}); ys=sorted({str(r.get(y_col,'')) for r in rows})
    vals={(str(r.get(x_col,'')),str(r.get(y_col,''))):_num(r.get(value_col, r.get('count'))) for r in rows}
    maxv=max(vals.values() or [1]) or 1
    head='<tr><th></th>'+''.join(f'<th>{html.escape(x)}</th>' for x in xs)+'</tr>'
    body=''
    for y in ys:
        body+='<tr><th>'+html.escape(y)+'</th>'
        for x in xs:
            v=vals.get((x,y),0); alpha=0.08+0.82*(v/maxv) if v else 0
            body+=f'<td style="background:rgba(37,99,235,{alpha:.2f})">{v:g}</td>'
        body+='</tr>'
    return f'<section><h2>{html.escape(title)}</h2><table class="matrix"><thead>{head}</thead><tbody>{body}</tbody></table></section>'

def _visual_sections(title, by):
    if title=='Trace Ecology Overview':
        return [_status_cards(by.get('stream_record_counts')), _bar_chart('Files by extension', (by.get('folder_inventory_summary') or {}).rows if by.get('folder_inventory_summary') else [], 'extension', 'file_count')]
    if title=='Event Density by Stream':
        parts=[]
        for tid,label in [('drive_events_by_hour','Drive events by hour'),('tldraw_event_density','TLDraw events by time bin'),('transcript_turns_by_time_bin','Transcript turns by time bin')]:
            t=by.get(tid); parts.append(_bar_chart(label, t.rows if t else [], t.columns[0] if t and t.columns else 'bin_start_utc', t.columns[-1] if t and t.columns else 'event_count'))
        return parts
    if title=='Actor Activity by Stream':
        return [_bar_chart('Drive actor activity', (by.get('drive_user_action_counts') or {}).rows if by.get('drive_user_action_counts') else [], 'actor_id_or_user','event_count'), _bar_chart('Document actor activity', (by.get('document_changelog_actor_counts') or {}).rows if by.get('document_changelog_actor_counts') else [], 'actor_label','total_events'), _bar_chart('TLDraw actor activity', (by.get('tldraw_actor_summary') or {}).rows if by.get('tldraw_actor_summary') else [], 'actor_label','event_count'), _bar_chart('Transcript speaker activity', (by.get('transcript_speaker_summary') or {}).rows if by.get('transcript_speaker_summary') else [], 'speaker','turn_count')]
    if title=='Artifact History Overview':
        return [_bar_chart('Most active artifacts', (by.get('artifact_history_summary') or {}).rows if by.get('artifact_history_summary') else [], 'artifact_name','event_count')]
    if title=='Team Case Study':
        return [_timeline('Cross-stream event timeline', by.get('normalized_observatory_events'))]
    if title=='TLDraw Concept Map Activity':
        t=by.get('tldraw_by_team_action'); return [_matrix('TLDraw team/action matrix', t.rows if t else [], 'action','team_or_room')]
    if title=='Transcript Activity':
        return [_bar_chart('Transcript speakers', (by.get('transcript_speaker_summary') or {}).rows if by.get('transcript_speaker_summary') else [], 'speaker','turn_count'), _timeline('Representative transcript snippets', by.get('transcript_representative_snippets'), 'start_seconds', 'speaker')]
    if title=='Document Change Activity':
        return [_bar_chart('Document changelog actors', (by.get('document_changelog_actor_counts') or {}).rows if by.get('document_changelog_actor_counts') else [], 'actor_label','total_events'), _matrix('Document activity/action matrix', (by.get('document_changelog_activity_action_counts') or {}).rows if by.get('document_changelog_activity_action_counts') else [], 'action','activity_keyword')]
    return []

def _write_visualizations(report, out):
    viz=Path(out)/'visualizations'; viz.mkdir(parents=True,exist_ok=True); paths={}; by={t.table_id:t for t in report.tables}
    css='body{font-family:system-ui,Segoe UI,sans-serif;max-width:1180px;margin:2rem auto;padding:0 1rem;line-height:1.4;color:#0f172a}table{border-collapse:collapse;width:100%;margin:1rem 0}th,td{border:1px solid #ddd;padding:.35rem;vertical-align:top}th{background:#f1f5f9}.caveat{background:#fff7ed;border:1px solid #fed7aa;padding:1rem}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:1rem}.card{border:1px solid #cbd5e1;border-radius:10px;padding:1rem;background:#f8fafc}.status{font-weight:700;color:#2563eb}.barrow{display:grid;grid-template-columns:220px 1fr 70px;gap:.75rem;align-items:center;margin:.35rem 0}.bar{height:18px;background:#e2e8f0;border-radius:999px;overflow:hidden}.bar i{display:block;height:100%;background:#2563eb}.timeline{border-left:3px solid #2563eb;padding-left:1rem}.timeline li{margin:.75rem 0}.timeline time{display:inline-block;min-width:160px;color:#475569}code{background:#f8fafc;padding:.1rem .25rem}'
    for filename,title,tids in VISUALIZATIONS:
        parts=[f'<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title><style>{css}</style></head><body>',f'<h1>{html.escape(title)}</h1>', '<p>This standalone visualization summarizes descriptive digital traces generated by Kairn. It uses local exported CSV/JSON tables only and requires no internet access.</p>', '<div class="caveat"><strong>Caveat:</strong> These are descriptive traces, not performance scores or direct measures of cognition. Missing traces do not mean missing work.</div>']
        parts.extend(_visual_sections(title, by))
        for tid in tids: parts.append(_html_table(by.get(tid), limit=15))
        parts.append('<p>Related CSV table names are shown above. Open them from the <code>tables/</code> folder for complete data.</p></body></html>')
        p=viz/filename; p.write_text('\n'.join(parts),encoding='utf-8'); paths[f'visualization:{filename[:-5]}']=str(p)
    return paths

def _write_inventory(report, out):
    rows=[{'table_id':t.table_id,'title':t.title,'source_stream':t.source_stream,'row_count':len(t.rows),'column_count':len(t.columns),'caveat':t.caveat or ''} for t in report.tables]
    p=Path(out)/'output_table_inventory.csv'
    with open(p,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=['table_id','title','source_stream','row_count','column_count','caveat']); w.writeheader(); w.writerows(rows)
    return str(p)

def _md(report):
    table_ids={t.table_id for t in report.tables}; stream_counts=next((t for t in report.tables if t.table_id=='stream_record_counts'),None); proc=next((t for t in report.tables if t.table_id=='source_processing_summary'),None)
    lines=["# Kairn Observatory Report",'',f"Project: {report.project_name or ''}",f"Created: {report.created_at}",'',"## Project/folder context",f"Root: `{report.project_root or ''}`",'',"## Source processing summary"]
    if proc:
        for r in proc.rows[:20]: lines.append(f"- {r.get('source_kind')} — {r.get('action_taken')} — records: {r.get('records_written')} — `{r.get('path')}`")
    else: lines.append('No source processing summary table was generated.')
    lines += ['',"## Trace ecology summary"]
    if stream_counts:
        for r in stream_counts.rows: lines.append(f"- {r.get('source_stream')}: available={r.get('available')}, records={r.get('records')}, primary table `{r.get('primary_table')}`")
    lines += ['',"## Eight digital exhaust types detected"]
    checks=[('Document text insertion/editing','document_changelog_overall_counts'),('Document text deletion/replacement','document_changelog_actor_counts'),('File lifecycle activity','drive_file_lifecycle_summary'),('File access/sharing/permission activity','drive_file_lifecycle_summary'),('Concept-map shape creation','tldraw_by_team_action'),('Concept-map object modification','tldraw_by_team_action'),('Concept-map text annotation/labeling','tldraw_text_snippets'),('Transcript speech act / meeting turn','transcript_overall_counts')]
    for label,tid in checks: lines.append(f"- {label}: {'detected' if tid in table_ids and next((t for t in report.tables if t.table_id==tid and t.rows),None) else 'not detected or unavailable'}")
    lines += ['',"## Key descriptives",'- Drive actions: see `tables/drive_action_counts.csv` and `tables/drive_file_lifecycle_summary.csv`.','- Document edits/deletions: see `tables/document_changelog_actor_counts.csv` and `tables/document_changelog_snippets.csv`.','- TLDraw actor/object/action summaries: see `tables/tldraw_actor_summary.csv`, `tables/tldraw_by_team_object_type.csv`, and `tables/tldraw_text_snippets.csv`.','- Transcript speaker/turn/word summaries: see `tables/transcript_speaker_summary.csv`, `tables/transcript_team_summary.csv`, and `tables/transcript_keyword_counts.csv`.','',"## Cross-stream normalized events",'`tables/normalized_observatory_events.csv` combines Drive, document, TLDraw, and transcript rows into actor-time-artifact-action records where fields are available.','',"## Visualizations",'- `visualizations/trace_ecology_overview.html`','- `visualizations/event_density_by_stream.html`','- `visualizations/actor_activity_by_stream.html`','- `visualizations/artifact_history_overview.html`','- `visualizations/document_change_activity.html`','- `visualizations/tldraw_concept_map_activity.html`','- `visualizations/transcript_activity.html`','- `visualizations/team_case_study.html`','',"## Representative snippets"]
    for s in report.snippets[:20]: lines.append(f"- {s}")
    lines += ['',"## Caveats and interpretation limits"] + [f"- {c}" for c in report.caveats]
    lines += ['- Transcript duration and timestamps may be relative to recording start rather than global project time.','- Actor/speaker names may require reconciliation across platforms.']
    return '\n'.join(lines)+'\n'

def export_observatory_report(report, out_dir, include_csv=True, include_json=True, include_markdown=True, include_chart_specs=True):
    out=Path(out_dir); (out/'tables').mkdir(parents=True,exist_ok=True); (out/'charts').mkdir(parents=True,exist_ok=True); (out/'visualizations').mkdir(parents=True,exist_ok=True); paths={}
    for t in report.tables:
        if include_csv: paths[f'table_csv:{t.table_id}']=str(out/'tables'/f'{t.table_id}.csv'); table_to_dataframe(t).to_csv(paths[f'table_csv:{t.table_id}'],index=False)
        if include_json: paths[f'table_json:{t.table_id}']=str(out/'tables'/f'{t.table_id}.json'); (out/'tables'/f'{t.table_id}.json').write_text(json.dumps(asdict(t),indent=2,default=str),encoding='utf-8')
    if include_chart_specs:
        for c in report.charts:
            p=out/'charts'/f'{c.chart_id}.json'; p.write_text(json.dumps(asdict(c),indent=2),encoding='utf-8'); paths[f'chart:{c.chart_id}']=str(p)
    paths.update(_write_visualizations(report,out))
    if include_markdown:
        p=out/'kairn_observatory_report.md'; p.write_text(_md(report),encoding='utf-8'); paths['markdown']=str(p)
    paths['inventory']=_write_inventory(report,out)
    stream_availability=[t.to_dict() for t in report.tables if t.table_id=='stream_record_counts']
    processing_summary=[t.to_dict() for t in report.tables if t.table_id=='source_processing_summary']
    p=out/'report_manifest.json'; p.write_text(json.dumps({'summary':report_summary(report),'files':paths,'warnings':report.warnings,'stream_availability':stream_availability,'processing_summary':processing_summary},indent=2),encoding='utf-8'); paths['manifest']=str(p); paths['out_dir']=str(out)
    return paths
