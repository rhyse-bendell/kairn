from __future__ import annotations
import json, re
from datetime import datetime, timezone

def timestamp_ms_to_utc(ts):
    if ts in (None, ""): return None
    try: return datetime.fromtimestamp(float(ts)/1000, tz=timezone.utc).isoformat().replace('+00:00','Z')
    except Exception: return None

def _dig(d,*ks):
    cur=d
    for k in ks:
        if not isinstance(cur,dict): return None
        cur=cur.get(k)
    return cur

def extract_shape_text(payload_dict) -> str | None:
    p=payload_dict or {}; props=p.get('props') or p.get('shape',{}).get('props') or {}
    vals=[]
    def walk(x):
        if isinstance(x,dict):
            if isinstance(x.get('text'),str): vals.append(x['text'])
            for v in x.values(): walk(v)
        elif isinstance(x,list):
            for v in x: walk(v)
    if isinstance(props.get('text'),str): vals.append(props['text'])
    walk(props.get('richText'))
    s=''.join(vals).strip()
    return s or None

def extract_shape_geometry(payload_dict) -> dict:
    p=payload_dict or {}; props=p.get('props') or p.get('shape',{}).get('props') or {}
    return {
        'x': p.get('x'), 'y': p.get('y'),
        'width': props.get('w', props.get('width', p.get('width'))),
        'height': props.get('h', props.get('height', p.get('height'))),
        'rotation': p.get('rotation'), 'parent_id': p.get('parentId') or p.get('parent_id'),
        'group_id': p.get('groupId') or p.get('group_id'), 'color': props.get('color'), 'fill': props.get('fill'),
    }

def extract_arrow_or_binding(payload_dict) -> dict:
    p=payload_dict or {}; props=p.get('props') or {}
    out={'arrow_from_shape_id':None,'arrow_to_shape_id':None,'arrow_terminal':None,'binding_from_id':None,'binding_to_id':None}
    for terminal in ('start','end'):
        b=(props.get(terminal) or {})
        if isinstance(b,dict) and b.get('boundShapeId'):
            out['arrow_terminal']=terminal if not out['arrow_terminal'] else out['arrow_terminal']+','+terminal
            out['arrow_from_shape_id' if terminal=='start' else 'arrow_to_shape_id']=b.get('boundShapeId')
    out['binding_from_id']=p.get('fromId') or p.get('from_id') or _dig(p,'props','fromId')
    out['binding_to_id']=p.get('toId') or p.get('to_id') or _dig(p,'props','toId')
    bindings=p.get('bindings')
    if isinstance(bindings,dict):
        for b in bindings.values():
            if isinstance(b,dict):
                out['binding_from_id']=out['binding_from_id'] or b.get('fromId')
                out['binding_to_id']=out['binding_to_id'] or b.get('toId')
    return out

def room_to_team_id(room_id) -> str | None:
    if not room_id: return None
    s=str(room_id).lower()
    if 'facilitator' in s: return 'Facilitator'
    m=re.search(r'team[-_ ]?(\d+)|team(\d+)', s)
    if m: return f"Team {int(m.group(1) or m.group(2))}"
    return str(room_id)

def load_payload(raw):
    if isinstance(raw,dict): return raw
    try: return json.loads(raw or '{}')
    except Exception: return {}
