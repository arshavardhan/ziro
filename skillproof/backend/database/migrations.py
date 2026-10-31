from database.connection import connect
from database.models import SCHEMA

def migrate():
    with connect() as db:
        db.execute('PRAGMA journal_mode=WAL')
        for statement in SCHEMA:
            db.execute(statement)
        db.execute('INSERT OR IGNORE INTO schema_migrations(version) VALUES (2)')
        db.execute('INSERT OR IGNORE INTO schema_migrations(version) VALUES (3)')
    from services.provenance_service import preserve_legacy
    from services.evaluation_service import preserve_original
    preserve_legacy()
    preserve_original()
    # Legacy v1 analysis_sessions remain readable as archival SQL data, not v2 sessions.
