from __future__ import annotations
from pathlib import Path, PurePosixPath
from collections import Counter
import zipfile

IMPORTANT_NAMES=('dailyLog.csv','TLDraw Logs.db')

def _safe_member(name:str)->bool:
    p=PurePosixPath(name.replace('\\','/'))
    return not p.is_absolute() and '..' not in p.parts

def inspect_zip_archive(zip_path)->dict:
    zpath=Path(zip_path); out={'path':str(zpath),'entry_count':0,'root_folders':[],'counts_by_extension':{},'important_files':{'dailyLog.csv':[],'TLDraw Logs.db':[],'changelogs':[],'html_exports':[],'documents':[],'slides':[],'nested_zips':[]},'team_folders':[],'participant_folders':[],'unsafe_entries':[],'warnings':[]}
    if not zipfile.is_zipfile(zpath): out['warnings'].append('Not a valid ZIP archive.'); return out
    with zipfile.ZipFile(zpath) as z:
        names=z.namelist(); out['entry_count']=len(names); roots=[]; exts=Counter()
        for n in names:
            np=n.replace('\\','/')
            if not _safe_member(np): out['unsafe_entries'].append(n)
            parts=[p for p in np.split('/') if p]
            if parts: roots.append(parts[0])
            if np.endswith('/'): 
                if len(parts)>=2 and parts[-1].lower().startswith('team '): out['team_folders'].append(np.rstrip('/'))
                if len(parts)>=2 and parts[-1].lower().startswith('participant '): out['participant_folders'].append(np.rstrip('/'))
                continue
            ext=Path(np).suffix.lower() or '(none)'; exts[ext]+=1; name=Path(np).name
            if name=='dailyLog.csv': out['important_files']['dailyLog.csv'].append(np)
            if name=='TLDraw Logs.db': out['important_files']['TLDraw Logs.db'].append(np)
            if ext=='.txt' and 'changelog' in name.lower(): out['important_files']['changelogs'].append(np)
            if ext=='.html' and name.lower().startswith('email_export'): out['important_files']['html_exports'].append(np)
            if ext=='.docx': out['important_files']['documents'].append(np)
            if ext=='.pptx': out['important_files']['slides'].append(np)
            if ext=='.zip': out['important_files']['nested_zips'].append(np)
            if len(parts)>=2 and parts[-2].lower().startswith('team '): out['team_folders'].append('/'.join(parts[:-1]))
            if len(parts)>=2 and parts[-2].lower().startswith('participant '): out['participant_folders'].append('/'.join(parts[:-1]))
        out['root_folders']=sorted(set(roots)); out['counts_by_extension']=dict(sorted(exts.items())); out['team_folders']=sorted(set(out['team_folders'])); out['participant_folders']=sorted(set(out['participant_folders']))
        if out['unsafe_entries']: out['warnings'].append('Archive contains unsafe path traversal entries; safe extraction will refuse them.')
    return out

def extract_zip_to_workspace(zip_path, workspace_dir, safe=True)->dict:
    zpath=Path(zip_path); w=Path(workspace_dir); w.mkdir(parents=True,exist_ok=True); insp=inspect_zip_archive(zpath); extracted=[]
    if safe and insp['unsafe_entries']: return {'path':str(zpath),'workspace_dir':str(w),'extracted_count':0,'extracted_root_paths':[],'nested_zips':insp['important_files']['nested_zips'],'warnings':['Extraction refused because archive contains unsafe entries.']}
    with zipfile.ZipFile(zpath) as z:
        for info in z.infolist():
            if safe and not _safe_member(info.filename): continue
            z.extract(info,w); extracted.append(info.filename)
    roots=[str(w/r) for r in insp['root_folders']]
    return {'path':str(zpath),'workspace_dir':str(w),'extracted_count':len(extracted),'extracted_root_paths':roots,'nested_zips':insp['important_files']['nested_zips'],'warnings':insp['warnings']}
