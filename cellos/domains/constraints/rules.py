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
TIGHT_BUDGET_COST = 4


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
