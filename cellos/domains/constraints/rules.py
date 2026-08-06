"""
Constraints: business rules. Pure functions.

A constraint is something a cell chose to hold itself to -- a budget it will
not exceed, a date work is wanted by. Both are optional everywhere and
required nowhere, exactly like evidence: two friends planning a weekend owe
nobody a spending limit.

Neither is a target the software enforces. CellOS does not stop anyone
spending or block a late task. It notices, and says so, and the organisation
decides what to do -- which is the whole design principle of the health layer
these feed into.
"""

TIGHT = 0.85       # budget this far spent is worth mentioning
SOON_DAYS = 3      # a deadline this close counts as imminent

OVERDUE_COST = 7   # the date has passed and the work is not done
SOON_COST = 3      # close, and not started
OVER_BUDGET_COST = 8
CONTRADICTION_COST = 6   # something inside is due later than the whole
TIGHT_BUDGET_COST = 4


def clean_deadline(due_on):
    """
    A date, or nothing. Optional on a cell and on a task alike -- committing
    to one is a choice, and clearing it is a different thing from having
    missed it.
    """
    import datetime

    from ...kernel.errors import DomainError

    if due_on in (None, ""):
        return None
    try:
        return datetime.date.fromisoformat(str(due_on)[:10]).isoformat()
    except ValueError:
        raise DomainError("A deadline is a date, like 2026-12-05.")


def cell_deadline_friction(goal, due_on, today, percent):
    """
    The cell's own date. Work still outstanding past the day it was wanted is
    worth saying plainly; a cell that finished is not late whatever the
    calendar says.
    """
    if percent >= 100:
        return []
    left = days_between(due_on, today)
    if left < 0:
        return [(OVERDUE_COST + 2, "this cell was due %s and is at %d%%" % (_ago(-left), percent))]
    if left <= SOON_DAYS:
        return [(SOON_COST, "this cell is due %s and is at %d%%" % (_within(left), percent))]
    return []


def inconsistent_deadline(what, name, inner_due, outer_due):
    """
    Something inside a cell is due after the cell itself. Not a rule anybody
    broke -- CellOS enforces nothing -- but a contradiction the two dates make
    that nobody may have noticed, and exactly the kind of thing the system can
    see and a person cannot.
    """
    if not inner_due or not outer_due or inner_due <= outer_due:
        return []
    return [(CONTRADICTION_COST,
             "%s “%s” is due after this cell is" % (what, name))]


OVER_ALLOCATED_COST = 7   # the cells inside have promised more than there is


def over_allocation(allocated, budget, currency, children_with_budgets):
    """
    The cells inside a cell have committed to more money than the cell itself
    has.

    Every cell sets its own budget, which is right -- a group that cannot say
    what it is willing to spend is not really running anything. But a budget
    set with no reference to the one above it is a wish, and nothing was
    noticing. A parent with 100,000 and three children holding 60,000 each is
    not a cell with a budget; it is a cell with a problem nobody has said out
    loud yet.

    Said, not enforced. CellOS does not refuse the third child's budget any
    more than it refuses a late task -- the contradiction is surfaced and the
    organisation decides what to do about it.
    """
    if not budget or not allocated or allocated <= budget:
        return []
    return [(OVER_ALLOCATED_COST,
             "the %d cells inside have committed to %s against this cell's %s"
             % (children_with_budgets, money(allocated, currency), money(budget, currency)))]


def share(spent, budget):
    """How much of the budget is gone. None when there is no budget to share."""
    if not budget:
        return None
    return spent / budget


def days_between(due_on, today):
    """Negative means the date has already passed."""
    import datetime

    due = datetime.date.fromisoformat(due_on)
    return (due - today).days


def deadline_friction(title, due_on, today, progress):
    """What one dated piece of work is costing, if anything."""
    left = days_between(due_on, today)
    if left < 0:
        return [(OVERDUE_COST, "“%s” was due %s" % (title, _ago(-left)))]
    if left <= SOON_DAYS and progress == 0:
        return [(SOON_COST, "“%s” is due %s and has not been started" % (title, _within(left)))]
    return []


def budget_friction(spent, budget, currency, remaining_work):
    """
    What the money is costing. Overspending is only worth saying once; a
    budget nearly gone with nothing left to do is not a problem, so the tight
    warning needs work still outstanding to mean anything.
    """
    used = share(spent, budget)
    if used is None:
        return []
    if used > 1:
        return [(OVER_BUDGET_COST, "the budget is spent and over by %s"
                 % money(spent - budget, currency))]
    if used >= TIGHT and remaining_work:
        return [(TIGHT_BUDGET_COST, "%d%% of the budget is spent with %d things still to do"
                 % (round(used * 100), remaining_work))]
    return []


def money(amount, currency):
    whole = round(amount)
    return "%s %s" % (currency or "", "{:,}".format(whole))


def _ago(days):
    if days == 0:
        return "today"
    if days == 1:
        return "yesterday"
    return "%d days ago" % days


def _within(days):
    if days == 0:
        return "today"
    if days == 1:
        return "tomorrow"
    return "in %d days" % days
