"""
Task: storage.

There is no `state` column. A task's state is a function of facts it already
stores -- whether anyone holds it, how far along it is, and whether it grew
into a cell -- so storing it as well would be another copy that could disagree
with them.

There is no `decision_id` column either, and no `expanded_into`. Which
decision produced a task, and which cell it grew into, are typed
relationships, so the same table serves work that came from a decision, work
somebody just added, and work that turned out to be a group's job.
"""

from ...kernel import db
from . import rules

SCHEMA = """
CREATE TABLE tasks (
    id           TEXT PRIMARY KEY,
    cell_id      TEXT NOT NULL,
    title        TEXT NOT NULL,
    owner_id     TEXT,
    progress     INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL,
    completed_at TEXT,
    -- Both optional, both null until somebody commits to them.
    due_on       TEXT,
    cost         REAL
);
CREATE INDEX tasks_due ON tasks (due_on);
CREATE INDEX tasks_cell ON tasks (cell_id, progress);
CREATE INDEX tasks_owner ON tasks (owner_id, progress);

-- What somebody said while doing the work.
--
-- A decision has remarks, which is where a cell argues before it settles
-- something. Work has notes, which is a different act: what was found, what
-- is in the way, what was tried. The two look alike and belong to different
-- domains, so the task domain keeps its own rather than borrowing.
CREATE TABLE notes (
    id        TEXT PRIMARY KEY,
    task_id   TEXT NOT NULL,
    author_id TEXT NOT NULL,
    body      TEXT NOT NULL,
    said_at   TEXT NOT NULL
);
CREATE INDEX notes_task ON notes (task_id, id);
"""

db.owns(["tasks", "notes"], SCHEMA)

# Work that became a cell. Its progress now comes back up from that cell, so
# counting it here as well would count the same work twice.
_EXPANDED = "SELECT from_id FROM relationships WHERE kind = 'expands_into'"

# The one place the state derivation is written in SQL, for queries that
# cannot call Python. It must agree with rules.state_of.
_STATE = """
    CASE WHEN grew.to_id IS NOT NULL THEN 'expanded'
         WHEN t.progress >= 100 THEN 'done'
         WHEN t.owner_id IS NOT NULL THEN 'active'
         ELSE 'open' END
"""

_SELECT = """
    SELECT t.*, %s AS state, u.name AS owner_name,
           grew.to_id AS expanded_into, c.goal AS expanded_goal
    FROM tasks t
    LEFT JOIN users u ON u.id = t.owner_id
    LEFT JOIN relationships grew ON grew.kind = 'expands_into' AND grew.from_id = t.id
    LEFT JOIN cells c ON c.id = grew.to_id
""" % _STATE


def get(task_id):
    return db.row(_SELECT + " WHERE t.id = ?", (task_id,))


def many(task_ids):
    task_ids = list(task_ids)
    if not task_ids:
        return []
    return db.rows(
        _SELECT + " WHERE t.id IN (%s) ORDER BY t.created_at" % db.marks(task_ids), task_ids
    )


def in_cells(cell_ids, owner_id=None, unfinished_only=False):
    cell_ids = list(cell_ids)
    if not cell_ids:
        return []
    sql = _SELECT + " WHERE t.cell_id IN (%s)" % db.marks(cell_ids)
    params = list(cell_ids)
    if owner_id:
        sql += " AND t.owner_id = ?"
        params.append(owner_id)
    if unfinished_only:
        sql += " AND t.progress < 100 AND grew.to_id IS NULL"
    sql += " ORDER BY t.progress >= 100, t.created_at"
    return db.rows(sql, params)


def tally_for(cell_id):
    """
    (count, summed progress, finished) for one cell -- the progress rollup's
    input. Work that expanded into a cell is left out here: it is counted one
    level down, as the cell it became.
    """
    return tallies_for([cell_id]).get(cell_id, (0, 0, 0))


def tallies_for(cell_ids):
    """The same, for a whole subtree in one query."""
    cell_ids = list(cell_ids)
    if not cell_ids:
        return {}
    rows = db.rows(
        "SELECT cell_id, count(*) AS n, coalesce(sum(progress), 0) AS total,"
        " coalesce(sum(progress >= 100), 0) AS done"
        " FROM tasks WHERE cell_id IN (%s) AND id NOT IN (%s) GROUP BY cell_id"
        % (db.marks(cell_ids), _EXPANDED),
        cell_ids,
    )
    return {r["cell_id"]: (r["n"], r["total"], r["done"]) for r in rows}


def cost_in(cell_ids):
    """What the work in these cells has cost so far. Work that expanded is
    counted in the cell it became, one level down."""
    cell_ids = list(cell_ids)
    if not cell_ids:
        return 0.0
    return db.value(
        "SELECT coalesce(sum(cost), 0) FROM tasks WHERE cell_id IN (%s)"
        " AND id NOT IN (%s)" % (db.marks(cell_ids), _EXPANDED),
        cell_ids, default=0.0)


def due_in(cell_ids, unfinished_only=True):
    """Work with a date on it, soonest first."""
    cell_ids = list(cell_ids)
    if not cell_ids:
        return []
    sql = _SELECT + " WHERE t.cell_id IN (%s) AND t.due_on IS NOT NULL" % db.marks(cell_ids)
    if unfinished_only:
        sql += " AND t.progress < 100 AND grew.to_id IS NULL"
    return db.rows(sql + " ORDER BY t.due_on", cell_ids)


def unowned_count(cell_ids):
    cell_ids = list(cell_ids)
    if not cell_ids:
        return 0
    return db.value(
        "SELECT count(*) FROM tasks WHERE cell_id IN (%s) AND owner_id IS NULL"
        " AND progress < 100 AND id NOT IN (%s)" % (db.marks(cell_ids), _EXPANDED),
        cell_ids,
        default=0,
    )


def stalled_count(cell_ids):
    """Work somebody holds and has not started. The thing a leader wants to see."""
    cell_ids = list(cell_ids)
    if not cell_ids:
        return 0
    return db.value(
        "SELECT count(*) FROM tasks WHERE cell_id IN (%s) AND owner_id IS NOT NULL"
        " AND progress = 0 AND id NOT IN (%s)" % (db.marks(cell_ids), _EXPANDED),
        cell_ids,
        default=0,
    )


def all_done(task_ids):
    """
    Whether a decision's work is finished. Work that became a cell counts as
    settled here -- the decision is not waiting on it any more, that cell is.
    """
    task_ids = list(task_ids)
    if not task_ids:
        return False
    remaining = db.value(
        "SELECT count(*) FROM tasks WHERE id IN (%s) AND progress < 100"
        " AND id NOT IN (%s)" % (db.marks(task_ids), _EXPANDED),
        task_ids,
        default=0,
    )
    return remaining == 0


def state_of(task_id):
    task = get(task_id)
    return None if task is None else task["state"]


def notes_of(task_id):
    """What has been said while doing this, oldest first."""
    return db.rows(
        """
        SELECT n.*, u.name AS author_name
        FROM notes n LEFT JOIN users u ON u.id = n.author_id
        WHERE n.task_id = ? ORDER BY n.id
        """,
        (task_id,),
    )
