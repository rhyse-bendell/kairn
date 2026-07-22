import json, os, sqlite3, subprocess, sys
from pathlib import Path

from kairn.core.ingestion.service import ingest_root
from kairn.core.projects import create_project, load_project
from kairn.core.profiles import load_profile
from kairn.core.progression import prepare_artifact_progression, generate_deterministic_progression_candidates, export_artifact_progression_package
from kairn.core.progression import repository as prepo
from kairn.core.progression.extraction import extract_file_units, extract_tldraw_units, extract_transcript_units


def _project_with_files(tmp_path):
    project=create_project('Progression Synthetic', kairn_home=tmp_path)
    root=Path(project['project_root'])/'data'/'original'
    (root/'Team 1'/'Participant 1').mkdir(parents=True)
    (root/'Team 1'/'Participant 1'/'individual synthesis.txt').write_text('Instructions: respond briefly\nshared access barrier\n', encoding='utf-8')
    (root/'Team 1'/'team synthesis.txt').parent.mkdir(parents=True, exist_ok=True)
    (root/'Team 1'/'team synthesis.txt').write_text('shared access barrier\nother low overlap text\n', encoding='utf-8')
    (root/'Team 1'/'problem framing statement.html').write_text('<h1>Final</h1><p>shared access barrier</p>', encoding='utf-8')
    (root/'Team 1'/'reflection motivation.txt').write_text('A reflection', encoding='utf-8')
    result=ingest_root(str(root), project['db_path'], collaboration_id=project['active_collaboration_id'])
    project=load_project(project['project_root']); project['active_collection_id']=result['collection_id']
    return project


def test_profile_stage_metadata_loads():
    profile=load_profile('problem_framing_workshop')
    stages={s['stage']:s for s in profile['progression_stages']}
    assert stages['individual_synthesis']['stage_order']==1
    assert stages['reflection_building_motivation']['include_by_default'] is False


def test_prepare_maps_stages_excludes_reflections_and_extracts_stable_ids(tmp_path):
    project=_project_with_files(tmp_path)
    s1=prepare_artifact_progression(project, collection_id=project['active_collection_id'])
    rows=prepo.fetch_rows(project['db_path'], prepo.MANIFEST_TABLE, s1['analysis_run_id'])
    assert any(r['stage']=='individual_synthesis' and r['included']=='true' for r in rows)
    assert any(r['artifact_role']=='reflection_motivation' and r['inclusion_status']=='excluded_reflection_by_default' for r in rows)
    units=prepo.fetch_rows(project['db_path'], prepo.EVIDENCE_TABLE, s1['analysis_run_id'])
    assert any(u['source_locator']=='line:2' and u['text']=='shared access barrier' for u in units)
    assert any(u['source_locator'].startswith('html:') for u in units)
    assert any(u['is_prompt']=='true' for u in units)
    ids1=sorted(u['evidence_unit_id'] for u in units)
    s2=prepare_artifact_progression(project, collection_id=project['active_collection_id'])
    units2=prepo.fetch_rows(project['db_path'], prepo.EVIDENCE_TABLE, s2['analysis_run_id'])
    ids2=sorted(u['evidence_unit_id'] for u in units2)
    assert ids1==ids2


def test_deterministic_candidates_and_export(tmp_path):
    project=_project_with_files(tmp_path)
    summary=prepare_artifact_progression(project, collection_id=project['active_collection_id'])
    cand=generate_deterministic_progression_candidates(project['db_path'], summary['analysis_run_id'])
    rows=prepo.fetch_rows(project['db_path'], prepo.CANDIDATE_TABLE, summary['analysis_run_id'])
    assert cand['candidate_count'] >= 1
    assert any(r['relation_type']=='exact_recurrence' for r in rows)
    generate_deterministic_progression_candidates(project['db_path'], summary['analysis_run_id'])
    assert len(prepo.fetch_rows(project['db_path'], prepo.CANDIDATE_TABLE, summary['analysis_run_id'])) == len(rows)
    out=tmp_path/'export'
    res=export_artifact_progression_package(project['db_path'], summary['analysis_run_id'], str(out))
    for name in ['artifact_inclusion_manifest.csv','artifact_inclusion_manifest.json','artifact_evidence_units.csv','artifact_evidence_units.jsonl','artifact_progression_candidates.csv','team_progression_matrix_long.csv','artifact_progression_summary.md','artifact_progression_manifest.json']:
        assert (out/name).exists()


