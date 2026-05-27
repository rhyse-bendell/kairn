from ..base import BaseIngestionAdapter
from ...models.runs import IngestionResult
from ...storage import repositories as repo
class UnknownFileAdapter(BaseIngestionAdapter):
    name='unknown'
    def can_handle(self,c): return 0.2 if c.guessed_kind=='unknown' else 0
    def ingest(self,c,ctx):
        aid=repo.upsert_artifact(ctx.db_path, ctx.collection_id, c)
        repo.add_warning(ctx.db_path, ctx.run_id, c.rel_path, 'No parser available')
        return IngestionResult(artifacts=[aid], warnings=['No parser available'])
