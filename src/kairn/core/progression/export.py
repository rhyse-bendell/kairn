from __future__ import annotations
import csv,json
from pathlib import Path
from collections import Counter,defaultdict
from . import repository as repo

INCLUSION_COLUMNS=['analysis_run_id','artifact_id','collection_id','rel_path','artifact_role','stage','stage_order','team_id','participant_id','included','inclusion_status','inclusion_reason','content_available','template_only','source_type','source_confidence','role_confidence','content_hash','review_status']
EVIDENCE_COLUMNS=['evidence_unit_id','analysis_run_id','artifact_id','collection_id','stage','stage_order','team_id','participant_id','unit_index','unit_type','text','normalized_text','source_locator','section_heading','is_prompt','is_response','is_template_content','content_hash']
CANDIDATE_COLUMNS=['candidate_id','analysis_run_id','team_id','source_evidence_unit_id','target_evidence_unit_id','source_stage','target_stage','relation_type','method','similarity_score','confidence','rationale','status','created_at','review_note']
MATRIX_LONG_COLUMNS=['analysis_run_id','team_id','stage','stage_order','artifact_id','rel_path','evidence_unit_id','unit_type','text','source_locator','is_prompt','is_template_content','candidate_count']

def _write_csv(path, rows, columns=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields=columns or (list(rows[0].keys()) if rows else [])
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
def export_artifact_progression_package(db_path: str, analysis_run_id: str, out_dir: str) -> dict:
    out=Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    run=repo.fetch_run(db_path, analysis_run_id) or {}
    inc=repo.fetch_rows(db_path, repo.MANIFEST_TABLE, analysis_run_id); ev=repo.fetch_rows(db_path, repo.EVIDENCE_TABLE, analysis_run_id); cand=repo.fetch_rows(db_path, repo.CANDIDATE_TABLE, analysis_run_id)
    paths={}
    paths['inclusion_csv']=str(out/'artifact_inclusion_manifest.csv'); _write_csv(Path(paths['inclusion_csv']), inc, INCLUSION_COLUMNS)
    paths['inclusion_json']=str(out/'artifact_inclusion_manifest.json'); Path(paths['inclusion_json']).write_text(json.dumps(inc,indent=2),encoding='utf-8')
    paths['evidence_csv']=str(out/'artifact_evidence_units.csv'); _write_csv(Path(paths['evidence_csv']), ev, EVIDENCE_COLUMNS)
    paths['evidence_jsonl']=str(out/'artifact_evidence_units.jsonl'); Path(paths['evidence_jsonl']).write_text('\n'.join(json.dumps(r) for r in ev)+('\n' if ev else ''),encoding='utf-8')
    paths['candidates_csv']=str(out/'artifact_progression_candidates.csv'); _write_csv(Path(paths['candidates_csv']), cand, CANDIDATE_COLUMNS)
    cc=Counter(c['target_evidence_unit_id'] for c in cand)+Counter(c['source_evidence_unit_id'] for c in cand)
    matrix=[{"analysis_run_id":analysis_run_id,"team_id":e.get('team_id'),"stage":e.get('stage'),"stage_order":e.get('stage_order'),"artifact_id":e.get('artifact_id'),"rel_path":next((i.get('rel_path') for i in inc if i.get('artifact_id')==e.get('artifact_id')),''),"evidence_unit_id":e.get('evidence_unit_id'),"unit_type":e.get('unit_type'),"text":e.get('text'),"source_locator":e.get('source_locator'),"is_prompt":e.get('is_prompt'),"is_template_content":e.get('is_template_content'),"candidate_count":str(cc.get(e.get('evidence_unit_id'),0))} for e in ev]
    paths['matrix_long_csv']=str(out/'team_progression_matrix_long.csv'); _write_csv(Path(paths['matrix_long_csv']), matrix, MATRIX_LONG_COLUMNS)
    counts=Counter(i.get('inclusion_status') for i in inc); teams=sorted({i.get('team_id') for i in inc if i.get('team_id')}); stages=sorted({i.get('stage') for i in inc if i.get('stage')})
    missing={t:[s for s in stages if not any(i.get('team_id')==t and i.get('stage')==s and i.get('included')=='true' for i in inc)] for t in teams}
    unsupported=Counter(i.get('source_type') for i in inc if i.get('inclusion_status')=='excluded_unsupported_source')
    summary=f"""# Artifact Progression Analysis Summary\n\nProfile: {run.get('profile','')}\n\nAnalysis run: {analysis_run_id}\n\nArtifacts: {len(inc)}\n\nIncluded: {counts.get('included',0)}\nExcluded: {sum(v for k,v in counts.items() if k and k.startswith('excluded'))}\nRequires review: {counts.get('requires_review',0)}\nEvidence units: {len(ev)}\nDeterministic candidates: {len(cand)}\n\nMissing stages by team where detectable:\n```json\n{json.dumps(missing, indent=2)}\n```\n\nUnsupported source counts:\n```json\n{json.dumps(dict(unsupported), indent=2)}\n```\n\nPrompt/template caveat: deterministic markers are conservative aids; prompt and template text is preserved and flagged rather than deleted.\n\nNo semantic or LLM interpretation was used. Outputs are descriptive evidence aids, not final qualitative findings or performance measures.\n"""
    paths['summary_md']=str(out/'artifact_progression_summary.md'); Path(paths['summary_md']).write_text(summary,encoding='utf-8')
    manifest={"analysis_run_id":analysis_run_id,"profile":run.get('profile'),"files":paths,"counts":{"artifacts":len(inc),"evidence_units":len(ev),"candidates":len(cand)}}
    paths['manifest_json']=str(out/'artifact_progression_manifest.json'); Path(paths['manifest_json']).write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return {"out_dir":str(out),"files":paths,"summary":manifest}
