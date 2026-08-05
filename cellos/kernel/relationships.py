"""
Typed relationships.

Every edge between two entities is a row here rather than a foreign key, so a
new kind of connection needs a registration and not a migration. Each kind
declares which entity types may sit at either end, and every write is checked
against that declaration -- which is stricter than an untyped column, not
looser.

Rows are projected from `RelationshipFormed` events like any other state, so
the graph rebuilds from the log.

Two edges named in the Phase 2 brief are deliberately *not* rows here:

  Task -> Progress Update   A progress update is an event, not an entity. The
                            log already records which task each one belongs
                            to; a relationship row would be a second copy of
                            that fact, which the normalization rule forbids.

  Decision -> Outcome       An outcome is one-to-one with its decision and has
                            no independent identity -- it is an attribute of
                            the decision, recorded by `KnowledgeRecorded`.
                            Making it an entity would be a new feature, which
                            this phase excludes.

Both are noted rather than quietly skipped; if outcomes ever need to be
recorded more than once per decision, that is the moment to promote them.
"""

from collections import namedtuple

from . import db, events
from .errors import DomainError

Kind = namedtuple("Kind", "name tail head single_head description")

_kinds = {}


def register(name, tail, head, single_head=False, description=""):
    """
    Declare an edge. `tail` and `head` are entity type names, or tuples of
    them where more than one is legitimate. `single_head` means the entity at
    the head may have at most one such edge pointing at it -- a cell has one
    parent, not several.
    """
    _kinds[name] = Kind(
        name=name,
        tail=(tail,) if isinstance(tail, str) else tuple(tail),
        head=(head,) if isinstance(head, str) else tuple(head),
        single_head=single_head,
        description=description,
    )
    return name


def kinds():
    return dict(_kinds)


def _kind(name):
    if name not in _kinds:
        raise DomainError("Unknown relationship kind %r." % name)
    return _kinds[name]


# ------------------------------------------------------------ projection

@events.projector("RelationshipFormed")
def _project_formed(conn, event):
    p = event["payload"]
    conn.execute(
        "INSERT OR IGNORE INTO relationships"
        " (id, kind, from_kind, from_id, to_kind, to_id, formed_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            event["subject_id"],
            p["kind"],
            p["from_kind"],
            p["from_id"],
            p["to_kind"],
            p["to_id"],
            event["occurred_at"],
        ),
    )


# ------------------------------------------------------------ writing

def form(kind, from_kind, from_id, to_kind, to_id, actor_id=None, cell_id=None):
    """Connect two entities. Validated against the registered kind."""
    spec = _kind(kind)
    if from_kind not in spec.tail:
        raise DomainError(
            "A %s relationship starts at %s, not %s."
            % (kind, " or ".join(spec.tail), from_kind)
        )
    if to_kind not in spec.head:
        raise DomainError(
            "A %s relationship ends at %s, not %s." % (kind, " or ".join(spec.head), to_kind)
        )
    if from_id == to_id:
        raise DomainError("Nothing may be related to itself.")
    if spec.single_head and head_of(kind, to_id) is not None:
        raise DomainError("That already has a %s." % kind)

    return events.append(
        "RelationshipFormed",
        actor_id=actor_id,
        cell_id=cell_id,
        subject_id=events.new_id("rel"),
        kind=kind,
        from_kind=from_kind,
        from_id=from_id,
        to_kind=to_kind,
        to_id=to_id,
    )


# ------------------------------------------------------------ reading

def heads(kind, from_id):
    """Everything this entity points at along `kind`."""
    _kind(kind)
    return [
        r["to_id"]
        for r in db.rows(
            "SELECT to_id FROM relationships WHERE kind = ? AND from_id = ? ORDER BY formed_at",
            (kind, from_id),
        )
    ]


def tails(kind, to_id):
    """Everything pointing at this entity along `kind`."""
    _kind(kind)
    return [
        r["from_id"]
        for r in db.rows(
            "SELECT from_id FROM relationships WHERE kind = ? AND to_id = ? ORDER BY formed_at",
            (kind, to_id),
        )
    ]


def head_of(kind, to_id):
    """The single entity pointing at this one, for `single_head` kinds."""
    found = tails(kind, to_id)
    return found[0] if found else None


def exists(kind, from_id, to_id):
    return db.row(
        "SELECT 1 FROM relationships WHERE kind = ? AND from_id = ? AND to_id = ?",
        (kind, from_id, to_id),
    ) is not None


def count(kind, from_id):
    return db.value(
        "SELECT count(*) FROM relationships WHERE kind = ? AND from_id = ?",
        (kind, from_id),
        default=0,
    )
