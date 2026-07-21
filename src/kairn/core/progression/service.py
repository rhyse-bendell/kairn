from __future__ import annotations
import json, uuid
from datetime import datetime, timezone
from pathlib import Path
from kairn.core.catalog.artifact_catalog import build_artifact_catalog
from kairn.core.profiles import load_profile
from kairn.core.projects.service import create_project_run, get_project_subpaths
from . import repository as repo
from .inclusion import manifest_row
from .extraction import extract_file_units, extract_tldraw_units, extract_transcript_units
from .template_detection import mark_prompt_flags

def _now(): return datetime.now(timezone.utc).isoformat()
def _artifact_path(project, rel):
    root=Path(project.get('project_root',''))
    for base in [root, root/'data'/'original', root/'data'/'linked_sources']:
        p=base/(rel or '')
        if p.exists(): return p
    return root/(rel or '')

def prepare_artifact_progression(project: dict, collection_id: str | None = None, profile: str = "problem_framing_workshop", include_reflections: bool = False) -> dict:
    db_path=project.get('db_path') or str(Path(project.get('project_root','.'))/'kairn.db')
    repo.ensure_progression_tables(db_path)
    prof=load_profile(profile or project.get('active_profile'))
    cid=collection_id or project.get('active_collection_id')
    run=create_project_run(project, label='artifact_progression')
    analysis_run_id=run['run_id']
    warnings=["Participant consent is not inferred by artifact progression analysis; review requirements remain external."]
    catalog=build_artifact_catalog(db_path, collection_id=cid, collaboration_id=None if cid else project.get('active_collaboration_id'), profile_name_or_path=profile)
    manifest=[]; units=[]
    for c in catalog:
        m=manifest_row(c, prof, include_reflections); m['analysis_run_id']=analysis_run_id
        if m['included']=='true':
            rel=m.get('rel_path') or ''; st=m.get('stage')
            if c.get('artifact_role')=='tldraw_board_log': extracted=extract_tldraw_units(db_path, analysis_run_id, m); ew=[]
            elif c.get('artifact_role')=='transcript': extracted=extract_transcript_units(db_path, analysis_run_id, m); ew=[]
            else: extracted, ew=extract_file_units(str(_artifact_path(project, rel)), analysis_run_id, m)
            warnings.extend([f"{rel}: {w}" for w in ew])
            if extracted:
                m['content_available']='true'; units.extend(extracted)
            else:
                m['content_available']='false'; m['included']='false'
                if any('unsupported' in w for w in ew): m['inclusion_status']='excluded_unsupported_source'
                else: m['inclusion_status']='excluded_blank'; m['inclusion_reason']='no substantive evidence units extracted'
        manifest.append(m)
    units=mark_prompt_flags(units)
    by_art={}
    for u in units: by_art.setdefault(u['artifact_id'], []).append(u)
    for m in manifest:
        us=by_art.get(m['artifact_id'],[])
        if us and all(u.get('is_prompt')=='true' or u.get('is_template_content')=='true' for u in us):
            m['template_only']='true'; m['included']='false'; m['inclusion_status']='excluded_template_only'
        if us:
            m['content_hash']=';'.join(sorted({u.get('content_hash') for u in us if u.get('content_hash')}))[:1024]
    repo.upsert_run(db_path,{"analysis_run_id":analysis_run_id,"project_id":project.get('project_id'),"collection_id":cid or '',"profile":prof.get('name'),"created_at":_now(),"settings_json":json.dumps({"include_reflections":include_reflections}),"status":"completed","warnings_json":json.dumps(warnings)})
    repo.replace_rows(db_path, repo.MANIFEST_TABLE, analysis_run_id, manifest)
    repo.replace_rows(db_path, repo.EVIDENCE_TABLE, analysis_run_id, units, pk='evidence_unit_id')
    summary={"analysis_run_id":analysis_run_id,"artifact_count":len(manifest),"included_artifacts":sum(1 for m in manifest if m['included']=='true'),"excluded_artifacts":sum(1 for m in manifest if m['inclusion_status'].startswith('excluded')),"requires_review_artifacts":sum(1 for m in manifest if m['inclusion_status']=='requires_review'),"evidence_unit_count":len(units),"warnings":warnings,"run_dir":run.get('run_dir')}
    return summary
