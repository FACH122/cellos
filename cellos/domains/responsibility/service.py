"""
Responsibility: who is expected to accomplish what.

This domain owns no table and emits no event. Every answer is derived from
facts other domains already recorded -- memberships, ownership, votes,
progress reports. Nothing here is configured, and there is no screen for
assigning a "responsible person", because the person holding the work already
is one.

It answers two shapes of question:

    for_cell / for_decision / for_task   who stands where on one thing
    graph(user_id)                       everything one person carries
"""

from ...kernel import db
from .. import permission
from ..decision import model as decision_model
from ..decision.workflow import LEADER_RESOLUTION, UNSETTLED, VOTING
from ..hierarchy import service as hierarchy
from ..member import model as member_model
from ..progress import service as progress
from ..task import model as task_model, service as task_service
from . import rules

LEADER, RESPONSIBLE, VERIFIER, PARTICIPANT = (
    rules.LEADER, rules.RESPONSIBLE, rules.VERIFIER, rules.PARTICIPANT,
)


# ------------------------------------------------------------ one thing

def _leaders_of(cell_id):
    return [m["id"] for m in member_model.members_of(cell_id) if m["role"] == "leader"]


def _leaders_above(cell_id):
    above = []
    for ancestor in hierarchy.ancestor_ids(cell_id):
        above.extend(_leaders_of(ancestor))
    return above


def for_cell(cell_id):
    """
    A cell is accountable to whoever leads it, and verified by whoever leads
    the cell above it. A root cell verifies itself, because there is nobody
    above -- which is the honest answer, not a gap.
    """
    leaders = _leaders_of(cell_id)
    above = _leaders_above(cell_id)
    return _shape(cell_id, {
        LEADER: leaders,
        RESPONSIBLE: leaders,
        VERIFIER: [v for v in [rules.verifier_of(None, leaders, above)] if v],
        PARTICIPANT: [m["id"] for m in member_model.members_of(cell_id)],
    })


def for_task(task):
    """
    Whoever holds the work is responsible for it. Work that expanded is
    answered for by the cell it became, so responsibility moves with it.
    """
    cell_id = task["cell_id"]
    leaders = _leaders_of(cell_id)
    above = _leaders_above(cell_id)

    if task.get("expanded_into"):
        responsible = _leaders_of(task["expanded_into"])
    else:
        responsible = [task["owner_id"]] if task["owner_id"] else []

    doer = responsible[0] if responsible else None
    reported = [
        r["actor_id"] for r in db.rows(
            "SELECT DISTINCT actor_id FROM events WHERE subject_id = ?"
            " AND type IN ('ProgressUpdated','TaskCompleted','TaskReopened')"
            " AND actor_id IS NOT NULL",
            (task["id"],),
        )
    ]
    return _shape(task["id"], {
        LEADER: leaders,
        RESPONSIBLE: responsible,
        VERIFIER: [v for v in [rules.verifier_of(doer, leaders, above)] if v],
        PARTICIPANT: sorted(set(reported) | set(responsible)),
    })


def for_decision(decision):
    """
    Before it is settled, the person who raised it carries it. After, the
    person who accepted it does -- that is what taking responsibility means.
    """
    cell_id = decision["cell_id"]
    leaders = _leaders_of(cell_id)
    above = _leaders_above(cell_id)
    carrier = decision["decided_by"] or decision["created_by"]

    voters = [
        r["user_id"] for r in db.rows(
            "SELECT DISTINCT user_id FROM votes WHERE decision_id = ?", (decision["id"],)
        )
    ]
    spoke = [
        r["author_id"] for r in db.rows(
            "SELECT DISTINCT author_id FROM remarks WHERE decision_id = ?"
            " AND author_id IS NOT NULL", (decision["id"],)
        )
    ]
    return _shape(decision["id"], {
        LEADER: leaders,
        RESPONSIBLE: [carrier] if carrier else [],
        VERIFIER: [v for v in [rules.verifier_of(carrier, leaders, above)] if v],
        PARTICIPANT: sorted(set(voters) | set(spoke)),
    })


