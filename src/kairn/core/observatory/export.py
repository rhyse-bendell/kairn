from pathlib import Path
import json, csv
from dataclasses import asdict
from .schemas import table_to_dataframe, report_summary

def _write_inventory(report, out):
    rows=[{'table_id':t.table_id,'title':t.title,'source_stream':t.source_stream,'row_count':len(t.rows),'column_count':len(t.columns),'caveat':t.caveat or ''} for t in report.tables]
    p=Path(out)/'output_table_inventory.csv'
    with open(p,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=['table_id','title','source_stream','row_count','column_count','caveat']); w.writeheader(); w.writerows(rows)
    return str(p)

def _md(report):
    lines=[f"# Kairn Observatory Report",'',f"Project: {report.project_name or ''}",f"Created: {report.created_at}",'',"## Project context",f"Root: `{report.project_root or ''}`",'',"## Data-origin summary",'',"See `data_origin_*` tables and stream availability outputs.",'',"## TLDraw activity summary",'',"See `tldraw_*` tables for descriptive concept-map event indicators.",'',"## Drive activity summary",'',"See `drive_*` tables for file/workflow activity indicators.",'',"## Document changelog summary",'',"See `document_changelog_*` and `problem_framing_*` tables.",'',"## Case-study section",'',"Case-study tables are prefixed by the selected team/activity scope when available.",'',"## Representative snippets",'']
    for s in report.snippets[:20]: lines.append(f"- {s}")
    lines += ['',"## Transcript availability note",'',"Transcript metrics are optional; see `transcript_availability`.",'',"## Caveats and interpretation limits"]
    lines += [f"- {c}" for c in report.caveats]
    lines += ['',"## Suggested manuscript tables",'','- data_origin_extension_counts','- stream_availability_summary','- tldraw_actor_summary','- tldraw_event_density','- drive_file_lifecycle_summary','- document_changelog_actor_counts']
    return '\n'.join(lines)+'\n'

def export_observatory_report(report, out_dir, include_csv=True, include_json=True, include_markdown=True, include_chart_specs=True):
    out=Path(out_dir); (out/'tables').mkdir(parents=True,exist_ok=True); (out/'charts').mkdir(parents=True,exist_ok=True); paths={}
    for t in report.tables:
        if include_csv: paths[f'table_csv:{t.table_id}']=str(out/'tables'/f'{t.table_id}.csv'); table_to_dataframe(t).to_csv(paths[f'table_csv:{t.table_id}'],index=False)
        if include_json: paths[f'table_json:{t.table_id}']=str(out/'tables'/f'{t.table_id}.json'); (out/'tables'/f'{t.table_id}.json').write_text(json.dumps(asdict(t),indent=2,default=str),encoding='utf-8')
    if include_chart_specs:
        for c in report.charts:
            p=out/'charts'/f'{c.chart_id}.json'; p.write_text(json.dumps(asdict(c),indent=2),encoding='utf-8'); paths[f'chart:{c.chart_id}']=str(p)
    if include_markdown:
        p=out/'kairn_observatory_report.md'; p.write_text(_md(report),encoding='utf-8'); paths['markdown']=str(p)
    paths['inventory']=_write_inventory(report,out)
    p=out/'report_manifest.json'; p.write_text(json.dumps({'summary':report_summary(report),'files':paths},indent=2),encoding='utf-8'); paths['manifest']=str(p); paths['out_dir']=str(out)
    return paths
