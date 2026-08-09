"""
Task: the public interface of this domain.

Accepted decisions become work without anyone retyping them, and the work
keeps a typed link back to the reasoning that produced it.

Work that outgrows one person does not get replaced by something else. It
**expands**: the task becomes the mission of a new cell, and everything
already attached to it -- who proposed it, what evidence was offered, what was
said, who was holding it, how far it had got -- stays attached, because
nothing is copied and nothing is recreated. The cell is that task, grown.

This domain does not write to the decisions table. When work starts, finishes
or expands it asks the decision domain to move its own object through its own
workflow.
"""

from ...kernel import events, relationships
from ...kernel.errors import DomainError, NotAllowed, NotFound
from .. import permission
from ..cell import service as cell_service
from ..decision import service as decision
from ..member import model as member_model
from . import model, rules

OPEN, ACTIVE, DONE, EXPANDED = rules.OPEN, rules.ACTIVE, rules.DONE, rules.EXPANDED

# Work and the cell it grew into. Typed rather than a column, so the task
# keeps its history and the cell keeps its origin.
EXPANDS_INTO = relationships.register(
    "expands_into", "task", "cell", single_head=True,
    description="Work that outgrew one person, and the cell whose mission it became.",
)


def get(task_id):
    task = model.get(task_id)
    if task is None:
        raise NotFound("No such task.")
    return task


def in_cells(cell_ids, **kw):
    return model.in_cells(cell_ids, **kw)


def create(actor_id, cell_id, title, owner_id=None):
    permission.require_member(actor_id, cell_id)
    title = rules.clean_title(title)
    if owner_id and not member_model.membership(owner_id, cell_id):
        raise DomainError("That person is not in this cell.")

    task_id = events.new_id("task")
    events.append("TaskCreated", actor_id=actor_id, cell_id=cell_id, subject_id=task_id,
                  title=title, owner_id=owner_id)
    return get(task_id)


def assign(actor_id, task_id, owner_id):
    """Taking work, or handing it over. Either way the cell can see who holds it."""
    task = get(task_id)
    permission.require_member(actor_id, task["cell_id"])
    if owner_id and not member_model.membership(owner_id, task["cell_id"]):
        raise DomainError("That person is not in this cell.")

    holder = task.get("owner_id")
    refusal = rules.check_assignment(
        member_model.names([holder]).get(holder), holder, actor_id, owner_id,
        permission.is_leader(actor_id, task["cell_id"]))
    if refusal:
        raise NotAllowed(refusal)

    events.append("TaskAssigned", actor_id=actor_id, cell_id=task["cell_id"],
                  subject_id=task_id, owner_id=owner_id)
    return get(task_id)


def note(actor_id, task_id, body):
    """
    Say something while doing the work.

    A decision has remarks -- that is a cell arguing before it settles
    something. Work has notes, which is a different act and belongs to whoever
    is holding it: what was found, what is in the way, what was tried and did
    not work. It is the difference between a task page that reports a number
    and one somebody actually works on.

    Anyone who can act in the cell may leave one. Being blocked by somebody
    else's task is exactly when you most need to say so.
    """
    task = get(task_id)
    permission.require_member(actor_id, task["cell_id"])
    body = rules.clean_note(body)
    events.append("TaskNoted", actor_id=actor_id, cell_id=task["cell_id"],
                  subject_id=task_id, body=body)
    return model.notes_of(task_id)


def report_progress(actor_id, task_id, progress):
    """
    Members report their own work. Nobody updates a number on their behalf,
    which is why cell progress can be trusted as it rolls upward.
    """
    progress = rules.clean_progress(progress)
    task = get(task_id)
    _require_hands_on(actor_id, task)

    event_type = rules.event_for(progress, task["state"] == DONE)
    payload = {} if event_type == "TaskCompleted" else {"progress": progress}
    events.append(event_type, actor_id=actor_id, cell_id=task["cell_id"],
                  subject_id=task_id, **payload)
    return get(task_id)


def set_deadline(actor_id, task_id, due_on):
    """When this is wanted by, or nothing. Anyone with hands on it may say."""
    task = get(task_id)
    _require_hands_on(actor_id, task)
    due_on = rules.clean_deadline(due_on)
    events.append("DeadlineSet", actor_id=actor_id, cell_id=task["cell_id"],
                  subject_id=task_id, due_on=due_on)
    return get(task_id)


