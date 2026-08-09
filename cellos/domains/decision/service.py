"""
Decision: the public interface of this domain.

One object moves through the whole lifecycle. A decision is never converted
into a task or copied into a document; it acquires work, then an outcome, and
keeps its question, options, votes, evidence and discussion the entire time.

Every state change goes through `act()`, which is the only door into the
workflow engine. There is no `accept()` or `reject()` here that a caller could
reach past it.
"""

from ...kernel import events, relationships
from ...kernel.errors import Conflict, DomainError, NotAllowed, NotFound
from .. import permission
from ..governance import rules as governance_rules
from ..hierarchy import service as hierarchy
from ..member import model as member_model
from . import model, rules
from .workflow import DRAFT, SETTLED, UNSETTLED, flow, position

# A decision produces the work that carries it out. Typed rather than a
# column, so a task always knows which reasoning it came from.
PRODUCES = relationships.register(
    "produces", "decision", "task", single_head=True,
    description="An accepted decision and the work it generated.",
)

# The other direction in meaning, the same direction in shape: a question
# raised *about* work that already exists. "Should we still be doing this?"
# is not the reasoning a task came from -- it is a thing that happened to the
# task, and it belongs in that task's record with everything else.
#
# Not single_head: one piece of work can be argued over more than once, and
# the second argument does not erase the first.
CONCERNS = relationships.register(
    "concerns", "decision", "task",
    description="A question raised about a piece of work that already exists.",
)


def get(decision_id):
    d = model.get(decision_id)
    if d is None:
        raise NotFound("No such decision.")
    return d


# ------------------------------------------------------------------ context

def context(actor_id, decision):
    """
    Everything the workflow needs to know about who is asking and what the
    cell is like. Assembled once and handed to guards and `requires`.
    """
    cell_id = decision["cell_id"]
    scale = hierarchy.scale(cell_id)
    result = rules.tally(model.vote_counts(decision["id"]))
    ctx = dict(permission.standing(actor_id, cell_id))
    ctx.update({
        # No cell_id here: the engine names that argument itself, and a guard
        # that needed it could reach it through the decision.
        "decision_id": decision["id"],
        "scale": scale,
        "governance": governance_rules.model(scale),
        "result": result,
        "has_winner": bool(result["winner"]),
    })
    return ctx


def actions(actor_id, decision):
    """What this person could do to this decision right now."""
    return flow.available(decision["id"], context(actor_id, decision))


# ------------------------------------------------------------------ writing

def propose(actor_id, cell_id, question, detail="", option_texts=None, work=None,
            about=None):
    """
    Raise a question. `about` names a task the question concerns -- work that
    already exists and is now being argued over, rather than work this
    question might one day produce.
    """
    permission.require_member(actor_id, cell_id)
    question = rules.clean_question(question)
    options = [
        dict(o, id=events.new_id("opt"))
        for o in rules.build_options(question, option_texts, work)
    ]

    decision_id = events.new_id("dec")
    with events.unit_of_work():
        events.append(
            "DecisionCreated",
            actor_id=actor_id, cell_id=cell_id, subject_id=decision_id,
            question=question, detail=(detail or "").strip(),
            options=options, state=DRAFT,
        )
        if about:
            relationships.form(CONCERNS, "decision", decision_id, "task", about,
                               actor_id=actor_id, cell_id=cell_id)
    return get(decision_id)


def questions_about(task_id):
    """Every question raised about this piece of work, oldest first."""
    return model.many(relationships.tails(CONCERNS, task_id))


def work_concerned(decision_id):
    """The task this question is about, if it is about one at all."""
    from ..task import model as task_model

    about = relationships.heads(CONCERNS, decision_id)
    return task_model.get(about[0]) if about else None


def remark(actor_id, decision_id, body, option_id=None):
    """
    Say something. `option_id` names the answer it is about -- the case for
    it, or against it -- rather than filing every argument against the
    question and leaving a reader to work out which one it bears on.
    """
    d = get(decision_id)
    permission.require_member(actor_id, d["cell_id"])
    body = rules.clean_note(body, "Say something.")
    if d["state"] not in UNSETTLED:
        raise DomainError("This decision is settled.")
    if option_id and not model.option(option_id, decision_id):
        raise DomainError("That is not one of the options.")
    events.append("RemarkAdded", actor_id=actor_id, cell_id=d["cell_id"],
                  subject_id=decision_id, body=body, option_id=option_id)


