"""
The application layer.

The database stores facts. The domains derive meaning. This file decides what
one particular person, standing in one particular cell, should be able to see
and do right now -- and the interface renders exactly that.

Three consequences, all deliberate:

  Absent, not empty. A key missing from this payload is a section the
  interface cannot draw. A two-person cell is not sent an empty dashboard; it
  is not sent a dashboard at all.

  No decisions downstream. Every action the interface offers comes from
  `actions`, which the workflow engine produced. The UI never works out
  whether something is allowed.

  Responsibility, not permissions. What a person is shown about themselves is
  what they are expected to accomplish, not what they are permitted to click.
"""

from ..domains import permission
from ..domains.cell import service as cell_service
from ..domains.constraints import rules as constraint_rules, service as constraints
from ..domains.dashboard import service as dashboard
from ..domains.decision import service as decision_service
from ..domains.evidence import service as evidence
from ..domains.governance import rules as governance
from ..domains.health import service as health
from ..domains.hierarchy import service as hierarchy
from ..domains.member import model as member_model, service as member
from ..domains.progress import service as progress
from ..domains.responsibility import service as responsibility
from ..domains.task import rules as task_rules, service as task_service
from ..kernel import events as event_log


def home(user_id):
    """Where a person starts: their own cells, and nothing above them."""
    cells = []
    for cell_id in permission.home_cell_ids(user_id):
        c = hierarchy.get(cell_id)
        p = progress.of_cell(cell_id)
        cells.append({
            "id": c["id"],
            "goal": c["goal"],
            "people": hierarchy.scale(cell_id),
            "percent": p["percent"],
            "open_decisions": len(decision_service.open_in(cell_id)),
            "role": (permission.membership(user_id, cell_id) or {}).get("role"),
        })
    cells.sort(key=lambda c: -c["people"])
    return {"cells": cells}


def cell(user_id, cell_id):
    """
    One cell, whole. A small cell answers this with a goal, some people, some
    open questions and some tasks -- and nothing else is in the payload,
    because nothing else exists yet.

    A cell six levels down answers with exactly the same shape. There is no
    second kind of cell.
    """
    permission.require_sight(user_id, cell_id)
    c = hierarchy.get(cell_id)
    scale = hierarchy.scale(cell_id)
    caps = governance.capabilities(scale)
    visible = permission.visible_cell_ids(user_id)
    subtree = [i for i in hierarchy.subtree_ids(cell_id) if i in visible]

    standing = dict(permission.standing(user_id, cell_id))
    standing["can_admit"] = member.may_admit(user_id, cell_id)
    standing["can_create_child"] = cell_service.may_create_child(user_id, cell_id)

    view = {
        "cell": {"id": c["id"], "goal": c["goal"], "created_at": c["created_at"],
                 "depth": hierarchy.depth(cell_id)},
        "path": [p for p in hierarchy.path(cell_id) if p["id"] in visible],
        "scale": scale,
        "capabilities": sorted(caps),
        "governance": governance.model(scale),
        "you": standing,
        "members": member.members(cell_id),
        "responsibility": responsibility.for_cell(cell_id),
        "open_decisions": [
            decision_service.record(user_id, d["id"]) for d in decision_service.open_in(cell_id)
        ],
        "tasks": [_task(user_id, t, standing) for t in task_service.in_cells([cell_id])],
        "progress": progress.of_cell(cell_id),
        # How this cell is doing, and why. Derived on read like progress:
        # nobody types any of it in, and nothing about it is stored.
        "health": health.of_cell(cell_id),
    }

    # Optional everywhere. A cell that never committed to a budget or a date
    # is not sent an empty one -- it is not sent the key at all.
    committed = constraints.of_cell(cell_id)
    if committed:
        view["constraints"] = committed

    settled = decision_service.settled_in([cell_id], limit=20)
    view["settled_decisions"] = [
        decision_service.record(user_id, d["id"]) for d in settled if d["state"] != "knowledge"
    ]

    # --- what this cell grew out of ----------------------------------------

    # A cell that began as a piece of work carries that work as its mission,
    # with everything that was already attached to it. Nothing was copied.
    mission = responsibility.mission(cell_id)
    if mission and mission["from_cell"]["id"] in visible:
        view["mission"] = mission

    # --- everything below appears only when it would say something ----------

    # The shape of the work, drawn rather than tabulated. Sent only when there
    # is a shape: one circle is not a diagram, it is decoration.
    # Structure that exists is always shown, whatever the headcount: work can
    # expand into a cell at any size, so gating the picture on the twenty-
    # person threshold would hide a shape that is really there. The threshold
    # governs only whether starting a group is *offered*.
    children = [ch for ch in hierarchy.children(cell_id) if ch["id"] in visible]
    if children:
        view["structure"] = responsibility.structure(user_id, cell_id)
        _diagnose(view["structure"])

    elif governance.CHILDREN in caps and standing["can_create_child"]:
        view["structure"] = None

    if governance.ANALYTICS in caps:
        view["analytics"] = dashboard.metrics(cell_id)

    # What this person carries. Shown once the cell is bigger than the task
    # list above, which is already their answer in a small one.
    if standing["acts_here"] and scale >= governance.threshold(governance.VOTING):
        carried = responsibility.graph(user_id, cell_id)
        if carried and _worth_showing(carried):
            view["yours"] = carried

    known = dashboard.knowledge(subtree)
    if known:
        view["knowledge"] = known

    # Evidence is optional everywhere. If this part of the organisation has
    # never used it, the interface is not told it exists.
    if evidence.used_in(subtree):
        view["evidence_in_use"] = True

    return view


