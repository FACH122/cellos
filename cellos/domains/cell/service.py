"""
Cell: the public interface of this domain.

A cell is one group of people pursuing one goal. It is the only container in
CellOS -- no organisations, no workspaces, no projects. A company and a
wedding are the same row, and a cell nested six deep is the same row again.

There is exactly one way a cell comes to sit inside another: a piece of work
expanded into it. Creating a "child cell" directly is the same act with the
task step hidden, and it is implemented that way rather than as a second code
path -- so every nested cell has a mission it came from, and there is no
second kind of cell to reason about.
"""

from ...kernel import events
from .. import permission
from ..governance import rules as governance_rules, service as governance
from ..hierarchy import service as hierarchy
from ..member import service as member
from . import model, rules


def get(cell_id):
    return hierarchy.get(cell_id)


def may_create_child(actor_id, parent_id):
    """
    Whether to offer the shortcut. Expanding a particular task is always open
    to a leader -- the work justifies it. Offering "start a group" with no
    work behind it is what waits for the cell to be large enough to need it.
    """
    return (
        governance.has(parent_id, governance_rules.CHILDREN)
        and permission.allows(permission.require_leader, actor_id, parent_id)
    )


def create(actor_id, goal, parent_id=None):
    """
    Start a cell. With no parent this is a beginning; with one it is work
    expanding, and it goes through exactly the same path as a task a leader
    judged too large.
    """
    goal = rules.clean_goal(goal)

    if parent_id:
        return _create_within(actor_id, goal, parent_id)

    cell_id = events.new_id("cell")
    with events.unit_of_work():
        events.append("CellCreated", actor_id=actor_id, cell_id=cell_id,
                      subject_id=cell_id, goal=goal)
        member.join(actor_id, cell_id, actor_id, role=permission.LEADER)
    return model.get(cell_id)


def _create_within(actor_id, goal, parent_id):
    """
    The shortcut: name the work and expand it in one step, rather than making
    the person add a task and then split it. Same mechanism underneath.
    """
    # Deferred: the task domain builds on this one, so it cannot be imported
    # at module level. This is the only place the arrow points back.
    from ..task import service as task

    hierarchy.get(parent_id)
    permission.require_leader(actor_id, parent_id, "start a group inside this cell")
    rules.check_can_hold_children(
        hierarchy.scale(parent_id), governance_rules.threshold(governance_rules.CHILDREN)
    )

    with events.unit_of_work():
        mission = task.create(actor_id, parent_id, goal)
        return task.expand(actor_id, mission["id"])


def expand_into(actor_id, goal, parent_id, leader_id=None):
    """
    The primitive: a cell created because a piece of work outgrew one person.
    Only the task domain calls this, and only with a real task behind it.

    Whoever was holding the work leads the group that takes it on.
    """
    goal = rules.clean_goal(goal)
    hierarchy.get(parent_id)
    permission.require_leader(actor_id, parent_id, "expand work into its own cell")

    cell_id = events.new_id("cell")
    with events.unit_of_work():
        events.append("CellCreated", actor_id=actor_id, cell_id=cell_id,
                      subject_id=cell_id, goal=goal)
        hierarchy.place_under(actor_id, parent_id, cell_id)
        member.join(actor_id, cell_id, leader_id or actor_id, role=permission.LEADER)
    return model.get(cell_id)


def set_budget(actor_id, cell_id, amount, currency=None):
    """
    Commit to a spending limit, or drop the commitment by passing nothing.
    Optional everywhere: a cell that never sets one is never asked about it.
    """
    permission.require_leader(actor_id, cell_id, "set a budget")
    amount, currency = rules.clean_budget(amount, currency)
    events.append("BudgetSet", actor_id=actor_id, cell_id=cell_id, subject_id=cell_id,
                  amount=amount, currency=currency)
    return model.get(cell_id)


def refine_goal(actor_id, cell_id, goal):
    permission.require_leader(actor_id, cell_id, "change the goal")
    goal = rules.clean_goal(goal)
    events.append("GoalRefined", actor_id=actor_id, cell_id=cell_id,
                  subject_id=cell_id, goal=goal)
    return model.get(cell_id)
