from pathlib import Path
from .schemas import table_from_rows
from .report import table_exists, read_sql_table_or_empty

def compute_transcript_metrics(project, db_path):
    found=[]
    for t in ['transcript_events','speech_events','audio_transcripts']:
        if table_exists(db_path,t): found.append((t,len(read_sql_table_or_empty(db_path,t))))
    if not found and project and project.get('project_root'):
        for p in Path(project['project_root']).rglob('*'):
            if p.suffix.lower() in ['.vtt','.srt'] or 'transcript' in p.name.lower(): found.append((str(p),0))
    rows=[{'transcript_stream_available':bool(found),'reason':'' if found else 'No transcript/audio-derived files found.','source':found[0][0] if found else '','record_count':found[0][1] if found else 0,'possible_future_metrics':'speech_events, speaking_duration, turn_counts, speaker_distribution, MITM codes'}]
    return [table_from_rows('transcript_availability','Transcript availability','Transcript/audio-derived stream availability placeholder.','transcript',rows,columns=['transcript_stream_available','reason','source','record_count','possible_future_metrics'],caveat='Transcript metrics are optional and require transcript/audio-derived inputs.')]