def _diagnose(node):
    """
    Hang a health reading on each node the map is about to draw. Only nodes
    actually being drawn are diagnosed, so opening a branch costs the reading
    for that branch and nothing else.
    """
    reading = health.of_cell(node["id"])
    node["health"] = reading["health"]
    node["attention_says"] = reading["attention"][:1]
    for child in node.get("children", []):
        _diagnose(child)


def _task(user_id, t, standing):
    """
    One piece of work, with what is expected of whom. Work that expanded
    reports the progress of the cell it became -- it did not stop existing, it
    grew, and its answer now comes from a group.
    """
    t["can_expand"] = standing["is_leader"] and not task_rules.check_can_expand(t["state"])
    if t["state"] == task_rules.EXPANDED and t.get("expanded_into"):
        grown = progress.of_cell(t["expanded_into"])
        t["progress"] = grown["percent"]
        t["expanded_people"] = hierarchy.scale(t["expanded_into"])
    # Whether this person may put a date or a cost on it -- asked of the same
    # rule the service enforces.
    t["can_time"] = standing["acts_here"] and t["state"] != task_rules.EXPANDED
    if t.get("due_on"):
        t["days_left"] = constraint_rules.days_between(t["due_on"], constraints.today())
    t["responsibility"] = responsibility.for_task(t)
    return t


def _worth_showing(carried):
    waiting = carried["waiting_on_you"]
    return bool(
        carried["yours"] or carried["blocked"]
        or waiting["votes"] or waiting["decisions"]
        or carried["you_are_waiting_on"]["work"]
    )


def task(user_id, task_id):
    """
    One piece of work, whole.

    Nothing here is new information -- it is the same task the cell page
    already lists, plus the things a list has no room for: why it exists, what
    has been offered in support of it, and who is expected to do what about
    it. A cell answers "what is going on"; this answers "what am I supposed to
    do about this one thing", which is a different question and deserves its
    own page rather than a row that grew a panel.
    """
    t = task_service.get(task_id)
    permission.require_sight(user_id, t["cell_id"])
    standing = dict(permission.standing(user_id, t["cell_id"]))
    cell = hierarchy.get(t["cell_id"])

    t = _task(user_id, t, standing)
    t["is_yours"] = t.get("owner_id") == user_id
    # Picking up work nobody holds needs no permission; taking it out of
    # somebody's hands is a leader's call. The same rule the service enforces.
    t["can_take"] = standing["acts_here"] and not task_rules.check_assignment(
        None, t.get("owner_id"), user_id, user_id, standing["is_leader"])
    t["can_report"] = standing["acts_here"] and t["state"] != task_rules.EXPANDED

    return {
        "task": t,
        "cell": {"id": cell["id"], "goal": cell["goal"]},
        "path": [p for p in hierarchy.path(t["cell_id"])
                 if p["id"] in permission.visible_cell_ids(user_id)],
        "you": standing,
        "because": responsibility._origin_decision(task_id),
        "evidence": evidence.supporting("task", task_id),
        "became": (
            {"id": t["expanded_into"], "goal": hierarchy.get(t["expanded_into"])["goal"],
             "people": hierarchy.scale(t["expanded_into"])}
            if t.get("expanded_into") else None),
    }


def decision(user_id, decision_id):
    """One question, whole, including what this person may do about it."""
    d = decision_service.get(decision_id)
    permission.require_sight(user_id, d["cell_id"])
    record = decision_service.record(user_id, decision_id)
    record["responsibility"] = responsibility.for_decision(d)
    return record


def history(user_id, cell_id, limit=200):
    """The permanent record, pruned to the reader's responsibility."""
    permission.require_sight(user_id, cell_id)
    visible = permission.visible_cell_ids(user_id)
    ids = [i for i in hierarchy.subtree_ids(cell_id) if i in visible]
    log = event_log.history(cell_ids=ids, limit=limit)

    names = member_model.names()
    for e in log:
        e["actor_name"] = names.get(e["actor_id"])
        e["subject_name"] = names.get(e["subject_id"])
    return log
