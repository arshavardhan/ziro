import sqlite3
from contextlib import contextmanager
import config

@contextmanager
def connect():
    db = sqlite3.connect(config.DB_PATH,timeout=30)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