def record_cost(actor_id, task_id, cost):
    """
    What this work cost. It rolls up into the cell's spend the same way
    progress rolls up -- nobody maintains a running total anywhere.
    """
    task = get(task_id)
    _require_hands_on(actor_id, task)
    cost = rules.clean_cost(cost)
    events.append("CostRecorded", actor_id=actor_id, cell_id=task["cell_id"],
                  subject_id=task_id, cost=cost)
    return get(task_id)


# ---------------------------------------------------------------- expansion

def may_expand(actor_id, task_id):
    """Asked ahead of time, so the interface never offers what would be refused."""
    task = model.get(task_id)
    if task is None or rules.check_can_expand(task["state"]):
        return False
    return permission.allows(permission.require_leader, actor_id, task["cell_id"])


def expand(actor_id, task_id, goal=None):
    """
    This is bigger than one person.

    The task becomes the mission of a new cell. It is not deleted, replaced or
    duplicated -- the decision that produced it still points at it, its
    evidence is still its evidence, and its history is still its history. What
    changes is who is doing it: a group, whose progress now answers for it.

    Whoever was holding the work leads the group that takes it on.
    """
    task = get(task_id)
    permission.require_leader(actor_id, task["cell_id"], "expand work into its own cell")

    refusal = rules.check_can_expand(task["state"])
    if refusal:
        raise DomainError(refusal)

    goal = rules.clean_title(goal or task["title"])

    with events.unit_of_work():
        grown = cell_service.expand_into(
            actor_id, goal, task["cell_id"], leader_id=task["owner_id"],
        )
        events.append("TaskExpanded", actor_id=actor_id, cell_id=task["cell_id"],
                      subject_id=task_id, into=grown["id"], goal=goal)
        relationships.form(EXPANDS_INTO, "task", task_id, "cell", grown["id"],
                           actor_id=actor_id, cell_id=task["cell_id"])
    return grown


def expanded_into(task_id):
    """The cell this work grew into, if it did."""
    grown = relationships.heads(EXPANDS_INTO, task_id)
    return grown[0] if grown else None


def mission_of(cell_id):
    """
    The task this cell is. A cell that began as work has a mission; a cell
    somebody started from nothing does not, and its goal is its own.
    """
    origin = relationships.tails(EXPANDS_INTO, cell_id)
    return model.get(origin[0]) if origin else None


def _require_hands_on(actor_id, task):
    if task["state"] == EXPANDED:
        raise DomainError(
            "That work is a cell now. Its progress comes from the people in it."
        )
    if task["owner_id"] == actor_id:
        return
    if task["owner_id"] is None:
        permission.require_member(actor_id, task["cell_id"])
        return
    permission.require_leader(actor_id, task["cell_id"], "change someone else's progress")


# ------------------------------------------------- a decision becoming work

@events.reactor("DecisionAccepted")
def _generate_work(event):
    """
    The moment a decision is accepted it stops being a proposal and starts
    being work. Nobody transcribes it.
    """
    import json

    from ..decision import model as decision_model

    option_id = event["payload"].get("option_id")
    option = decision_model.option(option_id) if option_id else None
    if option is None:
        return

    titles = json.loads(option["work"]) or [option["text"]]
    cell_id = event["cell_id"]
    decision_id = event["subject_id"]

    # A cell of one has nobody to give work to but the person standing there.
    people = member_model.members_of(cell_id)
    owner_id = people[0]["id"] if len(people) == 1 else None

    with events.unit_of_work():
        for title in titles:
            task_id = events.new_id("task")
            events.append("TaskGenerated", actor_id=event["actor_id"], cell_id=cell_id,
                          subject_id=task_id, title=title, owner_id=owner_id,
                          decision_id=decision_id)
            relationships.form(decision.PRODUCES, "decision", decision_id, "task", task_id,
                               actor_id=event["actor_id"], cell_id=cell_id)


# ------------------------------------- work moving its decision along with it

@events.reactor("TaskGenerated")
def _work_began(event):
    decision_id = decision.decision_of_task(event["subject_id"])
    if decision_id:
        decision.advance_execution(event["actor_id"], decision_id, "begin_execution")


@events.reactor("TaskCompleted", "TaskExpanded")
def _work_finished(event):
    """
    Expanding counts as settled here for the same reason completing does: this
    cell is no longer waiting on it, the cell it became is.
    """
    decision_id = decision.decision_of_task(event["subject_id"])
    if decision_id and model.all_done(decision.tasks_of(decision_id)):
        decision.advance_execution(event["actor_id"], decision_id, "finish_execution")


@events.reactor("TaskReopened")
def _work_resumed(event):
    decision_id = decision.decision_of_task(event["subject_id"])
    if decision_id:
        decision.advance_execution(event["actor_id"], decision_id, "resume_execution")