def vote(actor_id, decision_id, option_id):
    d = get(decision_id)
    permission.require_member(actor_id, d["cell_id"])
    if d["state"] != "voting":
        raise DomainError("This decision is not open for votes.")
    if not model.option(option_id, decision_id):
        raise DomainError("That is not one of the options.")
    events.append("VoteSubmitted", actor_id=actor_id, cell_id=d["cell_id"],
                  subject_id=decision_id, option_id=option_id)
    return rules.tally(model.vote_counts(decision_id))


def act(actor_id, decision_id, step, **args):
    """
    Move a decision. The only entry to the workflow engine, and the only way
    a decision's state ever changes.
    """
    d = get(decision_id)
    permission.require_member(actor_id, d["cell_id"])

    if step not in flow.transitions:
        raise DomainError("There is no such step.")

    ctx = context(actor_id, d)
    ctx.update(args)
    if not flow.can(decision_id, step, ctx):
        raise _refusal(d, step)

    flow.fire(step, decision_id, actor_id=actor_id, cell_id=d["cell_id"], **ctx)
    return get(decision_id)


def _refusal(decision, step):
    """Say which kind of no this is: not yours, or no longer possible."""
    transition = flow.transitions[step]
    if decision["state"] in transition.sources:
        return NotAllowed("Only a leader of this cell can %s." % transition.label.lower())
    return Conflict(
        "This decision is %s now." % decision["state"].replace("_", " ")
    )


def advance_execution(actor_id, decision_id, step):
    """
    Fired by the task domain when work starts, finishes or reopens. Not a
    person's action, so it skips the `requires` check -- but still goes
    through the engine, which is what keeps the state honest.
    """
    d = model.get(decision_id)
    if d is None or d["state"] not in flow.transitions[step].sources:
        return
    try:
        flow.fire(step, decision_id, actor_id=actor_id, cell_id=d["cell_id"],
                  decision_id=decision_id)
    except Conflict:
        pass  # something else moved it first; the log is still consistent


# ------------------------------------------------------------------ reading

def open_in(cell_id):
    return model.in_cells([cell_id], states=UNSETTLED)


def settled_in(cell_ids, limit=None):
    return model.in_cells(cell_ids, states=SETTLED, limit=limit)


def tasks_of(decision_id):
    return relationships.heads(PRODUCES, decision_id)


def decision_of_task(task_id):
    return relationships.head_of(PRODUCES, task_id)


def record(actor_id, decision_id):
    """
    Everything that was true about a decision, assembled for reading: the
    question, the options, who voted for what, who took responsibility, the
    evidence, the work and the outcome.
    """
    from ..evidence import service as evidence
    from ..task import model as task_model

    d = get(decision_id)
    result = rules.tally(model.vote_counts(decision_id))
    voters = model.voters_by_option(decision_id)

    options = model.options_of(decision_id)
    for o in options:
        o["votes"] = result["counts"].get(o["id"], 0)
        o["voters"] = voters.get(o["id"], [])
        o["chosen"] = o["id"] == d["chosen_option"]
        # The case for this answer, and against it: said and offered about
        # this option rather than about the question in general.
        o["said"] = model.remarks_of(decision_id, o["id"])
        o["evidence"] = evidence.supporting("option", o["id"])

    names = member_model.names([d["created_by"], d["decided_by"]])
    d.update({
        "options": options,
        "turnout": result["total"],
        "tied": result["tied"],
        "remarks": model.remarks_of(decision_id),
        "evidence": evidence.supporting("decision", decision_id),
        "tasks": task_model.many(tasks_of(decision_id)),
        "created_by_name": names.get(d["created_by"]),
        "decided_by_name": names.get(d["decided_by"]),
        "position": position(d["state"]),
        "lifecycle_length": len(flow.states) - 1,
        # Which of the two jobs an open question is doing: proposing work, or
        # settling something about work that already exists. A reader should
        # not have to infer that from whether the options happen to carry any.
        "about": (lambda t: {"id": t["id"], "title": t["title"]} if t else None)(
            work_concerned(decision_id)),
        "your_vote": model.vote_of(decision_id, actor_id),
        "actions": actions(actor_id, d),
        # Casting a vote is not a state change -- the question stays in
        # voting -- so it is not a transition and never appeared in `actions`.
        # That left the commonest thing a member ever does as the one thing
        # the server did not offer, and a reader had to know it from
        # somewhere else. It says so here instead.
        "can_vote": rules.may_vote(d["state"], permission.is_member(actor_id, d["cell_id"])),
    })
    return d
