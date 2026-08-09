"""
Governance: how a cell decides, derived from how big it is.

Nothing here is configurable, because configuration is the thing this file
exists to avoid. A cell that grows acquires capabilities and a cell that
shrinks gives them back.

    one person       a list of tasks
    two people       votes, because the moment there is somebody else to
                     disagree with, agreement stops being something you can
                     assume and starts being something you find out
    twenty people    child cells, and a leader who confirms the vote
    fifty people     a dashboard, because nobody can see the whole cell
    two hundred      analytics, because the shape of the work is now a question

Pure functions of a headcount. No storage, no queries.
"""

VOTING = "voting"
CHILDREN = "children"
LEADER_CONFIRMS = "leader_confirms"
DASHBOARD = "dashboard"
ANALYTICS = "analytics"

THRESHOLDS = (
    (VOTING, 2),
    (CHILDREN, 20),
    (LEADER_CONFIRMS, 20),
    (DASHBOARD, 50),
    (ANALYTICS, 200),
)

# Present at every scale, including one person alone.
ALWAYS = ("tasks", "decisions", "evidence", "knowledge")

# How a cell settles a question.
INFORMAL = "informal"          # someone decides and writes down why
VOTE_DECIDES = "vote_decides"  # the count settles it
LEADER_CONFIRMS_VOTE = "leader_confirms_vote"  # the count advises, a leader signs


def threshold(capability):
    return dict(THRESHOLDS)[capability]


def capabilities(scale):
    unlocked = set(ALWAYS)
    for name, at in THRESHOLDS:
        if scale >= at:
            unlocked.add(name)
    return unlocked


def has(scale, capability):
    return capability in capabilities(scale)


def model(scale):
    """Which of the three ways of settling a question this cell uses."""
    if has(scale, LEADER_CONFIRMS):
        return LEADER_CONFIRMS_VOTE
    if has(scale, VOTING):
        return VOTE_DECIDES
    return INFORMAL


def votes(scale):
    """Whether a decision in this cell goes to the cell at all."""
    return model(scale) in (VOTE_DECIDES, LEADER_CONFIRMS_VOTE)


def next_threshold(scale):
    """What growing would add. Used by tests and the seed, shown to nobody."""
    for name, at in THRESHOLDS:
        if scale < at:
            return name, at
    return None, None
