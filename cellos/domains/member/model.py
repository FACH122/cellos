"""
Member: storage.

This domain owns who people are and which cells they belong to. No other
domain writes these tables; they ask through `service`.
"""

from ...kernel import db

SCHEMA = """
CREATE TABLE users (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    registered_at TEXT NOT NULL
);

CREATE TABLE memberships (
    cell_id   TEXT NOT NULL,
    user_id   TEXT NOT NULL,
    role      TEXT NOT NULL,
    joined_at TEXT NOT NULL,
    PRIMARY KEY (cell_id, user_id)
);
CREATE INDEX memberships_user ON memberships (user_id);
"""

db.owns(["users", "memberships"], SCHEMA)


def user(user_id):
    return db.row("SELECT * FROM users WHERE id = ?", (user_id,))


def user_by_email(email):
    return db.row("SELECT * FROM users WHERE email = ?", (email,))


def names(user_ids=None):
    """id -> name, for rendering someone else's action."""
    if user_ids is None:
        return {r["id"]: r["name"] for r in db.rows("SELECT id, name FROM users")}
    user_ids = list(user_ids)
    if not user_ids:
        return {}
    return {
        r["id"]: r["name"]
        for r in db.rows(
            "SELECT id, name FROM users WHERE id IN (%s)" % db.marks(user_ids), user_ids
        )
    }


def membership(user_id, cell_id):
    return db.row(
        "SELECT * FROM memberships WHERE cell_id = ? AND user_id = ?", (cell_id, user_id)
    )


def members_of(cell_id):
    return db.rows(
        """
        SELECT u.id, u.name, u.email, m.role, m.joined_at
        FROM memberships m JOIN users u ON u.id = m.user_id
        WHERE m.cell_id = ?
        ORDER BY m.role = 'leader' DESC, m.joined_at
        """,
        (cell_id,),
    )


def cell_ids_of(user_id):
    return [
        r["cell_id"]
        for r in db.rows("SELECT cell_id FROM memberships WHERE user_id = ?", (user_id,))
    ]


def head_count(cell_ids):
    """Distinct people across a set of cells."""
    cell_ids = list(cell_ids)
    if not cell_ids:
        return 0
    return db.value(
        "SELECT count(DISTINCT user_id) FROM memberships WHERE cell_id IN (%s)"
        % db.marks(cell_ids),
        cell_ids,
        default=0,
    )


def leader_count(cell_id):
    return db.value(
        "SELECT count(*) FROM memberships WHERE cell_id = ? AND role = 'leader'",
        (cell_id,),
        default=0,
    )