def _shape(subject_id, roles):
    names = member_model.names({u for holders in roles.values() for u in holders})
    return {
        "subject_id": subject_id,
        "roles": {
            role: [{"id": u, "name": names.get(u)} for u in holders]
            for role, holders in roles.items()
        },
    }


def standing(user_id, roles_payload):
    """Which roles this person holds on a thing already shaped by `_shape`."""
    return sorted(
        role for role, holders in roles_payload["roles"].items()
        if any(h["id"] == user_id for h in holders)
    )


# ------------------------------------------------------------ one person

def graph(user_id, cell_id):
    """
    Everything one person carries, within one cell and everything beneath it.

    Five questions, in the order somebody actually asks them: what is mine,
    what is waiting on me, what am I waiting on, what is stuck, what is
    moving. Every one is a query over facts, not a stored list.
    """
    visible = permission.visible_cell_ids(user_id)
    # Nothing about a cell above you, not even a filtered version of it. If
    # you cannot see the cell, there is no answer here at all.
    if cell_id not in visible:
        return None
    subtree = [c for c in hierarchy.subtree_ids(cell_id) if c in visible]
    if not subtree:
        return None

    led = [c for c in subtree if permission.is_leader(user_id, c)]
    mine = task_model.in_cells(subtree, owner_id=user_id, unfinished_only=True)
    open_decisions = decision_model.in_cells(subtree, states=UNSETTLED)
    voted_on = set(decision_model.ids_voted_on_by(user_id, subtree))

    awaiting_vote = [
        d for d in open_decisions
        if d["state"] == VOTING and d["id"] not in voted_on
    ]
    awaiting_resolution = [
        d for d in open_decisions
        if d["state"] == LEADER_RESOLUTION and permission.is_leader(user_id, d["cell_id"])
    ]
    others_work = [
        t for t in task_model.in_cells(led, unfinished_only=True)
        if t["owner_id"] and t["owner_id"] != user_id
    ]
    unclaimed = [
        t for t in task_model.in_cells(subtree, unfinished_only=True) if not t["owner_id"]
    ]

    return {
        "cells_led": [
            {"id": c, "goal": hierarchy.get(c)["goal"],
             "people": hierarchy.scale(c), "percent": progress.of_cell(c)["percent"]}
            for c in led
        ],
        "yours": _light(mine),
        "progress": progress.of_tasks(mine),
        # Somebody cannot move until you do.
        "waiting_on_you": {
            "votes": [_question(d) for d in awaiting_vote],
            "decisions": [_question(d) for d in awaiting_resolution],
            "not_started": _light([t for t in mine if t["progress"] == 0]),
        },
        # You cannot finish until somebody else does.
        "you_are_waiting_on": {
            "work": _light(others_work),
            "questions": [
                _question(d) for d in open_decisions
                if d["id"] in voted_on and d["state"] != VOTING
            ],
        },
        "blocked": _light(unclaimed),
        "moving": _light([t for t in mine if 0 < t["progress"] < 100]),
    }


def _light(tasks):
    return [
        {
            "id": t["id"], "title": t["title"], "cell_id": t["cell_id"],
            "progress": t["progress"], "state": t["state"],
            "owner_id": t["owner_id"], "owner_name": t["owner_name"],
            "expanded_into": t.get("expanded_into"),
        }
        for t in tasks
    ]


def _question(decision):
    return {
        "id": decision["id"], "question": decision["question"],
        "cell_id": decision["cell_id"], "state": decision["state"],
    }


