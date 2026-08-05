"""
Cell: storage.

One table, and no parent column. Containment is a typed relationship
(`contains`) owned by the hierarchy domain, so a cell row says only what a
cell is -- a goal and when it started -- and never where it sits.
"""

from ...kernel import db

SCHEMA = """
CREATE TABLE cells (
    id         TEXT PRIMARY KEY,
    goal       TEXT NOT NULL,
    created_by TEXT,
    created_at TEXT NOT NULL,
    -- Optional, and null until somebody chooses to commit to one. A cell
    -- with no budget is not a cell with a budget of zero.
    budget     REAL,
    currency   TEXT
);
"""

db.owns(["cells"], SCHEMA)


def get(cell_id):
    return db.row("SELECT * FROM cells WHERE id = ?", (cell_id,))


def exists(cell_id):
    return db.row("SELECT 1 FROM cells WHERE id = ?", (cell_id,)) is not None


def many(cell_ids):
    cell_ids = list(cell_ids)
    if not cell_ids:
        return []
    return db.rows(
        "SELECT * FROM cells WHERE id IN (%s) ORDER BY created_at" % db.marks(cell_ids),
        cell_ids,
    )
