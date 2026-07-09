from .schemas import ObservatoryChartSpec

def build_chart_specs(tables):
    ids={t.table_id for t in tables}; specs=[]
    def add(cid,ctype,title,desc,tid,x,y,g=None):
        if tid in ids: specs.append(ObservatoryChartSpec(cid,title,desc,ctype,tid,x,y,g,caveat='Charts visualize observable trace counts only, not performance or quality.'))
    add('tldraw_actions_by_team','bar','TLDraw actions by team','Action counts by team/room.','tldraw_by_team_action','action','event_count','team_or_room')
    add('tldraw_actor_events','bar','TLDraw actor events','Actor event counts.','tldraw_actor_summary','actor_label','event_count','team_or_room')
    add('tldraw_event_density','line','TLDraw event density','Event counts by time bin.','tldraw_event_density','bin_start_utc','event_count','team_or_room')
    add('drive_action_counts','bar','Drive action counts','Drive activity actions.','drive_action_counts','action','event_count',None)
    add('document_actor_events','bar','Document actor events','Document changelog actor events.','document_changelog_actor_counts','actor_label','total_events',None)
    return specs
