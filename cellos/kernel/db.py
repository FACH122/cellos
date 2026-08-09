"""
Storage.

The kernel owns the connection, the write lock, and the two tables that belong
to no domain: the event log and the relationship graph. Every other table is
declared by the domain that owns it (see `domains/*/model.py`) and registered
here, so a rebuild can drop and recreate all of them without the kernel
knowing what any of them mean.

Nothing derivable is stored. Cell progress, dashboard totals and hierarchy
summaries have no columns anywhere; they are computed on read.
"""

import os
import sqlite3
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.environ.get("CELLOS_DB", os.path.join(ROOT, "data", "cellos.db"))

# Authoritative and permanent. Never dropped.
LOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT NOT NULL,
    actor_id    TEXT,
    cell_id     TEXT,
    subject_id  TEXT,
    payload     TEXT NOT NULL DEFAULT '{}',
    occurred_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_cell ON events (cell_id, id);
CREATE INDEX IF NOT EXISTS events_subject ON events (subject_id, id);
CREATE INDEX IF NOT EXISTS events_type ON events (type, id);
"""

# Runtime state, not organizational memory. Not projected, not rebuilt.
RUNTIME_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

# Every edge between entities lives here rather than in a foreign key, so a
# new kind of connection needs no migration. See kernel/relationships.py.
RELATIONSHIP_SCHEMA = """
CREATE TABLE relationships (
    id        TEXT PRIMARY KEY,
    kind      TEXT NOT NULL,
    from_kind TEXT NOT NULL,
    from_id   TEXT NOT NULL,
    to_kind   TEXT NOT NULL,
    to_id     TEXT NOT NULL,
    formed_at TEXT NOT NULL
);
CREATE INDEX rel_out ON relationships (kind, from_id);
CREATE INDEX rel_in  ON relationships (kind, to_id);
CREATE UNIQUE INDEX rel_unique ON relationships (kind, from_id, to_id);
"""

# Filled by domains at import time via `owns()`.
_projection_schemas = []
_projection_tables = []

_local = threading.local()

# Serializes every write. Held across read-check-append inside the workflow
# engine, which is what makes a transition atomic.
write_lock = threading.RLock()


def owns(tables, schema):
    """A domain declaring the tables it is responsible for."""
    _projection_tables.extend(tables)
    _projection_schemas.append(schema)


def projection_tables():
    return list(_projection_tables)


def use(path):
    """Point at a different database. For tests, which must never touch the real one."""
    global DB_PATH
    close()
    DB_PATH = path


def connect():
    """Thread-local connection. The HTTP server is threaded; SQLite is not."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA busy_timeout = 15000")
        _local.conn = conn
    return conn


def close():
    conn = getattr(_local, "conn", None)
    if conn is not None:
        conn.close()
        _local.conn = None


def init():
    """
    Make the database match the domains. Safe on every start, and returns
    whether the derived tables had to be built.

    A missing projection table means the shape has changed since this database
    was written -- a domain added one, or renamed one. The answer is not to
    patch the difference but to throw every projection away and rebuild from
    the log, which is exactly what the log is for. Anything else would leave
    two tables that disagree about when they were last correct.

    Before, a new table made `_all_present` false and sent the whole set
    through `CREATE TABLE`, which then failed on the first one that already
    existed. Adding a table to a live database could not be done at all.
    """
    conn = connect()
    with write_lock:
        conn.executescript(LOG_SCHEMA)
        conn.executescript(RUNTIME_SCHEMA)
        built = not _all_present(conn)
        if built:
            _drop_projections(conn)
            _create_projections(conn)
        conn.commit()
    return built


def _all_present(conn):
    """
    Whether the derived tables on disk are the ones the domains describe --
    every table, and every column of every table.

    Names alone were not enough. A domain adding a *column* left the old table
    in place, matching by name while missing the field, and the first query
    that mentioned it failed at runtime instead of at boot. Unit tests cannot
    catch that: they build a fresh database every run, so their schema is
    always the current one by construction. Only a database that has been
    around since before the change can be wrong.

    SQLite is the parser. The declared schema is built in memory and the two
    are compared column by column, which is exact and needs no SQL of our own
    to be read by hand.
    """
    expected = sqlite3.connect(":memory:")
    try:
        _create_projections(expected)
        for table in ["relationships"] + _projection_tables:
            live = [c[1] for c in conn.execute("PRAGMA table_info(%s)" % table)]
            if not live:
                return False
            want = [c[1] for c in expected.execute("PRAGMA table_info(%s)" % table)]
            if live != want:
                return False
    finally:
        expected.close()
    return True


def _create_projections(conn):
    conn.executescript(RELATIONSHIP_SCHEMA)
    for schema in _projection_schemas:
        conn.executescript(schema)


def _drop_projections(conn):
    for table in ["relationships"] + _projection_tables:
        conn.execute("DROP TABLE IF EXISTS %s" % table)


def drop_projections():
    """Throw away everything derived. The log survives."""
    conn = connect()
    with write_lock:
        _drop_projections(conn)
        _create_projections(conn)
        conn.commit()


# ---------------------------------------------------------------- reading

def rows(sql, params=()):
    return [dict(r) for r in connect().execute(sql, params).fetchall()]


def row(sql, params=()):
    r = connect().execute(sql, params).fetchone()
    return dict(r) if r else None


def value(sql, params=(), default=None):
    r = connect().execute(sql, params).fetchone()
    if r is None or r[0] is None:
        return default
    return r[0]


def marks(items):
    """`?,?,?` for an IN clause."""
    return ",".join("?" * len(items))
