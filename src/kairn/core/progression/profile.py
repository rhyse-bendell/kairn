from __future__ import annotations

def progression_stages(profile: dict) -> list[dict]:
    return sorted(profile.get('progression_stages') or [], key=lambda s: int(s.get('stage_order') or 0))

def stage_for_catalog_row(row: dict, profile: dict) -> tuple[dict|None, str]:
    role=row.get('artifact_role') or ''
    team=row.get('team_hint') or ''
    participant=row.get('participant_hint') or ''
    for st in progression_stages(profile):
        if role not in st.get('artifact_roles', []):
            continue
        stage=st.get('stage')
        if role=='framing_elements_terms':
            if stage=='individual_framing_elements' and participant:
                return st, 'participant hint resolves framing elements stage'
            if stage=='team_framing_elements' and team and not participant:
                return st, 'team hint resolves framing elements stage'
            continue
        return st, 'artifact role maps to progression stage'
    if role in {'individual_synthesis','team_synthesis','framing_elements_terms','tldraw_board_log','problem_framing_statement','reflection_motivation'}:
        return None, 'relevant role could not be confidently mapped to stage'
    return None, 'non-analytic artifact role for progression'
