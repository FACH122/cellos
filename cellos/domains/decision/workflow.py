"""
The decision lifecycle, declared.

    draft -> open -> voting -> leader resolution -> accepted
                                                      |
                                    executing -> completed -> knowledge

Every arrow is a transition here. Nothing outside this file may move a
decision, and no service writes `state` -- the workflow engine appends the
event and the state projector applies it, under one lock.

Which arrows a cell actually uses is not configured. `requires` reads the
cell's governance, which is a function of its size: alone you go straight from
open to accepted, at five people the cell votes and the count settles it, at
twenty a leader signs the count and may overrule it in writing.

The last four transitions are fired by the task domain rather than a person --
work starting is what makes a decision "executing", and work finishing is what
makes it "completed". Nobody clicks those.
"""

from ...kernel import workflow as engine
from ...kernel.errors import DomainError
from ..governance import rules as governance
from . import model, rules

DRAFT = "draft"
OPEN = "open"
VOTING = "voting"
LEADER_RESOLUTION = "leader_resolution"
ACCEPTED = "accepted"
EXECUTING = "executing"
COMPLETED = "completed"
KNOWLEDGE = "knowledge"
REJECTED = "rejected"

# In lifecycle order. `rejected` is terminal and sits outside the run.
LIFECYCLE = (DRAFT, OPEN, VOTING, LEADER_RESOLUTION, ACCEPTED, EXECUTING, COMPLETED, KNOWLEDGE)
STATES = LIFECYCLE + (REJECTED,)

# Still waiting on somebody.
UNSETTLED = (DRAFT, OPEN, VOTING, LEADER_RESOLUTION)
# Settled, one way or another.
SETTLED = (ACCEPTED, EXECUTING, COMPLETED, KNOWLEDGE, REJECTED)

flow = engine.Workflow(
    name="decision",
    states=STATES,
    initial=DRAFT,
    read_state=model.state_of,
)


# ------------------------------------------------------------------ guards

def _leader(ctx):
    return bool(ctx.get("is_leader"))


def _member(ctx):
    return bool(ctx.get("acts_here"))


def _cell_votes(ctx):
    return ctx.get("governance") in (governance.VOTE_DECIDES, governance.LEADER_CONFIRMS_VOTE)


def _needs_a_leader_to_close(ctx):
    """A big cell hands the count to someone accountable. So does a tied one."""
    return ctx.get("governance") == governance.LEADER_CONFIRMS_VOTE or not ctx.get("has_winner")


def _note_guard(why):
    def guard(ctx, _current):
        return {"note": rules.clean_note(ctx.get("note"), why)}

    return guard


def _count(ctx):
    """
    Re-read the votes inside the transition rather than trusting the tally the
    caller saw. Guards run under the write lock, so this is the count at the
    moment the decision actually moves.
    """
    return rules.tally(model.vote_counts(ctx["decision_id"]))


def _accept_by_vote(ctx, _current):
    result = _count(ctx)
    if not result["winner"]:
        raise DomainError("The cell is tied. This needs someone to decide it.")
    return {"option_id": result["winner"], "how": rules.BY_VOTE,
            "note": rules.vote_reason(result)}


def _accept_by_leader(ctx, _current):
    """A leader taking responsibility, whether or not the cell agrees."""
    option_id = ctx.get("option_id")
    if not model.option(option_id, ctx["decision_id"]):
        raise DomainError("That is not one of the options.")
    how = rules.how_decided(_count(ctx), option_id, ctx.get("note"))
    return {"option_id": option_id, "how": how, "note": (ctx.get("note") or "").strip()}


def _override_record(ctx, _current):
    """
    An override is a fact about accountability, so it is recorded as its own
    event rather than only as a field. Nothing is hidden.
    """
    option_id = ctx.get("option_id")
    result = _count(ctx)
    if result["winner"] and option_id != result["winner"]:
        return [(
            "LeaderOverride",
            {
                "option_id": option_id,
                "against": result["winner"],
                "note": (ctx.get("note") or "").strip(),
                "turnout": result["total"],
            },
        )]
    return []


def _record_knowledge(ctx, _current):
    return {
        "outcome": rules.clean_outcome(ctx.get("outcome")),
        "lesson": (ctx.get("lesson") or "").strip(),
    }


# ------------------------------------------------------------- transitions

(
    flow
    .transition(
        "open", DRAFT, OPEN, "DecisionOpened",
        requires=_member, label="Open it up",
    )
    .transition(
        "put_to_cell", (DRAFT, OPEN), VOTING, "VotingOpened",
        requires=lambda ctx: _member(ctx) and _cell_votes(ctx),
        label="Put it to the cell",
    )
    .transition(
        # Only offered when there is somebody else to hand it to. Alone, you
        # do not ask yourself for a resolution -- you decide.
        "ask_leader", (DRAFT, OPEN), LEADER_RESOLUTION, "ResolutionRequested",
        requires=lambda ctx: _member(ctx) and not _cell_votes(ctx) and not _leader(ctx),
        label="Ready to decide",
    )
    .transition(
        "accept_by_vote", VOTING, ACCEPTED, "DecisionAccepted",
        guard=_accept_by_vote,
        requires=lambda ctx: _member(ctx) and not _needs_a_leader_to_close(ctx),
        label="Close the vote",
    )
    .transition(
        "send_to_leader", VOTING, LEADER_RESOLUTION, "ResolutionRequested",
        requires=lambda ctx: _member(ctx) and _needs_a_leader_to_close(ctx),
        label="Close the vote",
    )
    .transition(
        "resolve", (DRAFT, OPEN, VOTING, LEADER_RESOLUTION), ACCEPTED, "DecisionAccepted",
        guard=_accept_by_leader, extra=_override_record,
        requires=_leader, label="Decide",
        asks=(
            {"name": "option_id", "kind": "option", "label": "Which one?", "required": True},
            {"name": "note", "kind": "text", "label": "Why",
             "hint": "The reasoning that will outlive this. Required if you go against the vote."},
        ),
    )
    .transition(
        "return", (VOTING, LEADER_RESOLUTION), OPEN, "DecisionReturned",
        guard=_note_guard("Say what needs reworking."),
        requires=_leader, label="Send back",
        asks=({"name": "note", "kind": "line", "label": "What needs reworking?",
               "required": True},),
    )
    .transition(
        "reject", (DRAFT, OPEN, VOTING, LEADER_RESOLUTION), REJECTED, "DecisionRejected",
        guard=_note_guard("Say why."),
        requires=_leader, label="Decline",
        asks=({"name": "note", "kind": "line", "label": "Say why", "required": True},),
    )
    # Fired by the task domain, never offered to a person.
    .transition("begin_execution", ACCEPTED, EXECUTING, "ExecutionStarted",
                requires=lambda ctx: False)
    .transition("finish_execution", EXECUTING, COMPLETED, "ExecutionCompleted",
                requires=lambda ctx: False)
    .transition("resume_execution", COMPLETED, EXECUTING, "ExecutionResumed",
                requires=lambda ctx: False)
    .transition(
        "record", (ACCEPTED, EXECUTING, COMPLETED), KNOWLEDGE, "KnowledgeRecorded",
        guard=_record_knowledge,
        requires=_member, label="Record how it turned out",
        asks=(
            {"name": "outcome", "kind": "text", "label": "How did it turn out?",
             "required": True},
            {"name": "lesson", "kind": "text",
             "label": "What would you tell someone facing this again?"},
        ),
    )
)


def position(state):
    """Where in the run this sits, for display. Declined sits outside it."""
    if state == REJECTED:
        return None
    return flow.position(state)
