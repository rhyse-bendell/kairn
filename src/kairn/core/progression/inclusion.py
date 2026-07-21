from __future__ import annotations
from pathlib import Path
from .profile import stage_for_catalog_row
SUPPORTED={'.txt','.html','.htm','.docx','.sqlite','.db','.srt'}
def manifest_row(cat: dict, profile: dict, include_reflections=False) -> dict:
    st, reason=stage_for_catalog_row(cat, profile)
    status='included' if st else ('requires_review' if 'relevant role' in reason else 'excluded_nonanalytic_role')
    if st and st.get('include_by_default') is False and not include_reflections:
        status='excluded_reflection_by_default'
    ext=(cat.get('extension') or Path(cat.get('rel_path') or '').suffix).lower()
    if st and ext and ext not in SUPPORTED and cat.get('source_type') not in {'tldraw_sqlite','clean_transcript'}:
        status='excluded_unsupported_source'
    return {"artifact_id":cat.get('artifact_id'),"collection_id":cat.get('collection_id'),"rel_path":cat.get('rel_path'),"artifact_role":cat.get('artifact_role'),"stage":st.get('stage') if st else '',"stage_order":str(st.get('stage_order')) if st else '',"team_id":cat.get('team_hint') or '',"participant_id":cat.get('participant_hint') or '',"included":"true" if status=='included' else 'false',"inclusion_status":status,"inclusion_reason":reason,"content_available":"unknown","template_only":"false","source_type":cat.get('source_type'),"source_confidence":str(cat.get('source_confidence') or ''),"role_confidence":str(cat.get('role_confidence') or ''),"content_hash":"","review_status":"pending" if status=='requires_review' else ''}
