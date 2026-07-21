import argparse, json
from pathlib import Path
from kairn.core.ingestion.service import ingest_root
from kairn.core.export.compiled_json import export_compiled
from kairn.core.export.jsonl import export_jsonl
from kairn.core.export.csv import export_timeline_csv
from kairn.core.analysis.metrics import compute_metrics
from kairn.core.visualization.timeline_plotly import build_timeline_html
from kairn.core.maintenance.rebuild_participants import rebuild
from kairn.core.storage import repositories as repo
from kairn.core.profiles import list_builtin_profiles, load_profile
from kairn.core.catalog.artifact_catalog import export_artifact_catalog
from kairn.core.tldraw.sqlite_parser import inspect_tldraw_db, parse_tldraw_audit_logs
from kairn.core.drive.activity_parser import parse_drive_activity_csv
from kairn.core.documents.changelog_parser import parse_all_changelogs_under_root
from kairn.core.process.unified_events import build_unified_process_events
from kairn.core.process.snapshots import create_board_snapshots
from kairn.core.sources import detect_compatible_source
from kairn.core.replay import load_replay_events, get_replay_summary
from kairn.core.replay.export import export_replay_events_csv, export_replay_events_json, export_replay_summary_json
from kairn.core.projects import create_project, load_project, list_projects, register_project_source, create_project_run
from kairn.core.projects.service import open_project_path
from kairn.core.export.workshop import export_workshop_data
from kairn.core.observatory import build_observatory_report, export_observatory_report, report_summary
from kairn.core.progression import prepare_artifact_progression, generate_deterministic_progression_candidates, export_artifact_progression_package

