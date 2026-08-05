"""
Evidence: storage.

No subject_kind/subject_id pair. What a piece of evidence supports is a typed
relationship, so evidence can support a decision today and something that does
not exist yet tomorrow without touching this table.
"""

from ...kernel import db

SCHEMA = """
CREATE TABLE evidence (
    id       TEXT PRIMARY KEY,
    cell_id  TEXT NOT NULL,
    kind     TEXT NOT NULL,
    label    TEXT NOT NULL,
    ref      TEXT NOT NULL DEFAULT '',
    added_by TEXT,
    added_at TEXT NOT NULL
);
CREATE INDEX evidence_cell ON evidence (cell_id);
"""

db.owns(["evidence"], SCHEMA)


def get(evidence_id):
    return db.row("SELECT * FROM evidence WHERE id = ?", (evidence_id,))


def many(evidence_ids):
    evidence_ids = list(evidence_ids)
    if not evidence_ids:
        return []
    return db.rows(
        """
        SELECT e.*, u.name AS added_by_name
        FROM evidence e LEFT JOIN users u ON u.id = e.added_by
        WHERE e.id IN (%s) ORDER BY e.added_at
        """ % db.marks(evidence_ids),
        evidence_ids,
    )


def count_in(cell_ids):
    cell_ids = list(cell_ids)
    if not cell_ids:
        return 0
    return db.value(
        "SELECT count(*) FROM evidence WHERE cell_id IN (%s)" % db.marks(cell_ids),
        cell_ids,
        default=0,
    )
