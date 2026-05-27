from ..storage.repositories import upsert_participants_from_events
def rebuild(db_path): upsert_participants_from_events(db_path)
