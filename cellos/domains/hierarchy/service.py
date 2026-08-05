"""
Hierarchy: the shape of the organisation.

This domain owns no table. It owns the meaning of one relationship kind --
`contains` -- and every way of walking it.

There is no maximum depth, and no recursion in the walking. A cell inside a
cell inside a cell is not a special case of anything; it is a cell. The only
structural rule is that nothing may contain itself, directly or at any
remove, because that is not depth -- it is a loop.
"""

from ...kernel import db, relationships
from ...kernel.errors import DomainError, NotFound
from ..cell import model as cell_model
from ..member import model as member_model

CONTAINS = relationships.register(
    "contains", "cell", "cell", single_head=True,
    description="A cell holding a cell. One parent, any number of children, any depth.",
)


def get(cell_id):
    cell = cell_model.get(cell_id)
    if cell is None:
        raise NotFound("No such cell.")
    return cell


def parent_id(cell_id):
    return relationships.head_of(CONTAINS, cell_id)


def child_ids(cell_id):
    return relationships.heads(CONTAINS, cell_id)


def children(cell_id):
    return cell_model.many(child_ids(cell_id))


def subtree_ids(cell_id):
    """
    This cell and everything beneath it, to any depth. SQLite walks it, so
    there is no Python stack to run out of.
    """
    return [
        r["id"]
        for r in db.rows(
            """
            WITH RECURSIVE below(id) AS (
                SELECT id FROM cells WHERE id = ?
                UNION
                SELECT r.to_id FROM relationships r JOIN below b ON r.from_id = b.id
                 WHERE r.kind = 'contains'
            )
            SELECT id FROM below
            """,
            (cell_id,),
        )
    ]


def ancestor_ids(cell_id):
    """Walked upward for loop checks. No user is ever shown anything up here."""
    return [
        r["id"]
        for r in db.rows(
            """
            WITH RECURSIVE above(id) AS (
                SELECT id FROM cells WHERE id = ?
                UNION
                SELECT r.from_id FROM relationships r JOIN above a ON r.to_id = a.id
                 WHERE r.kind = 'contains'
            )
            SELECT id FROM above WHERE id != ?
            """,
            (cell_id, cell_id),
        )
    ]


def path(cell_id):
    """Ordered root-to-cell. Iterative; callers prune it to what the reader may see."""
    chain, seen = [], set()
    current = cell_id
    while current and current not in seen:
        seen.add(current)
        cell = cell_model.get(current)
        if cell is None:
            break
        chain.append({"id": cell["id"], "goal": cell["goal"]})
        current = parent_id(current)
    chain.reverse()
    return chain


def depth(cell_id):
    """How deep this sits. Reported, never limited."""
    return len(ancestor_ids(cell_id))


def scale(cell_id):
    """
    How many people this cell is responsible for, itself and beneath. Scale --
    not the member count of one cell -- is what capabilities emerge from: four
    leaders coordinating six hundred people are not a small cell.
    """
    return member_model.head_count(subtree_ids(cell_id))


def check_placement(parent):
    if parent is None:
        return
    get(parent)


def place_under(actor_id, parent, child_id):
    """
    Record containment. The only rule is that nothing may contain itself, at
    any remove -- a loop is not deep nesting, it is a broken graph.
    """
    get(parent)
    if parent == child_id or parent in subtree_ids(child_id):
        raise DomainError("A cell cannot contain itself.")
    relationships.form(CONTAINS, "cell", parent, "cell", child_id,
                       actor_id=actor_id, cell_id=child_id)


def walk(cell_id, visible_ids=None):
    """
    Every cell in the subtree with its depth, breadth-first and iterative, so
    an organisation nested a thousand deep reads the same as one nested twice.
    """
    out, queue = [], [(cell_id, 0)]
    seen = set()
    while queue:
        current, level = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        cell = cell_model.get(current)
        if cell is None:
            continue
        out.append({"id": cell["id"], "goal": cell["goal"], "depth": level})
        for child in child_ids(current):
            if visible_ids is None or child in visible_ids:
                queue.append((child, level + 1))
    return out


def tree(cell_id, visible_ids=None):
    """Nested shape, built from the flat walk so nothing recurses."""
    flat = walk(cell_id, visible_ids)
    nodes = {c["id"]: dict(c, children=[]) for c in flat}
    root = None
    for cell in flat:
        parent = parent_id(cell["id"])
        if parent in nodes and cell["id"] != cell_id:
            nodes[parent]["children"].append(nodes[cell["id"]])
        elif cell["id"] == cell_id:
            root = nodes[cell["id"]]
    return root
