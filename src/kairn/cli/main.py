import argparse
from pathlib import Path
from kairn.core.ingestion.service import ingest_root
from kairn.core.export.compiled_json import export_compiled
from kairn.core.export.jsonl import export_jsonl
from kairn.core.export.csv import export_timeline_csv
from kairn.core.analysis.metrics import compute_metrics
from kairn.core.visualization.timeline_plotly import build_timeline_html
from kairn.core.maintenance.rebuild_participants import rebuild
from kairn.core.storage import repositories as repo

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
if __name__=='__main__': main()
