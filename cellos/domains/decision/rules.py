"""
Decision: business rules.

Pure functions over plain values -- counts, strings, lists. Nothing here
touches the database, which is what makes the interesting parts of CellOS
(how a vote is read, when a leader is overruling rather than confirming)
testable without one.
"""

from ...kernel.errors import DomainError

# How a decision came to be accepted. Recorded permanently.
BY_VOTE = "vote"
BY_LEADER = "leader"
BY_OVERRIDE = "override"


def clean_question(question):
    question = (question or "").strip()
    if not question:
        raise DomainError("A decision needs a question.")
    return question


def clean_note(note, why):
    note = (note or "").strip()
    if not note:
        raise DomainError(why)
    return note


def build_options(question, texts, work):
    """
    A decision with no options is the common case of 'shall we do this', and
    becomes a single option that is the question itself.
    """
    texts = [t.strip() for t in (texts or []) if t and t.strip()]
    if not texts:
        texts = [question]
    work = work or {}
    return [
        {
            "text": text,
            "work": [w.strip() for w in work.get(str(i), []) if w and w.strip()],
        }
        for i, text in enumerate(texts)
    ]


def tally(counts):
    """
    What the cell thinks, read from the votes. A tie has no winner -- which is
    the whole point: a tied cell has not decided anything.
    """
    counts = {k: v for k, v in (counts or {}).items() if v}
    total = sum(counts.values())
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    tied = len(ranked) > 1 and ranked[0][1] == ranked[1][1]
    return {
        "counts": counts,
        "total": total,
        "winner": None if (tied or not ranked) else ranked[0][0],
        "tied": tied,
    }


def how_decided(result, option_id, note):
    """
    Whether accepting this option confirms the cell or overrules it.

    No votes, or a tied vote, means the cell did not decide -- a person did,
    and the record says so. Choosing against a clear winner is allowed, and
    refused without a reason.
    """
    winner = result["winner"]
    if winner and option_id != winner:
        if not (note or "").strip():
            raise DomainError("Deciding against the vote requires a reason. Nothing is hidden.")
        return BY_OVERRIDE
    if winner:
        return BY_VOTE
    return BY_LEADER


def everyone_voted(turnout, eligible):
    """Whether the cell has finished answering. Used to offer closing the vote."""
    return eligible > 0 and turnout >= eligible


def clean_outcome(outcome):
    return clean_note(outcome, "Say how it turned out.")


# --------------------------------------------------------------- diagnostics

# What each kind of unfinished question costs the cell. A question waiting on
# one person costs more than one the whole cell is still answering, because
# the cell can carry on talking while it waits for itself.
STUCK_COST = {
    "draft": 3,               # written down and never opened
    "open": 2,                # being talked through, which is work
    "voting": 4,              # the cell is answering
    "leader_resolution": 8,   # everyone has done their part but one person
}
UNRECORDED_COST = 2           # finished, and nobody wrote down how it went
SILENT_VOTE_COST = 3          # a vote hardly anyone has answered


def friction(state, question, turnout=0, eligible=0, tasks=0):
    """
    What this question is costing, and how to say so. Pure: give it the facts
    and it returns signals, with no idea who is asking or why.
    """
    out = []
    cost = STUCK_COST.get(state)
    if cost:
        out.append((cost, _waiting_words(state, question)))
    if state == "voting" and eligible and turnout * 2 < eligible:
        out.append((SILENT_VOTE_COST,
                    "%d of %d have not answered “%s”" % (eligible - turnout, eligible, question)))
    if state == "completed" and tasks:
        out.append((UNRECORDED_COST,
                    "“%s” is finished and nobody has written down how it went" % question))
    return out


def _waiting_words(state, question):
    return {
        "draft": "“%s” was written down and never opened" % question,
        "open": "“%s” is still being talked through" % question,
        "voting": "“%s” is waiting on the cell to answer" % question,
        "leader_resolution": "“%s” is waiting on a leader to settle it" % question,
    }[state]