def main():
    p=argparse.ArgumentParser('kairn'); sp=p.add_subparsers(dest='cmd')
    ing=sp.add_parser('ingest'); ing.add_argument('root_path'); ing.add_argument('--db',default='kairn.db'); ing.add_argument('--collaboration-id')
    col=sp.add_parser('collaborations'); csp=col.add_subparsers(dest='ctype'); ccreate=csp.add_parser('create'); ccreate.add_argument('name'); ccreate.add_argument('--description',default=''); ccreate.add_argument('--db',default='kairn.db'); clist=csp.add_parser('list'); clist.add_argument('--db',default='kairn.db')
    cat=sp.add_parser('categories'); casp=cat.add_subparsers(dest='catype'); cal=casp.add_parser('list'); cal.add_argument('--db',default='kairn.db'); cal.add_argument('--collaboration-id',required=True); caa=casp.add_parser('add'); caa.add_argument('--db',default='kairn.db'); caa.add_argument('--collaboration-id',required=True); caa.add_argument('name'); caa.add_argument('--description',default=''); caa.add_argument('--applies-to',default='artifact')
    exp=sp.add_parser('export'); exsp=exp.add_subparsers(dest='etype'); ch=exsp.add_parser('changes'); ch.add_argument('--root',required=True); ch.add_argument('--db',default='kairn.db')
    tc=exsp.add_parser('timeline-csv'); tc.add_argument('--root',required=True); tc.add_argument('--db',default='kairn.db')
    ew=exsp.add_parser('workshop'); ew.add_argument('--out-dir',required=True); ew.add_argument('--db',default='kairn.db')
    m=sp.add_parser('metrics'); m.add_argument('--root',required=True); m.add_argument('--db',default='kairn.db')
    v=sp.add_parser('visualize'); vsp=v.add_subparsers(dest='vtype'); t=vsp.add_parser('timeline'); t.add_argument('--root',required=True); t.add_argument('--db',default='kairn.db')
    part=sp.add_parser('participants'); psp=part.add_subparsers(dest='ptype'); rb=psp.add_parser('rebuild'); rb.add_argument('--db',default='kairn.db')
    prof=sp.add_parser('profiles'); prsp=prof.add_subparsers(dest='prtype'); prsp.add_parser('list'); ps=prsp.add_parser('show'); ps.add_argument('profile')
    catalog=sp.add_parser('catalog'); catsp=catalog.add_subparsers(dest='catalog_type'); cb=catsp.add_parser('build'); cb.add_argument('--db',default='kairn.db'); cb.add_argument('--collection-id'); cb.add_argument('--collaboration-id'); cb.add_argument('--profile',default='problem_framing_workshop'); cb.add_argument('--out-dir',required=True)
    td=sp.add_parser('tldraw'); tdsp=td.add_subparsers(dest='tldraw_type'); tdi=tdsp.add_parser('inspect'); tdi.add_argument('db_path'); tdp=tdsp.add_parser('parse'); tdp.add_argument('db_path'); tdp.add_argument('--db',default='kairn.db'); tdp.add_argument('--collection-id'); tdp.add_argument('--run-id')
    dr=sp.add_parser('drive'); drsp=dr.add_subparsers(dest='drive_type'); drp=drsp.add_parser('parse'); drp.add_argument('csv_path'); drp.add_argument('--db',default='kairn.db'); drp.add_argument('--collection-id'); drp.add_argument('--run-id')
    docs=sp.add_parser('documents'); dosp=docs.add_subparsers(dest='documents_type'); dop=dosp.add_parser('parse-changelogs'); dop.add_argument('root_path'); dop.add_argument('--db',default='kairn.db'); dop.add_argument('--collection-id'); dop.add_argument('--run-id')
    proj=sp.add_parser('projects', help='Create, list, load, and manage local Kairn projects'); pjsp=proj.add_subparsers(dest='projects_type'); pc=pjsp.add_parser('create'); pc.add_argument('name'); pc.add_argument('--description',default=''); pc.add_argument('--home'); pc.add_argument('--profile',default='problem_framing_workshop'); pl=pjsp.add_parser('list'); pl.add_argument('--home'); psw=pjsp.add_parser('show'); psw.add_argument('project'); po=pjsp.add_parser('open'); po.add_argument('project'); prs=pjsp.add_parser('register-source'); prs.add_argument('project'); prs.add_argument('source_path'); prs.add_argument('--copy',action='store_true'); prs.add_argument('--source-type'); pnr=pjsp.add_parser('new-run'); pnr.add_argument('project'); pnr.add_argument('--label');
    srcp=sp.add_parser('sources'); srcsp=srcp.add_subparsers(dest='sources_type'); si=srcsp.add_parser('inspect'); si.add_argument('path')
    rep=sp.add_parser('replay'); repsp=rep.add_subparsers(dest='replay_type'); rs=repsp.add_parser('summary'); rs.add_argument('--db',default='kairn.db'); rs.add_argument('--collection-id'); rs.add_argument('--run-id'); re=repsp.add_parser('export'); re.add_argument('--db',default='kairn.db'); re.add_argument('--collection-id'); re.add_argument('--run-id'); re.add_argument('--out-dir',required=True)
    obs=sp.add_parser('observatory'); obsp=obs.add_subparsers(dest='observatory_type'); obr=obsp.add_parser('report'); obr.add_argument('project'); obr.add_argument('--out'); obr.add_argument('--team'); obr.add_argument('--activity'); obr.add_argument('--bin-minutes',type=int,default=15); obr.add_argument('--no-csv',action='store_true'); obr.add_argument('--no-json',action='store_true'); obr.add_argument('--no-markdown',action='store_true')
    prog=sp.add_parser('progression'); prgsp=prog.add_subparsers(dest='progression_type'); prgp=prgsp.add_parser('prepare'); prgp.add_argument('project'); prgp.add_argument('--collection-id'); prgp.add_argument('--profile',default='problem_framing_workshop'); prgp.add_argument('--include-reflections',action='store_true'); prgp.add_argument('--out'); prge=prgsp.add_parser('export'); prge.add_argument('project'); prge.add_argument('--analysis-run-id',required=True); prge.add_argument('--out',required=True)
    proc=sp.add_parser('process'); prsp=proc.add_subparsers(dest='process_type'); pbu=prsp.add_parser('build-unified'); pbu.add_argument('--db',default='kairn.db'); pbu.add_argument('--collection-id'); pbu.add_argument('--run-id'); psn=prsp.add_parser('snapshots'); psn.add_argument('--db',default='kairn.db'); psn.add_argument('--collection-id'); psn.add_argument('--run-id')
    sp.add_parser('diagnose'); mt=sp.add_parser('maintenance'); msp=mt.add_subparsers(dest='mtype'); msp.add_parser('fix-changelog-timestamps')
    a=p.parse_args()
    if a.cmd=='ingest': ingest_root(a.root_path,a.db, collaboration_id=a.collaboration_id)
    elif a.cmd=='collaborations' and a.ctype=='create': print(repo.create_collaboration(a.db,a.name,a.description))
    elif a.cmd=='collaborations' and a.ctype=='list': [print(f"{c['id']}\t{c['name']}") for c in repo.list_collaborations(a.db)]
    elif a.cmd=='categories' and a.catype=='list': [print(f"{c['id']}\t{c['name']}\t{c['applies_to']}") for c in repo.list_categories(a.db,a.collaboration_id)]
    elif a.cmd=='categories' and a.catype=='add': print(repo.create_category(a.db,a.collaboration_id,a.name,a.description,a.applies_to))
    elif a.cmd=='export' and a.etype=='changes': export_compiled(a.db,str(Path(a.root)/'compiled.json')); export_jsonl(a.db,str(Path(a.root)/'events.jsonl'),str(Path(a.root)/'events.compact.jsonl.gz'))
    elif a.cmd=='export' and a.etype=='timeline-csv': export_timeline_csv(a.db,str(Path(a.root)/'timeline.csv'))
    elif a.cmd=='export' and a.etype=='workshop': print(json.dumps(export_workshop_data(a.db,a.out_dir), indent=2))
    elif a.cmd=='metrics': compute_metrics(a.db,str(Path(a.root)/'metrics.csv'))
    elif a.cmd=='visualize' and a.vtype=='timeline': build_timeline_html(a.db,str(Path(a.root)/'timeline.html'))
    elif a.cmd=='participants' and a.ptype=='rebuild': rebuild(a.db)
    elif a.cmd=='profiles' and a.prtype=='list': [print(f"{p['name']}\t{p.get('description','')}") for p in list_builtin_profiles()]
    elif a.cmd=='profiles' and a.prtype=='show': print(json.dumps(load_profile(a.profile), indent=2))
    elif a.cmd=='tldraw' and a.tldraw_type=='inspect': print(json.dumps(inspect_tldraw_db(a.db_path), indent=2))
    elif a.cmd=='tldraw' and a.tldraw_type=='parse': print(json.dumps(parse_tldraw_audit_logs(a.db_path,a.db,a.collection_id,a.run_id), indent=2))
    elif a.cmd=='drive' and a.drive_type=='parse': print(json.dumps(parse_drive_activity_csv(a.csv_path,a.db,a.collection_id,a.run_id), indent=2))
    elif a.cmd=='documents' and a.documents_type=='parse-changelogs': print(json.dumps(parse_all_changelogs_under_root(a.root_path,a.db,a.collection_id,a.run_id), indent=2))

    elif a.cmd=='projects' and a.projects_type=='create': print(json.dumps(create_project(a.name,a.description,kairn_home=a.home,profile=a.profile), indent=2))
    elif a.cmd=='projects' and a.projects_type=='list': [print(f"{p['name']}\t{p['project_root']}\t{p.get('updated_at','')}") for p in list_projects(a.home)]
    elif a.cmd=='projects' and a.projects_type=='show': print(json.dumps(load_project(a.project), indent=2))
    elif a.cmd=='projects' and a.projects_type=='open':
        pr=load_project(a.project); open_project_path(pr['project_root']); print(pr['project_root'])
    elif a.cmd=='projects' and a.projects_type=='register-source': print(json.dumps(register_project_source(load_project(a.project), a.source_path, source_type=a.source_type, copy_into_project=a.copy), indent=2))
    elif a.cmd=='projects' and a.projects_type=='new-run': print(json.dumps(create_project_run(load_project(a.project), label=a.label), indent=2))
    elif a.cmd=='sources' and a.sources_type=='inspect': print(json.dumps(detect_compatible_source(a.path), indent=2))
    elif a.cmd=='replay' and a.replay_type=='summary': print(json.dumps(get_replay_summary(load_replay_events(a.db,a.collection_id,a.run_id)), indent=2))
    elif a.cmd=='replay' and a.replay_type=='export':
        ev=load_replay_events(a.db,a.collection_id,a.run_id); summ=get_replay_summary(ev); out=Path(a.out_dir); print(json.dumps({'csv':export_replay_events_csv(ev,out/'csv'/'replay_events.csv'),'json':export_replay_events_json(ev,out/'json'/'replay_events.json'),'summary':export_replay_summary_json(summ,out/'reports'/'replay_summary.json')}, indent=2))
    elif a.cmd=='observatory' and a.observatory_type=='report':
        pr=load_project(a.project); out=a.out or str(Path(pr.get('project_root','.') )/'runs'/'observatory_report'); report=build_observatory_report(pr, pr.get('db_path') or str(Path(pr.get('project_root','.'))/'kairn.db'), run_id=pr.get('active_run_id'), team=a.team, activity=a.activity, bin_minutes=a.bin_minutes); paths=export_observatory_report(report,out,include_csv=not a.no_csv,include_json=not a.no_json,include_markdown=not a.no_markdown); print(json.dumps({'out_dir':paths.get('out_dir'),'summary':report_summary(report)}, indent=2))
    elif a.cmd=='progression' and a.progression_type=='prepare':
        pr=load_project(a.project); summary=prepare_artifact_progression(pr, collection_id=a.collection_id, profile=a.profile, include_reflections=a.include_reflections); cand=generate_deterministic_progression_candidates(pr['db_path'], summary['analysis_run_id']); summary['deterministic_candidate_count']=cand.get('candidate_count',0);
        if a.out: summary['export']=export_artifact_progression_package(pr['db_path'], summary['analysis_run_id'], a.out)
        print(json.dumps(summary, indent=2))
    elif a.cmd=='progression' and a.progression_type=='export':
        pr=load_project(a.project); print(json.dumps(export_artifact_progression_package(pr['db_path'], a.analysis_run_id, a.out), indent=2))
    elif a.cmd=='process' and a.process_type=='build-unified': print(json.dumps(build_unified_process_events(a.db,a.collection_id,a.run_id), indent=2))
    elif a.cmd=='process' and a.process_type=='snapshots': print(json.dumps(create_board_snapshots(a.db,a.collection_id,a.run_id), indent=2))
    elif a.cmd=='catalog' and a.catalog_type=='build':
        if not a.collection_id and not a.collaboration_id:
            raise SystemExit('catalog build requires --collection-id or --collaboration-id')
        paths=export_artifact_catalog(a.db,a.out_dir,collection_id=a.collection_id,collaboration_id=a.collaboration_id,profile_name_or_path=a.profile)
        [print(f"{k}: {v}") for k,v in paths.items() if k != 'summary']
if __name__=='__main__': main()
