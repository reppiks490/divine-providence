"""Owner-local SQLite lifecycle; no schema or evidence-authority changes."""
from contextlib import closing, contextmanager
import sqlite3


@contextmanager
def sqlite_connection(path):
    with closing(sqlite3.connect(path)) as connection:
        with connection:
            yield connection
