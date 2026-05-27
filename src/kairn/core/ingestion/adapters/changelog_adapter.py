import re
from datetime import datetime, timezone
from pathlib import Path
from ..base import BaseIngestionAdapter
from ...models.runs import IngestionResult
from ...storage import repositories as repo
ACT=re.compile(r'^\[(?P<action>\w+)\]\s+(?P<actor>.*?)\s*\(.*?\):\s*(?P<content>.*)$')
GD=re.compile(r'(?P<actor>[^,]+),\s*(?P<action>created|edited|moved|renamed|deleted)\s*(?P<unit>.*)', re.I)
class ChangelogAdapter(BaseIngestionAdapter):
    name='changelog'
    def can_handle(self,c): return 1.0 if c.guessed_kind=='changelog' else 0
    def ingest(self,c,ctx):
        aid=repo.upsert_artifact(ctx.db_path, ctx.collection_id, c); out=IngestionResult(artifacts=[aid])
        for line in Path(c.path).read_text(errors='ignore').splitlines():
            m=ACT.match(line.strip())
            if m:
                act=m.group('action').lower(); actor=m.group('actor').strip(); content=m.group('content')
                eid=repo.add_event(ctx.db_path, ctx.collection_id, act, datetime.now(timezone.utc).isoformat(), artifact_id=aid, actor=actor, summary=content[:120], raw_row=line)
                repo.add_delta(ctx.db_path, eid, 'activity_log', content); out.events.append(eid); continue
            g=GD.search(line)
            if g: out.events.append(repo.add_event(ctx.db_path, ctx.collection_id, g.group('action').lower(), datetime.now(timezone.utc).isoformat(), artifact_id=aid, actor=g.group('actor').strip(), mentioned_unit=g.group('unit').strip() or None, summary=line[:120], raw_row=line))
        return out
