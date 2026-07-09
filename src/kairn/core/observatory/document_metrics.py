from .schemas import table_from_rows
from .report import read_sql_table_or_empty, normalize_timestamp_column, infer_team_from_path_or_room, infer_activity_keyword, safe_group_count

def _pick(rows,*names):
    keys=set().union(*(r.keys() for r in rows)) if rows else set(); low={k.lower():k for k in keys}
    for n in names:
        if n in keys: return n
        if n.lower() in low: return low[n.lower()]
    return None

def compute_document_metrics(db_path, project=None):
    rows=read_sql_table_or_empty(db_path,'document_edit_events'); cols=['parsed_records','bracketed_edit_delete_records','drive_style_records','unique_documents','unique_actors','first_timestamp_utc','last_timestamp_utc']
    if not rows: return [table_from_rows('document_changelog_overall_counts','Document changelog overall counts','No document_edit_events table detected.','document_changelog',[],columns=cols,caveat='Document changelog stream unavailable; metrics skipped without failing.')]
    rows=normalize_timestamp_column(rows,['timestamp_utc','timestamp','time','created_at']); actor=_pick(rows,'actor_label','actor','user'); action=_pick(rows,'action','edit_type','event_type'); doc=_pick(rows,'document_name','document','file_name','path'); text=_pick(rows,'text_snippet','snippet','text','content')
    norm=[]
    for r in rows:
        d=str(r.get(doc,'') if doc else ''); rr=dict(r,actor_label=str(r.get(actor,'unknown') if actor else 'unknown'),action=str(r.get(action,'') if action else '').lower(),document_name=d,text_snippet=str(r.get(text,'') if text else ''),inferred_team=infer_team_from_path_or_room(d) or '',activity_keyword=infer_activity_keyword(d) or ''); norm.append(rr)
    tabs=[table_from_rows('document_changelog_overall_counts','Document changelog overall counts','Parsed document changelog totals.','document_changelog',[{'parsed_records':len(norm),'bracketed_edit_delete_records':sum('edit' in r['action'] or 'delete' in r['action'] for r in norm),'drive_style_records':sum(any(x in r['action'] for x in ['rename','move','permission','create']) for r in norm),'unique_documents':len({r['document_name'] for r in norm}),'unique_actors':len({r['actor_label'] for r in norm}),'first_timestamp_utc':min([r.get('timestamp_utc','') for r in norm] or ['']),'last_timestamp_utc':max([r.get('timestamp_utc','') for r in norm] or [''])}],columns=cols)]
    actors={}
    for r in norm:
        a=actors.setdefault(r['actor_label'],{'actor_label':r['actor_label'],'edit_count':0,'delete_count':0,'total_events':0,'snippet_word_count':0}); a['edit_count']+=any(x in r['action'] for x in ['edit','insert','add']); a['delete_count']+=any(x in r['action'] for x in ['delete','remove']); a['total_events']+=1; a['snippet_word_count']+=len(r['text_snippet'].split())
    tabs.append(table_from_rows('document_changelog_actor_counts','Document changelog actor counts','Descriptive edit/delete counts by actor; not quality or effort.','document_changelog',list(actors.values()),columns=['actor_label','edit_count','delete_count','total_events','snippet_word_count']))
    for tid,gcols in [('document_changelog_activity_action_counts',['activity_keyword','action']),('document_changelog_team_activity_action_counts',['inferred_team','activity_keyword','action'])]: tabs.append(table_from_rows(tid,tid.replace('_',' ').title(),'', 'document_changelog',safe_group_count(norm,gcols,'event_count'),columns=gcols+['event_count']))
    pf=[r for r in norm if any(x in r['document_name'].lower() for x in ['problem','framing','frame'])]; groups={}
    for r in pf:
        k=(r['inferred_team'],r['document_name'],r['actor_label']); g=groups.setdefault(k,{'inferred_team':k[0],'document_name':k[1],'actor_label':k[2],'edit_count':0,'delete_count':0,'total_events':0,'snippet_word_count':0}); g['edit_count']+=('edit' in r['action']); g['delete_count']+=('delete' in r['action']); g['total_events']+=1; g['snippet_word_count']+=len(r['text_snippet'].split())
    tabs.append(table_from_rows('problem_framing_changelog_by_team_actor','Problem-framing changelog by team and actor','Problem-framing document activity counts.','document_changelog',list(groups.values()),columns=['inferred_team','document_name','actor_label','edit_count','delete_count','total_events','snippet_word_count']))
    tabs.append(table_from_rows('document_changelog_snippets','Document changelog snippets','Representative document snippets; not quality indicators.','document_changelog',[{'inferred_team':r['inferred_team'],'activity_keyword':r['activity_keyword'],'document_name':r['document_name'],'actor_label':r['actor_label'],'timestamp_utc':r.get('timestamp_utc'),'action':r['action'],'text_snippet':r['text_snippet'][:240]} for r in norm if r['text_snippet']][:100],columns=['inferred_team','activity_keyword','document_name','actor_label','timestamp_utc','action','text_snippet']))
    return tabs
