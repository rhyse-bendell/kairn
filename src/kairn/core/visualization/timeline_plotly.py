from __future__ import annotations
from pathlib import Path
from ..analysis.timelines import build_timeline


def build_timeline_html(db_path,out_html,collection_id=None):
    data=build_timeline(db_path,collection_id=collection_id)
    events=data['events']
    out=Path(out_html); out.parent.mkdir(parents=True,exist_ok=True)
    try:
        import plotly.express as px
        fig=px.scatter(events,x='ts',y='unit',color='actor_label',hover_data=['action','artifact_path','summary'],title='Kairn Timeline')
        fig.write_html(str(out))
    except Exception:
        out.write_text('<html><body><h1>Kairn Timeline</h1></body></html>',encoding='utf-8')
    unit_dir=out.parent/'units'; unit_dir.mkdir(exist_ok=True)
    paths=[]
    for unit in sorted({e.get('unit') for e in events if e.get('unit')})[:50]:
        up=unit_dir/f"{str(unit).replace('/','_')}.html"
        ue=[e for e in events if e.get('unit')==unit]
        try:
            import plotly.express as px
            fig=px.scatter(ue,x='ts',y='action',color='actor_label',title=f'Unit: {unit}')
            fig.write_html(str(up))
        except Exception:
            up.write_text(f'<html><body><h2>{unit}</h2></body></html>',encoding='utf-8')
        paths.append(str(up))
    return str(out),paths
