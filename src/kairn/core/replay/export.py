from __future__ import annotations
import csv,json
from pathlib import Path
from .models import ReplayEvent
def export_replay_events_csv(events,out_path):
 p=Path(out_path); p.parent.mkdir(parents=True,exist_ok=True); rows=[e.to_dict() for e in events]
 with p.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0].keys()) if rows else list(ReplayEvent('').to_dict().keys())); w.writeheader(); w.writerows(rows)
 return str(p)
def export_replay_events_json(events,out_path):
 p=Path(out_path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps([e.to_dict() for e in events],indent=2,default=str),encoding='utf-8'); return str(p)
def export_replay_summary_json(summary,out_path):
 p=Path(out_path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(summary,indent=2,default=str),encoding='utf-8'); return str(p)
