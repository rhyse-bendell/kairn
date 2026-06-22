from pathlib import Path
import json
TEXT_EXT={'.txt','.md','.csv','.json','.yaml','.yml','.xml','.log','.tsv','.rst'}
IMAGE_EXT={'.png','.jpg','.jpeg','.gif','.bmp','.webp'}
def classify(path:Path)->str:
    ext=path.suffix.lower()
    n=path.name.lower()
    if ext=='.docx': return 'docx'
    if ext=='.pdf': return 'pdf'
    if ext=='.pptx': return 'pptx'
    if ext=='.zip': return 'archive'
    if ext in {'.db','.sqlite','.sqlite3'}: return 'sqlite'
    if ext in {'.html','.htm'}: return 'html'
    if ext in {'.jsonl','.vtt','.srt'}: return 'text'
    if ext in IMAGE_EXT: return 'image'
    if 'changelog' in n or 'activity' in n: return 'changelog'
    if ext=='.json':
        try:
            obj=json.loads(path.read_text(errors='ignore')[:200000])
            if isinstance(obj,dict) and any(k in obj for k in ('nodes','edges','links','shapes','connectors','elements','diagram','graph')):
                return 'diagram_json'
        except Exception: pass
        return 'json'
    if ext=='.md': return 'markdown'
    if ext=='.csv': return 'csv'
    if ext in TEXT_EXT: return 'text'
    if ext in {'.xlsx','.xls'}: return 'spreadsheet'
    return 'unknown'
