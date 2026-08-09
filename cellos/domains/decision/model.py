"""
Decision: storage.

Options belong to their decision -- they have no life without it, so they are
a column of it, not a relationship. The edges that *are* relationships are the
ones between independent things: the tasks a decision produced, the evidence
that supports it.

`state` is written only by the workflow engine's projector. No service in this
domain sets it.
"""

import json

from ...kernel import db

SCHEMA = """
CREATE TABLE decisions (
    id              TEXT PRIMARY KEY,
    cell_id         TEXT NOT NULL,
    question        TEXT NOT NULL,
    detail          TEXT NOT NULL DEFAULT '',
    state           TEXT NOT NULL,
    created_by      TEXT,
    created_at      TEXT NOT NULL,
    chosen_option   TEXT,
    decided_by      TEXT,
    decided_at      TEXT,
    decided_how     TEXT,
    resolution_note TEXT NOT NULL DEFAULT '',
    revision_note   TEXT NOT NULL DEFAULT '',
    outcome         TEXT,
    lesson          TEXT,
    closed_at       TEXT
);
CREATE INDEX decisions_cell ON decisions (cell_id, state);

CREATE TABLE options (
    id          TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL,
    text        TEXT NOT NULL,
    position    INTEGER NOT NULL,
    work        TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX options_decision ON options (decision_id, position);

CREATE TABLE votes (
    decision_id TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    option_id   TEXT NOT NULL,
    cast_at     TEXT NOT NULL,
    PRIMARY KEY (decision_id, user_id)
);

CREATE TABLE remarks (
    id          INTEGER PRIMARY KEY,
    decision_id TEXT NOT NULL,
    author_id   TEXT,
    body        TEXT NOT NULL,
    said_at     TEXT NOT NULL
);
CREATE INDEX remarks_decision ON remarks (decision_id, id);
"""

db.owns(["decisions", "options", "votes", "remarks"], SCHEMA)


def get(decision_id):
    return db.row("SELECT * FROM decisions WHERE id = ?", (decision_id,))


def many(decision_ids):
    """Several by id, oldest first."""
    decision_ids = list(decision_ids)
    if not decision_ids:
        return []
    return db.rows(
        "SELECT * FROM decisions WHERE id IN (%s) ORDER BY created_at, id"
        % db.marks(decision_ids),
        decision_ids,
    )


def state_of(decision_id):
    return db.value("SELECT state FROM decisions WHERE id = ?", (decision_id,))


def options_of(decision_id):
    out = db.rows(
        "SELECT * FROM options WHERE decision_id = ? ORDER BY position", (decision_id,)
    )
    for o in out:
        o["work"] = json.loads(o["work"])
    return out


def option(option_id, decision_id=None):
    if decision_id:
        return db.row(
            "SELECT * FROM options WHERE id = ? AND decision_id = ?", (option_id, decision_id)
        )
    return db.row("SELECT * FROM options WHERE id = ?", (option_id,))


def vote_counts(decision_id):
    return {
        r["option_id"]: r["n"]
        for r in db.rows(
            "SELECT option_id, count(*) AS n FROM votes WHERE decision_id = ? GROUP BY option_id",
            (decision_id,),
        )
    }


def vote_of(decision_id, user_id):
    return db.value(
        "SELECT option_id FROM votes WHERE decision_id = ? AND user_id = ?",
        (decision_id, user_id),
    )


def voters_by_option(decision_id):
    grouped = {}
    for r in db.rows(
        """
        SELECT v.option_id, u.name FROM votes v JOIN users u ON u.id = v.user_id
        WHERE v.decision_id = ? ORDER BY u.name
        """,
        (decision_id,),
    ):
        grouped.setdefault(r["option_id"], []).append(r["name"])
    return grouped


def remarks_of(decision_id):
    return db.rows(
        """
        SELECT r.*, u.name AS author_name
        FROM remarks r LEFT JOIN users u ON u.id = r.author_id
        WHERE r.decision_id = ? ORDER BY r.id
        """,
        (decision_id,),
    )


def in_cells(cell_ids, states=None, limit=None):
    cell_ids = list(cell_ids)
    if not cell_ids:
        return []
    sql = "SELECT * FROM decisions WHERE cell_id IN (%s)" % db.marks(cell_ids)
    params = list(cell_ids)
    if states:
        states = list(states)
        sql += " AND state IN (%s)" % db.marks(states)
        params.extend(states)
    sql += " ORDER BY created_at DESC"
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    return db.rows(sql, params)


def count_by_state(cell_ids):
    cell_ids = list(cell_ids)
    if not cell_ids:
        return {}
    return {
        r["state"]: r["n"]
        for r in db.rows(
            "SELECT state, count(*) AS n FROM decisions WHERE cell_id IN (%s) GROUP BY state"
            % db.marks(cell_ids),
            cell_ids,
        )
    }


def count_by_how(cell_ids):
    cell_ids = list(cell_ids)
    if not cell_ids:
        return {}
    return {
        r["decided_how"]: r["n"]
        for r in db.rows(
            "SELECT decided_how, count(*) AS n FROM decisions WHERE cell_id IN (%s)"
            " AND decided_how IS NOT NULL GROUP BY decided_how" % db.marks(cell_ids),
            cell_ids,
        )
    }


def ids_voted_on_by(user_id, cell_ids):
    cell_ids = list(cell_ids)
    if not cell_ids:
        return []
    return [
        r["decision_id"]
        for r in db.rows(
            "SELECT DISTINCT v.decision_id FROM votes v JOIN decisions d ON d.id = v.decision_id"
            " WHERE v.user_id = ? AND d.cell_id IN (%s)" % db.marks(cell_ids),
            [user_id] + cell_ids,
        )
    ]
