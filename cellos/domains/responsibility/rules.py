"""
Responsibility: business rules. Pure functions.

Permission asks what a person is *allowed* to do. Responsibility asks what
they are *expected to accomplish*. They are different questions and this
domain answers the second one.

Four roles, and none of them is assigned. Every one is read off facts the
system already records, because a system that has to be told who is
responsible has already lost the answer:

    leader        accountable for the whole -- the cell's leader
    responsible   expected to accomplish this -- whoever holds it
    verifier      confirms it is really done -- the leader above the doer
    participants  took part -- voted, argued, reported progress

A thing with no responsible person is not a mistake to be validated away. It
is the most useful signal in the system: work nobody has picked up.
"""

LEADER = "leader"
RESPONSIBLE = "responsible"
VERIFIER = "verifier"
PARTICIPANT = "participant"

ROLES = (LEADER, RESPONSIBLE, VERIFIER, PARTICIPANT)


def verifier_of(doer_id, leaders, above_leaders):
    """
    Who confirms this is done.

    Not the person who did it. Accountability points upward: work is verified
    by the leader above whoever did it, and only falls back to the local
    leader when there is nothing above.
    """
    candidates = [uid for uid in above_leaders if uid != doer_id]
    if candidates:
        return candidates[0]
    local = [uid for uid in leaders if uid != doer_id]
    return local[0] if local else None


def standing_of(user_id, roles):
    """Which of the four roles this person holds on one thing."""
    return sorted(role for role, holders in roles.items() if user_id in holders)


def is_blocked(state, responsible_id, progress):
    """
    Work that is not moving and not anyone's. Unowned unfinished work is
    blocked; owned work at zero is stalled, which is a different thing and
    belongs to a person.
    """
    return state in ("open",) and responsible_id is None and progress == 0


def is_stalled(state, responsible_id, progress):
    return state == "active" and responsible_id is not None and progress == 0
