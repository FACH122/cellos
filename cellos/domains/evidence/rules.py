"""Evidence: business rules. Pure functions."""

from ...kernel.errors import DomainError

KINDS = ("link", "file", "document", "measurement", "report", "note")
# An option is a subject in its own right: a quote for one venue is not
# evidence about "where do we hold it", it is evidence about the garden.
SUBJECTS = ("decision", "option", "task", "cell")


def clean_label(label):
    label = (label or "").strip()
    if not label:
        raise DomainError("Evidence needs a description.")
    return label


def check_kind(kind):
    if kind not in KINDS:
        raise DomainError("Unknown kind of evidence.")
    return kind


def check_subject(subject_kind):
    if subject_kind not in SUBJECTS:
        raise DomainError("Evidence attaches to a decision, an answer, a task or a cell.")
    return subject_kind


# --------------------------------------------------------------- diagnostics

UNEVIDENCED_COST = 2   # settled against nothing anybody can point at


def friction(question, turnout, evidence_count):
    """
    A question the cell voted on and nobody offered anything for. Small,
    deliberately: evidence is optional everywhere in CellOS, and two people
    choosing a caterer owe nobody a citation. It only starts to matter once
    enough people were involved that somebody should have had a reason.
    """
    if evidence_count or turnout < 3:
        return []
    return [(UNEVIDENCED_COST,
             "“%s” was settled with nothing anybody can point at" % question)]
