"""
Permission: one place, derived, never scattered.

Answers are computed from four things and nothing else:

    membership   are they in this cell
    hierarchy    are they in a cell above it -- responsibility flows downward
    governance   what this cell's size makes formal
    responsibility  member or leader

There is no access control list and no role that grants sight of a cell you
are not inside. A person sees the cells they belong to and everything beneath
them; nothing above, ever.

Every `require_*` has an `allows()` twin so the interface can ask the same
question ahead of time instead of re-deriving the rule and drifting from it.
"""

from ...kernel.errors import NotAllowed
from ..hierarchy import service as hierarchy
from ..member import model as member_model
from ..member.rules import LEADER, MEMBER  # noqa: F401  (re-exported vocabulary)


def allows(check, *args, **kwargs):
    """Ask a requirement as a question. True if it would pass."""
    try:
        check(*args, **kwargs)
        return True
    except NotAllowed:
        return False


def membership(user_id, cell_id):
    return member_model.membership(user_id, cell_id)


# ------------------------------------------------------------------ sight

def visible_cell_ids(user_id):
    """Cells the person belongs to, plus every cell beneath those."""
    seen = set()
    for cell_id in member_model.cell_ids_of(user_id):
        if cell_id in seen:
            continue
        seen.update(hierarchy.subtree_ids(cell_id))
    return seen


def home_cell_ids(user_id):
    """
    Where a person's view starts: cells they belong to that are not already
    beneath another cell they belong to.
    """
    mine = member_model.cell_ids_of(user_id)
    mine_set = set(mine)
    return [c for c in mine if not (set(hierarchy.ancestor_ids(c)) & mine_set)]


def can_see(user_id, cell_id):
    return cell_id in visible_cell_ids(user_id)


def require_sight(user_id, cell_id):
    hierarchy.get(cell_id)
    if not can_see(user_id, cell_id):
        raise NotAllowed("This cell is not yours to see.")


# ------------------------------------------------------------------ acting

def is_member(user_id, cell_id):
    """Inside this cell, or inside one above it."""
    if membership(user_id, cell_id):
        return True
    return any(membership(user_id, above) for above in hierarchy.ancestor_ids(cell_id))


def require_member(user_id, cell_id):
    if not is_member(user_id, cell_id):
        raise NotAllowed("You are not part of this cell.")


def is_leader(user_id, cell_id):
    """A leader here, or a leader of any cell that contains it."""
    own = membership(user_id, cell_id)
    if own and own["role"] == LEADER:
        return True
    for above in hierarchy.ancestor_ids(cell_id):
        m = membership(user_id, above)
        if m and m["role"] == LEADER:
            return True
    return False


def require_leader(user_id, cell_id, action="do this"):
    require_member(user_id, cell_id)
    if not is_leader(user_id, cell_id):
        raise NotAllowed("Only a leader of this cell can %s." % action)


def standing(user_id, cell_id):
    """
    Everything the interface needs to know about where this person stands,
    computed once so no screen has to work any of it out.
    """
    own = membership(user_id, cell_id)
    return {
        "role": own["role"] if own else None,
        "is_member": bool(own),
        "acts_here": is_member(user_id, cell_id),
        "is_leader": is_leader(user_id, cell_id),
    }
