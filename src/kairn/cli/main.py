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

def main():
    p=argparse.ArgumentParser('kairn'); sp=p.add_subparsers(dest='cmd')
    ing=sp.add_parser('ingest'); ing.add_argument('root_path'); ing.add_argument('--db',default='kairn.db'); ing.add_argument('--collaboration-id')
    col=sp.add_parser('collaborations'); csp=col.add_subparsers(dest='ctype'); ccreate=csp.add_parser('create'); ccreate.add_argument('name'); ccreate.add_argument('--description',default=''); ccreate.add_argument('--db',default='kairn.db'); clist=csp.add_parser('list'); clist.add_argument('--db',default='kairn.db')
    cat=sp.add_parser('categories'); casp=cat.add_subparsers(dest='catype'); cal=casp.add_parser('list'); cal.add_argument('--db',default='kairn.db'); cal.add_argument('--collaboration-id',required=True); caa=casp.add_parser('add'); caa.add_argument('--db',default='kairn.db'); caa.add_argument('--collaboration-id',required=True); caa.add_argument('name'); caa.add_argument('--description',default=''); caa.add_argument('--applies-to',default='artifact')
    exp=sp.add_parser('export'); exsp=exp.add_subparsers(dest='etype'); ch=exsp.add_parser('changes'); ch.add_argument('--root',required=True); ch.add_argument('--db',default='kairn.db')
    tc=exsp.add_parser('timeline-csv'); tc.add_argument('--root',required=True); tc.add_argument('--db',default='kairn.db')
    m=sp.add_parser('metrics'); m.add_argument('--root',required=True); m.add_argument('--db',default='kairn.db')
    v=sp.add_parser('visualize'); vsp=v.add_subparsers(dest='vtype'); t=vsp.add_parser('timeline'); t.add_argument('--root',required=True); t.add_argument('--db',default='kairn.db')
    part=sp.add_parser('participants'); psp=part.add_subparsers(dest='ptype'); rb=psp.add_parser('rebuild'); rb.add_argument('--db',default='kairn.db')
    prof=sp.add_parser('profiles'); prsp=prof.add_subparsers(dest='prtype'); prsp.add_parser('list'); ps=prsp.add_parser('show'); ps.add_argument('profile')
    catalog=sp.add_parser('catalog'); catsp=catalog.add_subparsers(dest='catalog_type'); cb=catsp.add_parser('build'); cb.add_argument('--db',default='kairn.db'); cb.add_argument('--collection-id'); cb.add_argument('--collaboration-id'); cb.add_argument('--profile',default='problem_framing_workshop'); cb.add_argument('--out-dir',required=True)
    sp.add_parser('diagnose'); mt=sp.add_parser('maintenance'); msp=mt.add_subparsers(dest='mtype'); msp.add_parser('fix-changelog-timestamps')
    a=p.parse_args()
    if a.cmd=='ingest': ingest_root(a.root_path,a.db, collaboration_id=a.collaboration_id)
    elif a.cmd=='collaborations' and a.ctype=='create': print(repo.create_collaboration(a.db,a.name,a.description))
    elif a.cmd=='collaborations' and a.ctype=='list': [print(f"{c['id']}\t{c['name']}") for c in repo.list_collaborations(a.db)]
    elif a.cmd=='categories' and a.catype=='list': [print(f"{c['id']}\t{c['name']}\t{c['applies_to']}") for c in repo.list_categories(a.db,a.collaboration_id)]
    elif a.cmd=='categories' and a.catype=='add': print(repo.create_category(a.db,a.collaboration_id,a.name,a.description,a.applies_to))
    elif a.cmd=='export' and a.etype=='changes': export_compiled(a.db,str(Path(a.root)/'compiled.json')); export_jsonl(a.db,str(Path(a.root)/'events.jsonl'),str(Path(a.root)/'events.compact.jsonl.gz'))
    elif a.cmd=='export' and a.etype=='timeline-csv': export_timeline_csv(a.db,str(Path(a.root)/'timeline.csv'))
    elif a.cmd=='metrics': compute_metrics(a.db,str(Path(a.root)/'metrics.csv'))
    elif a.cmd=='visualize' and a.vtype=='timeline': build_timeline_html(a.db,str(Path(a.root)/'timeline.html'))
    elif a.cmd=='participants' and a.ptype=='rebuild': rebuild(a.db)
    elif a.cmd=='profiles' and a.prtype=='list': [print(f"{p['name']}\t{p.get('description','')}") for p in list_builtin_profiles()]
    elif a.cmd=='profiles' and a.prtype=='show': print(json.dumps(load_profile(a.profile), indent=2))
    elif a.cmd=='catalog' and a.catalog_type=='build':
        if not a.collection_id and not a.collaboration_id:
            raise SystemExit('catalog build requires --collection-id or --collaboration-id')
        paths=export_artifact_catalog(a.db,a.out_dir,collection_id=a.collection_id,collaboration_id=a.collaboration_id,profile_name_or_path=a.profile)
        [print(f"{k}: {v}") for k,v in paths.items() if k != 'summary']
if __name__=='__main__': main()
