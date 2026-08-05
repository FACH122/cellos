"""
The workflow engine.

A workflow is a declaration: a list of states and the transitions between
them. Nothing else in CellOS may move an object from one state to another --
no service writes a state column, and no endpoint accepts one.

The engine reads the current state, checks the transition is legal, runs the
guard, and appends the resulting events **inside a single held write lock**.
That is what makes a transition atomic: two people resolving the same
decision at the same instant cannot both pass the check, because the second
one reads the state the first one just wrote.

It also answers `available()` -- which transitions this actor could fire right
now. The interface renders that list rather than working it out for itself,
which is how business rules stay out of the UI.
"""

from collections import namedtuple

from . import db, events
from .errors import Conflict, DomainError

Transition = namedtuple(
    "Transition", "name sources target event guard extra label requires asks"
)


class Workflow:
    """
    `read_state(subject_id)` returns the current state, or None if the object
    does not exist. The workflow never touches storage itself.
    """

    def __init__(self, name, states, initial, read_state):
        self.name = name
        self.states = tuple(states)
        self.initial = initial
        self.read_state = read_state
        self.transitions = {}
        if initial not in self.states:
            raise RuntimeError("%s: initial state %r is not a state" % (name, initial))

    # -------------------------------------------------------- declaration

    def transition(self, name, sources, target, event,
                   guard=None, extra=None, label="", requires=None, asks=()):
        """
        `guard(ctx, current)` validates and returns the payload for the event,
        or raises DomainError. `extra(ctx, current)` may return a list of
        (type, payload) recorded before it. `requires(ctx)` decides whether
        this transition is offered at all -- responsibility, not validity.

        `asks` describes what the actor must supply, so an interface can build
        the form from the declaration instead of knowing what a decision is.
        """
        sources = (sources,) if isinstance(sources, str) else tuple(sources)
        for s in sources + (target,):
            if s not in self.states:
                raise RuntimeError("%s: %r is not a state" % (self.name, s))
        self.transitions[name] = Transition(
            name=name, sources=sources, target=target, event=event,
            guard=guard, extra=extra, label=label or name, requires=requires,
            asks=tuple(asks),
        )
        return self

    def position(self, state):
        """How far along the lifecycle a state sits. For display only."""
        return self.states.index(state) if state in self.states else 0

    # -------------------------------------------------------- asking

    def available(self, subject_id, ctx=None):
        """
        Transitions that could be fired right now, given who is asking.
        Guards are not run -- this answers "is this offered", not "would it
        succeed with these arguments".
        """
        current = self.read_state(subject_id)
        if current is None:
            return []
        ctx = ctx or {}
        out = []
        for t in self.transitions.values():
            if current not in t.sources:
                continue
            if t.requires and not t.requires(ctx):
                continue
            out.append({
                "name": t.name,
                "label": t.label,
                "target": t.target,
                "asks": [dict(a) for a in t.asks],
            })
        return out

    def can(self, subject_id, name, ctx=None):
        return any(t["name"] == name for t in self.available(subject_id, ctx))

    # -------------------------------------------------------- moving

    def fire(self, name, subject_id, actor_id=None, cell_id=None, **ctx):
        """
        Move the object. Read, check, guard and append all happen under one
        lock, so the state a guard saw is the state it acts on.
        """
        t = self.transitions.get(name)
        if t is None:
            raise DomainError("There is no such step in this workflow.")

        with events.unit_of_work():
            current = self.read_state(subject_id)
            if current is None:
                raise DomainError("There is nothing here to move.")
            if current not in t.sources:
                raise Conflict(
                    "This has already moved on -- it is %s now."
                    % current.replace("_", " ")
                )

            payload = t.guard(ctx, current) if t.guard else {}
            payload = dict(payload or {})

            if t.extra:
                for extra_type, extra_payload in t.extra(ctx, current) or []:
                    events.append(
                        extra_type, actor_id=actor_id, cell_id=cell_id,
                        subject_id=subject_id, **extra_payload
                    )

            payload["state"] = t.target
            events.append(
                t.event, actor_id=actor_id, cell_id=cell_id, subject_id=subject_id, **payload
            )
        return t.target


def state_projector(table, column="state"):
    """
    The projector every workflow event shares: write the target state onto the
    row. Domains use this so no service ever sets a state column by hand.
    """

    def project(conn, event):
        state = event["payload"].get("state")
        if state is None:
            return
        conn.execute(
            "UPDATE %s SET %s = ? WHERE id = ?" % (table, column),
            (state, event["subject_id"]),
        )

    return project


def read_column(table, column="state"):
    """A `read_state` for the common case of a state column on one table."""

    def read(subject_id):
        return db.value("SELECT %s FROM %s WHERE id = ?" % (column, table), (subject_id,))

    return read
