from .schemas import table_from_rows
from .tldraw_metrics import compute_tldraw_metrics
from .document_metrics import compute_document_metrics

def _slug(s): return ''.join(ch.lower() for ch in str(s or 'case') if ch.isalnum()) or 'case'

def compute_case_study(db_path, project, team=None, activity=None, streams=None, bin_minutes=15):
    tabs=[]; prefix=_slug(team or 'selected')
    for t in compute_tldraw_metrics(db_path, team=team, bin_minutes=bin_minutes):
        if t.table_id in ['tldraw_actor_summary','tldraw_by_team_action','tldraw_by_team_object_type','tldraw_event_density','tldraw_text_snippets']:
            rows=t.rows
            if team: rows=[r for r in rows if team.lower() in str(r.get('team_or_room','')).lower() or team.lower().replace(' ','') in str(r.get('team_or_room','')).lower().replace(' ','')]
            tabs.append(table_from_rows(f'{prefix}_{t.table_id}',f'{team or "Selected"} {t.title}',t.description,'case_study',rows,{'team':team,'activity':activity},t.columns,t.caveat))
    for t in compute_document_metrics(db_path, project):
        if t.table_id in ['problem_framing_changelog_by_team_actor','document_changelog_snippets']:
            rows=t.rows
            if team: rows=[r for r in rows if team.lower() in str(r.get('inferred_team','')).lower() or team.lower().replace(' ','') in str(r.get('document_name','')).lower().replace(' ','')]
            if activity: rows=[r for r in rows if activity.lower() in str(r).lower()]
            tabs.append(table_from_rows(f'{prefix}_{t.table_id}',f'{team or "Selected"} {t.title}',t.description,'case_study',rows,{'team':team,'activity':activity},t.columns,t.caveat))
    return tabs
