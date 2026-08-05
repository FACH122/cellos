"""
Progress: derived, never stored.

This domain owns no table and emits no event. A cell's progress is the
progress its members reported on their own tasks, rolled up through the child
cells and weighted by how much work each holds. It is recomputed every time it
is asked for, so no manager can set it and it cannot drift from the work it
describes.

The rollup is iterative and deepest-first, and reads the whole subtree in
three queries rather than one per cell. That is not only faster -- it means
depth is genuinely unlimited, with no Python stack to run out of.
"""

from ..hierarchy import rules as hierarchy_rules, service as hierarchy
from ..task import model as task_model

EMPTY = {"percent": 0, "task_count": 0, "done": 0, "remaining": 0}


def of_cell(cell_id):
    """Progress of this cell and everything beneath it, to any depth."""
    levels = hierarchy.walk(cell_id)
    if not levels:
        return dict(EMPTY)

    ids = [c["id"] for c in levels]
    own = task_model.tallies_for(ids)
    children = _child_map(ids)

    rolled = {}
    for cell in sorted(levels, key=lambda c: -c["depth"]):
        below = [rolled[k] for k in children.get(cell["id"], []) if k in rolled]
        rolled[cell["id"]] = hierarchy_rules.rollup(
            own.get(cell["id"], (0, 0, 0)),
            [(b["task_count"], b["percent"] * b["task_count"], b["done"]) for b in below],
        )
    return rolled[cell_id]


def of_cells(cell_ids):
    """Progress for several cells at once, for a list of children."""
    return {cell_id: of_cell(cell_id) for cell_id in cell_ids}


def of_tasks(tasks):
    """Progress across an arbitrary handful of work, for one person's own list."""
    if not tasks:
        return dict(EMPTY)
    done = sum(1 for t in tasks if t["progress"] >= 100)
    return {
        "percent": int(round(sum(t["progress"] for t in tasks) / len(tasks))),
        "task_count": len(tasks),
        "done": done,
        "remaining": len(tasks) - done,
    }


def _child_map(cell_ids):
    """parent -> [children], for the cells being rolled up, in one query."""
    from ...kernel import db

    if not cell_ids:
        return {}
    out = {}
    for r in db.rows(
        "SELECT from_id, to_id FROM relationships WHERE kind = 'contains'"
        " AND from_id IN (%s)" % db.marks(cell_ids),
        cell_ids,
    ):
        out.setdefault(r["from_id"], []).append(r["to_id"])
    return out
