HANDLERS={
 'tldraw_sqlite': {'label':'TLDraw SQLite Audit Log','available_actions':['inspect','parse','replay']},
 'drive_activity_csv': {'label':'Google Drive Activity CSV','available_actions':['inspect','parse','replay']},
 'document_changelog': {'label':'Document/Drive Changelog','available_actions':['inspect','parse','replay']},
 'workshop_folder': {'label':'Workshop Folder','available_actions':['inspect','build_catalog','parse_known_sources','replay']},
 'zip_archive': {'label':'Archive','available_actions':['inspect','extract_then_parse']},
}
def handler(name, confidence=0.0, warnings=None):
 d=dict(HANDLERS[name]); d['handler']=name; d['confidence']=confidence; d['warnings']=warnings or []; return d
