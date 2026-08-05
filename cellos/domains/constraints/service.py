"""
Constraints: derived, never stored beyond the commitment itself.

A cell stores the budget it committed to. What it has spent is not stored --
it is the sum of what the work cost, rolled up through the child cells exactly
the way progress is. A task stores the date it is wanted by; whether it is
late is worked out on read against today.

This domain owns no table. It reads the two optional facts other domains keep
and answers what they mean right now.
"""

import datetime

from ..cell import model as cell_model
from ..hierarchy import service as hierarchy
from ..task import model as task_model
from . import rules


def today():
    return datetime.date.today()


def budget_of(cell_id, scope=None):
    """
    How this cell stands against what it committed to spending -- or nothing
    at all, if it never committed to anything. A cell with no budget is not a
    cell at 0%; it is a cell the question does not apply to.
    """
    cell = cell_model.get(cell_id)
    if cell is None or cell["budget"] is None:
        return None

    scope = scope or hierarchy.subtree_ids(cell_id)
    spent = task_model.cost_in(scope)
    used = rules.share(spent, cell["budget"])
    return {
        "amount": cell["budget"],
        "currency": cell["currency"],
        "spent": round(spent, 2),
        "remaining": round(cell["budget"] - spent, 2),
        "share": None if used is None else round(used * 100),
        "over": spent > cell["budget"],
        "reads": "%s of %s" % (rules.money(spent, cell["currency"]),
                               rules.money(cell["budget"], cell["currency"])),
    }


def deadline_of(cell_id):
    """When this cell is wanted by, or nothing at all."""
    cell = cell_model.get(cell_id)
    if cell is None or not cell.get("due_on"):
        return None
    left = rules.days_between(cell["due_on"], today())
    return {"due_on": cell["due_on"], "days_left": left, "late": left < 0}


def deadlines_in(scope, when=None):
    """Dated work, sorted by how much it matters: late first, then imminent."""
    when = when or today()
    late, soon, ahead = [], [], []
    for t in task_model.due_in(scope):
        left = rules.days_between(t["due_on"], when)
        row = {"id": t["id"], "title": t["title"], "cell_id": t["cell_id"],
               "due_on": t["due_on"], "days_left": left,
               "owner_name": t["owner_name"], "progress": t["progress"]}
        (late if left < 0 else soon if left <= rules.SOON_DAYS else ahead).append(row)
    return {"late": late, "soon": soon, "ahead": ahead}


def friction(cell_id, scope=None, when=None):
    """
    What the cell's own commitments are costing it. Fed to the health layer
    like any other domain's signals -- constraints do not get special
    treatment for having been chosen deliberately.
    """
    scope = scope or hierarchy.subtree_ids(cell_id)
    when = when or today()
    signals = []

    for t in task_model.due_in(scope):
        signals += rules.deadline_friction(t["title"], t["due_on"], when, t["progress"])

    money = budget_of(cell_id, scope)
    if money:
        remaining = len(task_model.in_cells(scope, unfinished_only=True))
        signals += rules.budget_friction(
            money["spent"], money["amount"], money["currency"], remaining)

    signals += _own_deadline(cell_id, when)
    return signals


def _own_deadline(cell_id, when):
    """
    The cell's own date, and anything inside it promised for later than the
    whole. Nothing is blocked or refused -- the contradiction is simply said
    out loud, which is the only thing software is in a position to do about it.
    """
    from ..progress import service as progress

    cell = cell_model.get(cell_id)
    if cell is None or not cell.get("due_on"):
        return []

    mine = cell["due_on"]
    signals = rules.cell_deadline_friction(
        cell["goal"], mine, when, progress.of_cell(cell_id)["percent"])

    for t in task_model.due_in([cell_id]):
        signals += rules.inconsistent_deadline("the work", t["title"], t["due_on"], mine)
    for child in hierarchy.children(cell_id):
        signals += rules.inconsistent_deadline("the cell", child["goal"],
                                               child.get("due_on"), mine)
    return signals


def of_cell(cell_id):
    """Everything this cell committed to, or None when it committed to nothing."""
    scope = hierarchy.subtree_ids(cell_id)
    money = budget_of(cell_id, scope)
    dates = deadlines_in(scope)
    own = deadline_of(cell_id)
    if not money and not own and not (dates["late"] or dates["soon"] or dates["ahead"]):
        return None
    return {"budget": money, "due": own, "deadlines": dates}
