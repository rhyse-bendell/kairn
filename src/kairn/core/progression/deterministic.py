from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from . import repository as repo

def _tokens(s): return {t for t in (s or '').split() if len(t)>2}
def _cid(run,a,b,method): return hashlib.sha1(f"{run}|{a}|{b}|{method}".encode()).hexdigest()
def generate_deterministic_progression_candidates(db_path: str, analysis_run_id: str) -> dict:
    units=[u for u in repo.fetch_rows(db_path, repo.EVIDENCE_TABLE, analysis_run_id) if u.get('is_prompt')!='true' and u.get('is_template_content')!='true']
    out=[]; now=datetime.now(timezone.utc).isoformat()
    for i,a in enumerate(units):
        for b in units[i+1:]:
            if (a.get('team_id') or '') != (b.get('team_id') or ''): continue
            if not a.get('team_id'): continue
            try:
                if int(a.get('stage_order') or 0) >= int(b.get('stage_order') or 0): continue
            except Exception: continue
            method=''; rel=''; score=0.0; rat=''
            if a.get('normalized_text') and a.get('normalized_text')==b.get('normalized_text'):
                method='exact_normalized_text'; rel='exact_recurrence'; score=1.0; rat='Exact normalized text recurs across ordered stages.'
            else:
                ta,tb=_tokens(a.get('normalized_text')), _tokens(b.get('normalized_text'))
                if min(len(ta),len(tb)) < 3: continue
                score=len(ta&tb)/len(ta|tb) if (ta|tb) else 0
                if score>=0.80: method='token_set_overlap'; rel='near_recurrence'; rat='High conservative token-set overlap across ordered stages.'
            if method:
                out.append({"candidate_id":_cid(analysis_run_id,a['evidence_unit_id'],b['evidence_unit_id'],method),"analysis_run_id":analysis_run_id,"team_id":a.get('team_id'),"source_evidence_unit_id":a['evidence_unit_id'],"target_evidence_unit_id":b['evidence_unit_id'],"source_stage":a.get('stage'),"target_stage":b.get('stage'),"relation_type":rel,"method":method,"similarity_score":f"{score:.3f}","confidence":"deterministic_conservative","rationale":rat,"status":"proposed","created_at":now,"review_note":""})
    repo.replace_rows(db_path, repo.CANDIDATE_TABLE, analysis_run_id, out, pk='candidate_id')
    return {"analysis_run_id":analysis_run_id,"candidate_count":len(out)}
