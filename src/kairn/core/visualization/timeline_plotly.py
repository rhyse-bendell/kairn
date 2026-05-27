from ..storage.repositories import fetchall
def build_timeline_html(db_path,out_html):
    events=sorted(fetchall(db_path,'events'), key=lambda x:x['ts'])
    try:
        import plotly.express as px
        fig=px.scatter(x=[e['ts'] for e in events], y=[e['action'] for e in events], color=[e.get('actor') or 'unknown' for e in events], title='Kairn: Knowledge Space Timeline')
        fig.write_html(out_html)
    except Exception:
        open(out_html,'w').write('<html><body><h1>Kairn: Knowledge Space Timeline</h1></body></html>')
