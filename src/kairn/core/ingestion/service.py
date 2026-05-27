from pathlib import Path
from .scanner import scan
from .registry import AdapterRegistry
from .adapters.filesystem_adapter import FilesystemAdapter
from .adapters.text_adapter import TextAdapter
from .adapters.changelog_adapter import ChangelogAdapter
from .adapters.docx_adapter import DocxAdapter
from .adapters.pdf_adapter import PdfAdapter
from .adapters.image_adapter import ImageAdapter
from .adapters.diagram_json_adapter import DiagramJsonAdapter
from .adapters.pptx_adapter import PptxAdapter
from .adapters.unknown_file_adapter import UnknownFileAdapter
from ..models.runs import IngestionContext
from ..storage import repositories as repo

def default_registry():
    r=AdapterRegistry()
    for a in [FilesystemAdapter(),TextAdapter(),ChangelogAdapter(),DocxAdapter(),PdfAdapter(),ImageAdapter(),DiagramJsonAdapter(),PptxAdapter(),UnknownFileAdapter()]: r.register(a)
    return r

def ingest_root(root_path:str, db_path:str='kairn.db', snapshot_dir:str='.kairn_snapshots', actor_hint:str|None=None):
    cid=repo.ensure_collection(db_path, root_path); rid=repo.start_run(db_path,cid,root_path)
    ctx=IngestionContext(collection_id=cid, root_path=root_path, root_label=Path(root_path).name, run_id=rid, actor_hint=actor_hint, db_path=db_path, snapshot_dir=snapshot_dir, event_sink=None)
    reg=default_registry()
    for c in scan(root_path):
        adapters=reg.resolve(c)
        for a in adapters:
            a.ingest(c,ctx)
    return {'collection_id':cid,'run_id':rid}
