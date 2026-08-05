"""
Health: the final interpretation layer.

It owns no table, emits no event and is a source of truth for nothing. It
reads what the other domains already recorded, asks each of them what its own
objects are costing the cell, and composes the answer.

The dependency arrow points one way only:

    decision · task · evidence · member · progress  →  health  →  the interface

Nothing above this line knows health exists, which is what keeps it a
diagnostic rather than a target. A number the organisation is measured on
stops describing the organisation; this one is only ever an observation.
"""

from ...kernel import db
from .. import permission
from ..constraints import service as constraints
from ..decision import model as decision_model, rules as decision_rules
from ..decision.workflow import SETTLED, UNSETTLED
from ..evidence import model as evidence_model, rules as evidence_rules
from ..hierarchy import service as hierarchy
from ..member import model as member_model
from ..progress import service as progress
from ..task import model as task_model, rules as task_rules
from . import rules

# Events that mean the cell did something, rather than merely existing.
ACTIVITY = (
    "ProgressUpdated", "TaskCompleted", "TaskGenerated", "TaskAssigned",
    "VoteSubmitted", "DecisionAccepted", "KnowledgeRecorded", "RemarkAdded",
    "EvidenceAttached", "TaskExpanded",
)
WINDOW = 40  # events either side of "recently", measured in the cell's own history


def of_cell(cell_id, deep=True):
    """
    How this cell is doing, and why. `deep` includes everything beneath it,
    which is what a leader wants; a single cell's own reading is what its own
    members want.
    """
    scope = hierarchy.subtree_ids(cell_id) if deep else [cell_id]

    people = member_model.head_count(scope)
    outcomes = decision_model.count_by_state(scope).get("knowledge", 0)
    evidence_count = evidence_model.count_in(scope)

    potential = rules.potential(people, outcomes, evidence_count)
    signals = _signals(scope)
    friction = rules.friction(signals, ceiling=potential)
    capacity = rules.capacity(potential, friction)
    momentum = rules.momentum(*_activity(scope))
    band, score = rules.health(capacity, momentum)

    return {
        "potential": potential,
        "friction": friction,
        "capacity": capacity,
        "momentum": momentum,
        "health": band,
        "score": score,
        "progress": progress.of_cell(cell_id)["percent"],
        "attention": rules.attention(signals),
        "attention_count": len(signals),
    }


def attention_only(cell_id):
    """The human-facing half, for a row in a list. Cheaper than the whole reading."""
    signals = _signals(hierarchy.subtree_ids(cell_id))
    return rules.attention(signals, limit=2)


# ------------------------------------------------------------------ signals

def _signals(scope):
    """
    Ask every domain what its own objects are costing. None of them knows what
    the answer is used for, and none of them touches another's tables.
    """
    out = []
    out.extend(_from_questions(scope))
    out.extend(_from_work(scope))
    out.extend(_from_load(scope))
    # What the cell committed to. A budget it is overspending and a date it
    # has missed drag on it exactly like anything else -- choosing a
    # constraint deliberately does not earn it special treatment.
    if scope:
        out.extend(constraints.friction(scope[0], scope))
    return out


def _from_questions(scope):
    eligible = member_model.head_count(scope)
    signals = []

    for d in decision_model.in_cells(scope, states=UNSETTLED):
        turnout = sum(decision_model.vote_counts(d["id"]).values())
        signals += decision_rules.friction(d["state"], d["question"],
                                           turnout=turnout, eligible=eligible)

    for d in decision_model.in_cells(scope, states=SETTLED):
        turnout = sum(decision_model.vote_counts(d["id"]).values())
        if d["state"] != "knowledge":
            tasks = _task_count_of(d["id"])
            lifecycle = "completed" if tasks and _all_done(d["id"]) else d["state"]
            signals += decision_rules.friction(lifecycle, d["question"], tasks=tasks)
        signals += evidence_rules.friction(
            d["question"], turnout, len(evidence_model.many(_evidence_ids(d["id"]))))
    return signals


def _from_work(scope):
    signals = []
    for t in task_model.in_cells(scope, unfinished_only=True):
        signals += task_rules.friction(t["state"], t["title"], t["progress"], t["owner_name"])
    return signals


def _from_load(scope):
    """One person holding too much is a shape problem, not a personal failing."""
    if not scope:
        return []
    rows = db.rows(
        "SELECT u.name, count(*) AS holding FROM tasks t JOIN users u ON u.id = t.owner_id"
        " WHERE t.cell_id IN (%s) AND t.progress < 100"
        " AND t.id NOT IN (SELECT from_id FROM relationships WHERE kind = 'expands_into')"
        " GROUP BY t.owner_id" % db.marks(scope),
        scope,
    )
    signals = []
    for r in rows:
        signals += task_rules.overload_friction(r["name"], r["holding"])
    return signals


# ------------------------------------------------------------------ trend

def _activity(scope):
    """
    Two stretches of the cell's own history, most recent first. Counted in
    events rather than days, so a cell that works in bursts is judged on what
    it did, not on when the clock happened to be read.
    """
    if not scope:
        return 0, 0
    rows = db.rows(
        "SELECT id FROM events WHERE cell_id IN (%s) AND type IN (%s)"
        " ORDER BY id DESC LIMIT ?" % (db.marks(scope), db.marks(ACTIVITY)),
        list(scope) + list(ACTIVITY) + [WINDOW * 2],
    )
    return len(rows[:WINDOW]), len(rows[WINDOW:])


def trail(cell_id, points=12):
    """
    The curve, reconstructed rather than stored: how much this cell was doing
    across successive stretches of its own history. The log has always held
    this; nothing new is written to produce it.
    """
    scope = hierarchy.subtree_ids(cell_id)
    if not scope:
        return []
    ids = [r["id"] for r in db.rows(
        "SELECT id FROM events WHERE cell_id IN (%s) AND type IN (%s) ORDER BY id"
        % (db.marks(scope), db.marks(ACTIVITY)),
        list(scope) + list(ACTIVITY),
    )]
    if len(ids) < points:
        return []
    step = len(ids) // points
    return [len(ids[i * step:(i + 1) * step]) for i in range(points)]


# ------------------------------------------------------------------ helpers

def _task_count_of(decision_id):
    return db.value(
        "SELECT count(*) FROM relationships WHERE kind = 'produces' AND from_id = ?",
        (decision_id,), default=0)


def _all_done(decision_id):
    from ..decision import service as decision_service
    return task_model.all_done(decision_service.tasks_of(decision_id))


def _evidence_ids(decision_id):
    return [r["from_id"] for r in db.rows(
        "SELECT from_id FROM relationships WHERE kind = 'supports' AND to_id = ?",
        (decision_id,))]


def for_children(user_id, cell_id):
    """One reading per child cell, for a leader looking down."""
    visible = permission.visible_cell_ids(user_id)
    out = {}
    for child in hierarchy.children(cell_id):
        if child["id"] in visible:
            out[child["id"]] = of_cell(child["id"])
    return out
