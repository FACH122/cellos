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


def clean_title(title):
    title = (title or "").strip()
    if not title:
        raise DomainError("A task needs a description.")
    return title


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
    """A date, or nothing. Optional everywhere, like evidence."""
    import datetime

    if due_on in (None, ""):
        return None
    try:
        return datetime.date.fromisoformat(str(due_on)[:10]).isoformat()
    except ValueError:
        raise DomainError("A deadline is a date, like 2026-12-05.")


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
