"""
Health: the arithmetic. Pure functions over plain numbers.

    Potential  →  Friction  →  Effective Capacity  →  Momentum  →  Health

Nothing here is stored, and nothing here is a target. These are diagnostics:
they say where a cell is losing its capability, not what anybody should do
about it. The organisation decides; the software observes.

Every weight below is a first cut, chosen to be explainable rather than
accurate, and kept in one place so it can be argued with. The tests pin the
*relationships* -- more people means more potential, unclaimed work costs more
than unstarted work -- rather than the exact numbers, so the model can be
sharpened without rewriting them.
"""

SCALE = 100

# --- potential: what this cell could do if nothing slowed it down ----------
# Three sources, summing to the scale. People dominate, but with sharply
# diminishing returns: the tenth person adds far less than the second.
FROM_PEOPLE = 60
FROM_LEARNING = 20
FROM_EVIDENCE = 20

PERSON_DECAY = 0.85     # each additional person adds 85% of what the last did
LEARNING_FULL = 4       # recorded outcomes at which learning is maxed out
EVIDENCE_FULL = 7       # pieces of evidence at which being informed is maxed

# --- health bands ---------------------------------------------------------
BANDS = (
    (75, "excellent"),
    (58, "good"),
    (38, "moderate"),
    (20, "at risk"),
    (0, "critical"),
)

RISING, STEADY, FALLING, UNKNOWN = "rising", "steady", "falling", "unknown"
MOMENTUM_NUDGE = 8      # how far momentum moves the health score
QUIET = 6               # fewer events than this either side and we say nothing


def potential(people, outcomes_recorded, evidence_count):
    """
    What this cell could achieve. Optimistic on purpose: it ignores every
    delay, every stuck question and every unclaimed job. That is friction's
    business, and keeping the two apart is what makes the difference between
    them legible.
    """
    people_part = FROM_PEOPLE * (1 - PERSON_DECAY ** max(0, people))
    learning = FROM_LEARNING * min(1.0, outcomes_recorded / LEARNING_FULL)
    informed = FROM_EVIDENCE * min(1.0, evidence_count / EVIDENCE_FULL)
    return int(round(people_part + learning + informed))


def friction(signals, ceiling=None):
    """
    Everything standing between the cell and its potential, added up. Capped
    at the cell's own potential: a cell cannot lose more than it has.
    """
    total = sum(points for points, _reason in signals)
    return min(total, ceiling if ceiling is not None else SCALE)


def capacity(potential_score, friction_score):
    """The useful work actually available right now."""
    return max(0, potential_score - friction_score)


def momentum(recent, previous):
    """
    Whether the cell is becoming healthier or weaker -- the derivative, not
    the level. A cell at 20% that is speeding up is in better shape than one
    at 80% that has stopped.

    Measured over the cell's own recent history rather than the calendar, so
    a group that works in weekend bursts is not called dying on a Tuesday.
    """
    if recent + previous < QUIET:
        return UNKNOWN
    if previous == 0:
        return RISING if recent else UNKNOWN
    ratio = recent / previous
    if ratio >= 1.15:
        return RISING
    if ratio <= 0.85:
        return FALLING
    return STEADY


def health(capacity_score, momentum_state):
    """
    The summary a leader reads in a second. Capacity is the level; momentum
    tips it, because a cell losing ground deserves to be described worse than
    the same cell holding steady.
    """
    score = capacity_score
    if momentum_state == RISING:
        score += MOMENTUM_NUDGE
    elif momentum_state == FALLING:
        score -= MOMENTUM_NUDGE
    score = max(0, min(SCALE, score))

    for floor, name in BANDS:
        if score >= floor:
            return name, score
    return BANDS[-1][1], score


def attention(signals, limit=4):
    """
    Friction, said in human words. This is what people actually see: not a
    number they cannot act on, but the two or three things currently in the
    way, worst first.
    """
    ranked = sorted(signals, key=lambda s: -s[0])
    return [reason for _points, reason in ranked[:limit]]
