"""Task: business rules. Pure functions."""

from ...kernel.errors import DomainError

OPEN = "open"
ACTIVE = "active"
DONE = "done"
# Work that outgrew one person and expanded into a cell. It has not gone
# anywhere: it is that cell's mission, and its progress is that cell's
# progress.
EXPANDED = "expanded"

COMPLETE = 100
MAX_NOTE = 2000


def clean_title(title):
    title = (title or "").strip()
    if not title:
        raise DomainError("A task needs a description.")
    return title


def clean_note(body):
    """
    Something said while doing the work. Kept short on purpose: a note is what
    you would tell somebody who asked how it was going, not a report.
    """
    body = (body or "").strip()
    if not body:
        raise DomainError("A note needs something in it.")
    if len(body) > MAX_NOTE:
        raise DomainError("That is %d characters; a note stops at %d. "
                          "Anything longer is probably evidence."
                          % (len(body), MAX_NOTE))
    return body


def clean_progress(progress):
    try:
        progress = int(progress)
    except (TypeError, ValueError):
        raise DomainError("Progress is a number between 0 and 100.")
    if not 0 <= progress <= COMPLETE:
        raise DomainError("Progress is a number between 0 and 100.")
    return progress


def state_of(owner_id, progress, expanded_into=None):
    """
    Derived, never stored. Work that expanded is a cell's mission now, and
    reports that cell's progress. Otherwise: finished work is done, held work
    is active, and everything else waits for someone to pick it up.
    """
    if expanded_into:
        return EXPANDED
    if progress >= COMPLETE:
        return DONE
    return ACTIVE if owner_id else OPEN


def check_assignment(holder_name, holder_id, actor_id, owner_id, actor_leads):
    """
    Who may move a piece of work between hands.

    Picking up something nobody holds needs no permission -- that is the whole
    point of leaving work unowned, and asking to be allowed would defeat it.
    Everything else touches a commitment somebody has already made: handing
    work to a third person, taking it out of the hands it is in, or putting
    down something you are not holding.

    Those are a leader's call, or the holder's own. Without that rule a person
    can silently lose work they still believe is theirs, and the cell ends up
    with two people each certain they are doing it and one of them wrong --
    which is the exact failure the whole system exists to prevent.
    """
    if actor_leads:
        return None
    if owner_id and owner_id != actor_id:
        return "Only a leader can hand work to someone else."
    if holder_id and holder_id != actor_id:
        return "%s has that. Ask them, or ask a leader to move it." % (holder_name or "Somebody")
    return None


def check_can_expand(state):
    """
    Only work that is still one person's to do. Finished work has nothing left
    to give a group, and work that already expanded is already a cell.
    """
    if state == EXPANDED:
        return "That work is already a cell."
    if state == DONE:
        return "That work is finished."
    return None


def event_for(progress, currently_done):
    """
    Which fact a progress report records. Finishing and un-finishing are
    worth naming in the permanent record; moving from 40% to 60% is not.
    """
    if progress >= COMPLETE:
        return "TaskCompleted"
    if currently_done:
        return "TaskReopened"
    return "ProgressUpdated"


# --------------------------------------------------------------- diagnostics

UNTAKEN_COST = 5     # nobody has picked it up: the commonest reason work stops
UNSTARTED_COST = 3   # somebody holds it and has not begun
OVERLOAD_AT = 4      # holding more than this many unfinished things at once
OVERLOAD_COST = 4


def friction(state, title, progress, owner_name=None):
    """What one piece of work is costing the cell. Pure."""
    if state == OPEN:
        return [(UNTAKEN_COST, "nobody has taken “%s”" % title)]
    if state == ACTIVE and progress == 0:
        return [(UNSTARTED_COST,
                 "%s has “%s” and has not started it" % (owner_name or "somebody", title))]
    return []


def overload_friction(owner_name, holding):
    """
    One person holding too much is a cell problem, not a personal one: it is
    the shape of the work, and it shows up as the cell being unable to use
    everybody else.
    """
    if holding <= OVERLOAD_AT:
        return []
    return [(OVERLOAD_COST,
             "%s is holding %d things at once" % (owner_name or "somebody", holding))]


# ------------------------------------------------------------- constraints

MAX_COST = 1e12


def clean_deadline(due_on):
    """A date, or nothing. The rule lives with the other constraints."""
    from ..constraints.rules import clean_deadline as shared

    return shared(due_on)


def clean_cost(cost):
    if cost in (None, ""):
        return None
    try:
        cost = float(cost)
    except (TypeError, ValueError):
        raise DomainError("A cost is a number.")
    if cost < 0:
        raise DomainError("A cost cannot be negative.")
    if cost > MAX_COST:
        raise DomainError("That is not a cost, that is a typo.")
    return round(cost, 2)
