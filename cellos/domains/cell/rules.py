"""Cell: business rules. Pure functions."""

from ...kernel.errors import DomainError

MAX_GOAL = 300


def clean_goal(goal):
    goal = (goal or "").strip()
    if not goal:
        raise DomainError("A cell needs a goal.")
    if len(goal) > MAX_GOAL:
        raise DomainError("A goal should be one sentence, not an essay.")
    return goal


def check_can_hold_children(parent_scale, threshold):
    """
    A cell splits into child cells when it is too big to hold its work
    directly -- not because someone turned the feature on.
    """
    if parent_scale < threshold:
        raise DomainError(
            "This cell is still small enough to hold its work directly. "
            "Child cells appear once it is coordinating %d people." % threshold
        )


MAX_BUDGET = 1e12


def clean_budget(amount, currency):
    """
    A budget is optional. Clearing it is not the same as setting it to zero:
    a cell with no budget has not committed to anything, and a cell with a
    budget of zero has committed to spending nothing.
    """
    if amount in (None, ""):
        return None, None
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        raise DomainError("A budget is a number.")
    if amount < 0:
        raise DomainError("A budget cannot be negative.")
    if amount > MAX_BUDGET:
        raise DomainError("That is not a budget, that is a typo.")
    currency = (currency or "").strip()[:8] or "EUR"
    return round(amount, 2), currency