def descendants(user_id, cell_id):
    """
    What a leader is responsible for below them: one row per cell they hold,
    with what is stuck in it. Never anything above -- there is no view upward
    in CellOS.
    """
    visible = permission.visible_cell_ids(user_id)
    rows = []
    for child in hierarchy.children(cell_id):
        if child["id"] not in visible:
            continue
        below = hierarchy.subtree_ids(child["id"])
        p = progress.of_cell(child["id"])
        leaders = _leaders_of(child["id"])
        names = member_model.names(leaders)
        rows.append({
            "id": child["id"],
            "goal": child["goal"],
            "people": hierarchy.scale(child["id"]),
            "percent": p["percent"],
            "task_count": p["task_count"],
            "remaining": p["remaining"],
            "led_by": [names.get(u) for u in leaders][:2],
            "open_decisions": len(decision_model.in_cells(below, states=UNSETTLED)),
            "unowned": task_model.unowned_count(below),
            "stalled": task_model.stalled_count(below),
        })
    return rows


def node(user_id, cell_id):
    """
    One cell as the map draws it: how far along, whether anything in it needs
    attention, how many cells sit inside it, and *why it exists* -- the
    question whose answer grew into it.

    There is no depth argument anywhere in this domain. The map asks for a
    cell's children when somebody expands it, so recursion is bounded by
    curiosity rather than by a constant.
    """
    visible = permission.visible_cell_ids(user_id)
    if cell_id not in visible:
        return None

    below = hierarchy.subtree_ids(cell_id)
    p = progress.of_cell(cell_id)
    kids = [c for c in hierarchy.child_ids(cell_id) if c in visible]
    unowned = task_model.unowned_count(below)
    stalled = task_model.stalled_count(below)
    waiting = len(decision_model.in_cells(below, states=UNSETTLED))

    return {
        "id": cell_id,
        "goal": hierarchy.get(cell_id)["goal"],
        "people": hierarchy.scale(cell_id),
        "percent": p["percent"],
        "remaining": p["remaining"],
        "unowned": unowned,
        "stalled": stalled,
        "questions": waiting,
        # One flag, so the drawing encodes two things and not five.
        "attention": bool(unowned or stalled or waiting),
        "because": _because(cell_id),
        # How many cells are inside, so a collapsed node can say what it holds
        # without anybody having to compute what is in there.
        "child_count": len(kids),
    }


def children_of(user_id, cell_id):
    """The cells directly inside this one. Fetched when somebody expands it."""
    visible = permission.visible_cell_ids(user_id)
    return [n for n in (node(user_id, c) for c in hierarchy.child_ids(cell_id)
                        if c in visible) if n]


def structure(user_id, cell_id):
    """
    What the map starts from: this cell and the ring immediately inside it.
    Everything deeper arrives when it is asked for.
    """
    root = node(user_id, cell_id)
    if root is None:
        return None
    root["children"] = children_of(user_id, cell_id)
    return root


def _because(cell_id):
    """
    Why this cell exists: the work it grew out of, and the question that
    produced that work. A root cell simply began.
    """
    origin = task_service.mission_of(cell_id)
    if origin is None:
        return None
    decision_id = _decision_id_of(origin["id"])
    d = decision_model.get(decision_id) if decision_id else None
    return {
        "work": origin["title"],
        "question": d["question"] if d else None,
    }


def _decision_id_of(task_id):
    from ..decision import service as decision_service

    return decision_service.decision_of_task(task_id)


def mission(cell_id):
    """
    The work this cell grew out of, if it grew out of any -- with everything
    that was already attached to it. Nothing is copied here; this is the same
    task, read from where it always was.
    """
    from ..evidence import service as evidence

    origin = task_service.mission_of(cell_id)
    if origin is None:
        return None

    came_from = hierarchy.get(origin["cell_id"])
    return {
        "task_id": origin["id"],
        "title": origin["title"],
        "created_at": origin["created_at"],
        "from_cell": {"id": came_from["id"], "goal": came_from["goal"]},
        "decision": _origin_decision(origin["id"]),
        "evidence": evidence.supporting("task", origin["id"]),
        "responsibility": for_task(origin),
    }


def _origin_decision(task_id):
    from ..decision import service as decision_service

    decision_id = decision_service.decision_of_task(task_id)
    if not decision_id:
        return None
    d = decision_model.get(decision_id)
    return None if d is None else {
        "id": d["id"], "question": d["question"], "cell_id": d["cell_id"],
    }