def test_docx_unavailable_warning_when_import_blocked(tmp_path, monkeypatch):
    p=tmp_path/'x.docx'; p.write_bytes(b'not real')
    row={'artifact_id':'a','collection_id':'c','stage':'s','stage_order':'1','team_id':'Team 1','participant_id':''}
    import builtins
    orig=builtins.__import__
    def fake(name,*args,**kwargs):
        if name=='docx': raise ImportError('blocked')
        return orig(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',fake)
    units,warnings=extract_file_units(str(p),'run',row)
    assert units==[] and any('python-docx is unavailable' in w for w in warnings)


def test_cli_progression_prepare_smoke(tmp_path):
    project=_project_with_files(tmp_path)
    env=os.environ.copy(); env['PYTHONPATH']=str(Path.cwd()/'src')+os.pathsep+env.get('PYTHONPATH','')
    out=tmp_path/'cli_out'
    proc=subprocess.run([sys.executable,'-m','kairn.cli.main','progression','prepare',project['project_root'],'--collection-id',project['active_collection_id'],'--out',str(out)], text=True, capture_output=True, check=True, env=env)
    data=json.loads(proc.stdout)
    assert data['evidence_unit_count'] >= 1
    assert (out/'artifact_progression_manifest.json').exists()


def test_tldraw_and_transcript_extraction_scope_to_manifest_artifact(tmp_path):
    db = tmp_path / 'kairn.db'
    with sqlite3.connect(db) as c:
        c.execute('create table parsed_tldraw_events(event_key text, object_id text, origin text, text_snippet text)')
        c.execute('insert into parsed_tldraw_events values (?,?,?,?)', ('e1', 'o1', str(tmp_path / 'Team 1' / 'TLDraw Logs.db'), 'team one board'))
        c.execute('insert into parsed_tldraw_events values (?,?,?,?)', ('e2', 'o2', str(tmp_path / 'Team 2' / 'TLDraw Logs.db'), 'team two board'))
        c.execute('create table transcript_turn_events(source_path text, text text, turn_index text, start_seconds text, end_seconds text)')
        c.execute('insert into transcript_turn_events values (?,?,?,?,?)', (str(tmp_path / 'Team 1' / 'team_transcript.srt'), 'team one transcript', '1', '0', '1'))
        c.execute('insert into transcript_turn_events values (?,?,?,?,?)', (str(tmp_path / 'Team 2' / 'team_transcript.srt'), 'team two transcript', '1', '0', '1'))
    row1 = {'artifact_id': 'a1', 'collection_id': 'c', 'rel_path': 'Team 1/TLDraw Logs.db', 'stage': 's', 'stage_order': '1', 'team_id': 'Team 1', 'participant_id': ''}
    tldraw_units, warnings = extract_tldraw_units(str(db), 'run', row1, artifact_path=str(tmp_path / 'Team 1' / 'TLDraw Logs.db'))
    assert warnings == []
    assert [u['text'] for u in tldraw_units] == ['team one board']
    row2 = dict(row1, artifact_id='a2', rel_path='Team 2/team_transcript.srt', team_id='Team 2')
    transcript_units, warnings = extract_transcript_units(str(db), 'run', row2, artifact_path=str(tmp_path / 'Team 2' / 'team_transcript.srt'))
    assert warnings == []
    assert [u['text'] for u in transcript_units] == ['team two transcript']


def test_replace_rows_with_pk_deletes_stale_analysis_run_rows(tmp_path):
    db = tmp_path / 'kairn.db'
    prepo.ensure_progression_tables(str(db))
    base = {'analysis_run_id': 'run', 'team_id': 'Team 1', 'source_evidence_unit_id': 's', 'target_evidence_unit_id': 't', 'source_stage': 'a', 'target_stage': 'b', 'relation_type': 'exact_recurrence', 'method': 'm', 'similarity_score': '1', 'confidence': 'c', 'rationale': 'r', 'status': 'proposed', 'created_at': 'now', 'review_note': ''}
    prepo.replace_rows(str(db), prepo.CANDIDATE_TABLE, 'run', [dict(base, candidate_id='keep'), dict(base, candidate_id='stale')], pk='candidate_id')
    prepo.replace_rows(str(db), prepo.CANDIDATE_TABLE, 'run', [dict(base, candidate_id='keep')], pk='candidate_id')
    assert [r['candidate_id'] for r in prepo.fetch_rows(str(db), prepo.CANDIDATE_TABLE, 'run')] == ['keep']


def test_transcript_extraction_refuses_ambiguous_fallback(tmp_path):
    db = tmp_path / 'kairn.db'
    with sqlite3.connect(db) as c:
        c.execute('create table transcript_turn_events(source_path text, text text, turn_index text, start_seconds text, end_seconds text)')
        c.execute('insert into transcript_turn_events values (?,?,?,?,?)', (str(tmp_path/'a.srt'), 'a', '1', '0', '1'))
        c.execute('insert into transcript_turn_events values (?,?,?,?,?)', (str(tmp_path/'b.srt'), 'b', '1', '0', '1'))
    row={'artifact_id':'a','collection_id':'c','stage':'s','stage_order':'1','team_id':'Team 1','participant_id':''}
    units, warnings = extract_transcript_units(str(db), 'run', row, artifact_path=str(tmp_path/'missing.srt'))
    assert units == []
    assert any('multiple transcript sources' in w for w in warnings)


def test_tldraw_extraction_refuses_ambiguous_fallback(tmp_path):
    db = tmp_path / 'kairn.db'
    with sqlite3.connect(db) as c:
        c.execute('create table parsed_tldraw_events(event_key text, object_id text, origin text, text_snippet text)')
        c.execute('insert into parsed_tldraw_events values (?,?,?,?)', ('e1', 'o1', str(tmp_path/'a.db'), 'a'))
        c.execute('insert into parsed_tldraw_events values (?,?,?,?)', ('e2', 'o2', str(tmp_path/'b.db'), 'b'))
    row={'artifact_id':'a','collection_id':'c','stage':'s','stage_order':'1','team_id':'Team 1','participant_id':''}
    units, warnings = extract_tldraw_units(str(db), 'run', row, artifact_path=str(tmp_path/'missing.db'))
    assert units == []
    assert any('multiple TLDraw sources' in w for w in warnings)


def test_empty_progression_export_writes_headers(tmp_path):
    db = tmp_path / 'kairn.db'
    prepo.ensure_progression_tables(str(db))
    prepo.upsert_run(str(db), {'analysis_run_id':'run-empty','project_id':'p','collection_id':'c','profile':'problem_framing_workshop','created_at':'now','settings_json':'{}','status':'completed','warnings_json':'[]'})
    out=tmp_path/'empty_export'
    export_artifact_progression_package(str(db), 'run-empty', str(out))
    assert (out/'artifact_evidence_units.csv').read_text(encoding='utf-8').startswith('evidence_unit_id,analysis_run_id,artifact_id')
    assert (out/'artifact_progression_candidates.csv').read_text(encoding='utf-8').startswith('candidate_id,analysis_run_id,team_id')
    assert (out/'team_progression_matrix_long.csv').read_text(encoding='utf-8').startswith('analysis_run_id,team_id,stage')
