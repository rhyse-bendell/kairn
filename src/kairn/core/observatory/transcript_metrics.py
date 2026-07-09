from __future__ import annotations

import re
from .schemas import table_from_rows
from .report import read_sql_table_or_empty

KEYWORDS = ["problem","framing","resilience","infrastructure","equity","community","system","scale","stakeholder","data","decision","adaptation"]

def _num(v):
    try: return float(v or 0)
    except Exception: return 0.0

def _word(v):
    try: return int(float(v or 0))
    except Exception: return len(str(v or '').split())

def compute_transcript_metrics(project, db_path):
    rows = read_sql_table_or_empty(db_path, 'transcript_turn_events')
    if not rows:
        found=[]
        try:
            from pathlib import Path
            for p in Path(project.get('project_root') or '.').rglob('*'):
                if p.suffix.lower() in ['.vtt','.srt'] or 'transcript' in p.name.lower(): found.append((str(p),0))
        except Exception: pass
        return [table_from_rows('transcript_availability','Transcript availability','Transcript/audio-derived stream availability placeholder.','transcript',[{'transcript_stream_available':bool(found),'reason':'' if found else 'No transcript/audio-derived files found.','source':found[0][0] if found else '','record_count':found[0][1] if found else 0,'possible_future_metrics':'speech_events, speaking_duration, turn_counts, speaker_distribution, MITM codes'}],columns=['transcript_stream_available','reason','source','record_count','possible_future_metrics'],caveat='Transcript metrics are optional and require transcript/audio-derived inputs.')]
    for r in rows:
        r['speaker']=r.get('speaker') or 'unknown'; r['team_or_session']=r.get('team_or_session') or 'unknown'; r['word_count_num']=_word(r.get('word_count')); r['duration_num']=_num(r.get('duration_seconds')); r['start_num']=_num(r.get('start_seconds')); r['end_num']=_num(r.get('end_seconds'))
    tabs=[]
    tabs.append(table_from_rows('transcript_overall_counts','Transcript overall counts','SRT transcript turn totals.','transcript',[{'total_turns':len(rows),'unique_speakers':len({r['speaker'] for r in rows}),'total_words':sum(r['word_count_num'] for r in rows),'total_speech_duration_seconds':round(sum(r['duration_num'] for r in rows),3),'first_start_seconds':min([r['start_num'] for r in rows] or [0]),'last_end_seconds':max([r['end_num'] for r in rows] or [0]),'unique_sessions_or_teams':len({r['team_or_session'] for r in rows})}],columns=['total_turns','unique_speakers','total_words','total_speech_duration_seconds','first_start_seconds','last_end_seconds','unique_sessions_or_teams']))
    def agg(keys):
        d={}
        for r in rows:
            k=tuple(r[x] for x in keys); g=d.setdefault(k,{x:k[i] for i,x in enumerate(keys)}|{'turn_count':0,'word_count':0,'speech_duration_seconds':0.0,'first_start_seconds':r['start_num'],'last_end_seconds':r['end_num'],'speakers':set()})
            g['turn_count']+=1; g['word_count']+=r['word_count_num']; g['speech_duration_seconds']+=r['duration_num']; g['first_start_seconds']=min(g['first_start_seconds'],r['start_num']); g['last_end_seconds']=max(g['last_end_seconds'],r['end_num']); g['speakers'].add(r['speaker'])
        return list(d.values())
    sp=agg(['speaker','team_or_session'])
    for g in sp: g['speech_duration_seconds']=round(g['speech_duration_seconds'],3); g['mean_turn_words']=round(g['word_count']/g['turn_count'],2) if g['turn_count'] else 0; g.pop('speakers',None)
    tabs.append(table_from_rows('transcript_speaker_summary','Transcript speaker summary','Turn, word, and duration counts by speaker/session.','transcript',sp,columns=['speaker','team_or_session','turn_count','word_count','speech_duration_seconds','mean_turn_words','first_start_seconds','last_end_seconds']))
    tm=agg(['team_or_session'])
    for g in tm: g['unique_speakers']=len(g.pop('speakers')); g['speech_duration_seconds']=round(g['speech_duration_seconds'],3)
    tabs.append(table_from_rows('transcript_team_summary','Transcript team summary','Turn, word, speaker, and duration counts by session/team.','transcript',tm,columns=['team_or_session','turn_count','unique_speakers','word_count','speech_duration_seconds','first_start_seconds','last_end_seconds']))
    bins={}
    for r in rows:
        b=int(r['start_num']//300*300); k=(r['team_or_session'],b); g=bins.setdefault(k,{'team_or_session':k[0],'bin_start_seconds':b,'bin_minutes':5,'turn_count':0,'word_count':0,'speakers':set()}); g['turn_count']+=1; g['word_count']+=r['word_count_num']; g['speakers'].add(r['speaker'])
    br=[]
    for g in bins.values(): g['unique_speakers']=len(g.pop('speakers')); br.append(g)
    tabs.append(table_from_rows('transcript_turns_by_time_bin','Transcript turns by time bin','Transcript activity in five-minute relative-time bins.','transcript',sorted(br,key=lambda x:(x['team_or_session'],x['bin_start_seconds'])),columns=['team_or_session','bin_start_seconds','bin_minutes','turn_count','word_count','unique_speakers']))
    sn=sorted(rows,key=lambda r:(-r['word_count_num'], r['start_num']))[:100]
    tabs.append(table_from_rows('transcript_representative_snippets','Transcript representative snippets','Representative transcript snippets; descriptive only.','transcript',[{'team_or_session':r['team_or_session'],'speaker':r['speaker'],'start_seconds':r['start_num'],'end_seconds':r['end_num'],'text_snippet':str(r.get('text',''))[:240],'word_count':r['word_count_num']} for r in sn],columns=['team_or_session','speaker','start_seconds','end_seconds','text_snippet','word_count']))
    kc=[]
    for team in sorted({r['team_or_session'] for r in rows}):
        trs=[r for r in rows if r['team_or_session']==team]
        for kw in KEYWORDS:
            pat=re.compile(r'\b'+re.escape(kw)+r'\w*\b', re.I); mentions=sum(len(pat.findall(str(r.get('text','')))) for r in trs); turns=sum(bool(pat.search(str(r.get('text','')))) for r in trs)
            kc.append({'team_or_session':team,'keyword':kw,'mention_count':mentions,'turn_count':turns})
    tabs.append(table_from_rows('transcript_keyword_counts','Transcript keyword counts','Transparent keyword counts for workshop terms.','transcript',kc,columns=['team_or_session','keyword','mention_count','turn_count']))
    return tabs
