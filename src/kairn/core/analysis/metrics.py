import csv
from collections import defaultdict
from ..storage.repositories import fetchall
def compute_metrics(db_path,out_csv):
    events=fetchall(db_path,'events'); deltas=fetchall(db_path,'deltas')
    words=defaultdict(int)
    for d in deltas:
        if d['delta_type'] in ('text_edit','activity_log'): words[d['event_id']]+=len((d['payload'] or '').split())
    rows=defaultdict(lambda:{'total_events':0,'words_added':0,'first_ts':None,'last_ts':None})
    for e in events:
        a=e['actor'] or 'unknown'; r=rows[a]; r['total_events']+=1; r['words_added']+=words.get(e['id'],0); r['first_ts']=min(filter(None,[r['first_ts'],e['ts']])) if r['first_ts'] else e['ts']; r['last_ts']=max(filter(None,[r['last_ts'],e['ts']])) if r['last_ts'] else e['ts']
    with open(out_csv,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['actor','total_events','words_added','first_ts','last_ts']); w.writeheader();
        for a,r in rows.items(): w.writerow({'actor':a,**r})
