from pathlib import Path
import difflib
from datetime import datetime, timezone
from ..base import BaseIngestionAdapter
from ...models.runs import IngestionResult
from ...storage import repositories as repo
class TextAdapter(BaseIngestionAdapter):
    name='text'
    kinds={'text','markdown','csv','json','transcript'}
    def can_handle(self,c): return 0.95 if c.guessed_kind in self.kinds else 0
    def ingest(self,c,ctx):
        p=Path(c.path); text=p.read_text(errors='ignore'); h=repo.hash_bytes(text.encode())
        aid=repo.upsert_artifact(ctx.db_path, ctx.collection_id, c, h); prev=repo.last_version_hash(ctx.db_path, aid)
        snap=Path(ctx.snapshot_dir)/ctx.collection_id; snap.mkdir(parents=True, exist_ok=True); snap_path=snap/f"{aid}.txt"
        out=IngestionResult(artifacts=[aid])
        if prev is None:
            repo.add_version(ctx.db_path, aid, h, str(snap_path)); snap_path.write_text(text)
            out.events.append(repo.add_event(ctx.db_path, ctx.collection_id, 'created', datetime.now(timezone.utc).isoformat(), artifact_id=aid, actor=ctx.actor_hint))
        elif prev!=h:
            old=snap_path.read_text(errors='ignore') if snap_path.exists() else ''
            diff='\n'.join(difflib.unified_diff(old.splitlines(), text.splitlines(), lineterm=''))
            repo.add_version(ctx.db_path, aid, h, str(snap_path)); snap_path.write_text(text)
            eid=repo.add_event(ctx.db_path, ctx.collection_id, 'edited', datetime.now(timezone.utc).isoformat(), artifact_id=aid, actor=ctx.actor_hint)
            repo.add_delta(ctx.db_path, eid, 'text_edit', diff); out.events.append(eid)
        return out
