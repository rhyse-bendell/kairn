from ..base import BaseIngestionAdapter
from ...models.runs import IngestionResult
from ...storage import repositories as repo
class FilesystemAdapter(BaseIngestionAdapter):
    name='filesystem'
    def can_handle(self,c): return 0.1
    def ingest(self,c,ctx):
        aid=repo.upsert_artifact(ctx.db_path, ctx.collection_id, c)
        return IngestionResult(artifacts=[aid])
