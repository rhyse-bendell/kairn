from datetime import datetime, timezone
from dateutil.parser import parse
from .schemas import table_from_rows
from .report import read_sql_table_or_empty, normalize_timestamp_column, infer_team_from_path_or_room, safe_group_count

def _pick(rows,*names):
    keys=set().union(*(r.keys() for r in rows)) if rows else set()
    low={k.lower():k for k in keys}
    for n in names:
        if n in keys: return n
        if n.lower() in low: return low[n.lower()]
    return None

def _load(db):
    for t in ['parsed_tldraw_events','raw_tldraw_events','tldraw_events']:
        rows=read_sql_table_or_empty(db,t)
        if rows: return rows,t
    return [],None

def _floor(ts, mins):
    try:
        d=parse(ts); d=d.replace(minute=(d.minute//mins)*mins, second=0, microsecond=0); return d.strftime('%Y-%m-%dT%H:%M:%SZ')
    except Exception: return ''

def compute_tldraw_metrics(db_path, team=None, bin_minutes=15):
    rows,src=_load(db_path); cols=['total_events','user_originated_events','remote_or_sync_events','unique_rooms','unique_actors','unique_objects','first_timestamp_utc','last_timestamp_utc']
    if not rows: return [table_from_rows('tldraw_overall_counts','TLDraw overall counts','No TLDraw table detected.','tldraw',[],columns=cols,caveat='No TLDraw event table found; metrics skipped without failing.')]
    rows=normalize_timestamp_column(rows,['timestamp_utc','timestamp','ts','created_at','time'])
    room=_pick(rows,'team_or_room','room','room_id','source_room','file_path'); actor=_pick(rows,'actor_label','actor','user','user_id','session_id'); action=_pick(rows,'action','event_type','op'); obj=_pick(rows,'object_id','shape_id','record_id'); typ=_pick(rows,'object_type','shape_type','record_type','type'); source=_pick(rows,'source','origin'); text=_pick(rows,'text','plain_text','text_snippet','content')
    norm=[]
    for r in rows:
        rr=dict(r); tr=str(r.get(room,'') if room else ''); rr['team_or_room']=infer_team_from_path_or_room(tr) or tr or 'unknown'; rr['actor_label']=str(r.get(actor,'unknown') if actor else 'unknown'); rr['action']=str(r.get(action,'') if action else ''); rr['object_type']=str(r.get(typ,'') if typ else ''); rr['object_id']=str(r.get(obj,'') if obj else ''); rr['text_snippet']=str(r.get(text,'') if text else ''); norm.append(rr)
    if team: norm=[r for r in norm if team.lower() in r['team_or_room'].lower() or team.lower().replace(' ','') in r['team_or_room'].lower().replace(' ','')]
    user=[r for r in norm if str(r.get(source,'')).lower()=='user'] if source else list(norm); caveat=None if source else 'Source column unavailable; actor/activity counts include all TLDraw events.'
    tabs=[table_from_rows('tldraw_overall_counts','TLDraw overall counts','Provenance-preserving TLDraw event totals.','tldraw',[{'total_events':len(norm),'user_originated_events':len(user),'remote_or_sync_events':len(norm)-len(user) if source else 0,'unique_rooms':len({r['team_or_room'] for r in norm}),'unique_actors':len({r['actor_label'] for r in user}),'unique_objects':len({r['object_id'] for r in norm if r['object_id']}),'first_timestamp_utc':min([r.get('timestamp_utc','') for r in norm] or ['']),'last_timestamp_utc':max([r.get('timestamp_utc','') for r in norm] or [''])}],columns=cols,caveat=caveat)]
    if source:
        for r in norm: r['source_norm']=str(r.get(source,''))
        tabs.append(table_from_rows('tldraw_by_team_source','TLDraw by team and source','','tldraw',safe_group_count(norm,['team_or_room','source_norm'],'event_count'),columns=['team_or_room','source_norm','event_count']))
    for tid,gcols,base in [('tldraw_by_team_action',['team_or_room','action'],norm),('tldraw_by_team_object_type',['team_or_room','object_type'],norm),('tldraw_by_actor_action',['actor_label','team_or_room','action'],user),('tldraw_by_actor_object_type',['actor_label','team_or_room','object_type'],user)]: tabs.append(table_from_rows(tid,tid.replace('_',' ').title(),'', 'tldraw',safe_group_count(base,gcols,'event_count'),columns=gcols+['event_count']))
    sums={}
    for r in user:
        k=(r['actor_label'],r['team_or_room']); s=sums.setdefault(k,{'actor_label':k[0],'team_or_room':k[1],'event_count':0,'create_count':0,'update_count':0,'delete_count':0,'objects':set(),'text_bearing_events':0,'first_timestamp_utc':r.get('timestamp_utc',''),'last_timestamp_utc':r.get('timestamp_utc','')}); s['event_count']+=1; a=r['action'].lower(); s['create_count']+=('create' in a or 'add' in a); s['update_count']+=('update' in a or 'edit' in a); s['delete_count']+=('delete' in a or 'remove' in a); s['text_bearing_events']+=bool(r['text_snippet']); s['objects'].add(r['object_id']); s['first_timestamp_utc']=min(s['first_timestamp_utc'],r.get('timestamp_utc','')); s['last_timestamp_utc']=max(s['last_timestamp_utc'],r.get('timestamp_utc',''))
    act=[]
    for s in sums.values(): s['unique_objects']=len({o for o in s.pop('objects') if o}); act.append(s)
    tabs.append(table_from_rows('tldraw_actor_summary','TLDraw actor summary','User-originated descriptive actor activity counts; not performance scores.','tldraw',act,columns=['actor_label','team_or_room','event_count','create_count','update_count','delete_count','unique_objects','text_bearing_events','first_timestamp_utc','last_timestamp_utc'],caveat=caveat))
    dens=[]
    for r in norm: rr=dict(r); rr['bin_start_utc']=_floor(r.get('timestamp_utc',''),bin_minutes); dens.append(rr)
    tabs.append(table_from_rows('tldraw_event_density','TLDraw event density','Events per time bin.','tldraw',safe_group_count(dens,['team_or_room','bin_start_utc'],'event_count'),columns=['team_or_room','bin_start_utc','event_count']))
    tabs.append(table_from_rows('tldraw_text_snippets','TLDraw representative text snippets','Representative text-bearing TLDraw events; snippets do not indicate quality.','tldraw',[{'team_or_room':r['team_or_room'],'actor_label':r['actor_label'],'timestamp_utc':r.get('timestamp_utc'),'object_type':r['object_type'],'action':r['action'],'text_snippet':r['text_snippet'][:240],'object_id':r['object_id']} for r in user if r['text_snippet']][:100],columns=['team_or_room','actor_label','timestamp_utc','object_type','action','text_snippet','object_id']))
    last={}
    for r in sorted(norm,key=lambda x:x.get('timestamp_utc','')):
        if r['object_id']: last[r['object_id']]=r
    tabs.append(table_from_rows('tldraw_final_object_inventory','TLDraw final object inventory','Last observed event per object.','tldraw',[{'team_or_room':r['team_or_room'],'object_id':r['object_id'],'object_type':r['object_type'],'last_action':r['action'],'actor_label_last':r['actor_label'],'last_timestamp_utc':r.get('timestamp_utc'),'text_snippet':r['text_snippet'][:240]} for r in last.values()],columns=['team_or_room','object_id','object_type','last_action','actor_label_last','last_timestamp_utc','text_snippet']))
    return tabs
