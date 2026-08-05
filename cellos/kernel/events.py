"""
The event log.

Every important action appends one immutable event. Current state is a
projection of that log and nothing writes to a projection table except a
projector.

Three kinds of handler attach to an event type:

  projector  restates the event as current state. Never appends. Runs on live
             writes *and* on replay, so a rebuild reproduces state exactly.

  reactor    one domain answering another domain's event by appending its own
             (an accepted decision becoming tasks). Runs on live writes only,
             after the surrounding unit of work commits -- on replay the
             events it once produced are already in the log.

  listener   read-only observation. Never appends, never projects.

A unit of work groups several appends into one commit, so a transition that
must record two facts -- a leader override and the acceptance it caused --
cannot leave half of itself behind.
"""

import json
import threading
import uuid
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone

from . import db
from .errors import DomainError

_projectors = {}
_reactors = defaultdict(list)
_listeners = defaultdict(list)
_replaying = False
_local = threading.local()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix):
    return "%s_%s" % (prefix, uuid.uuid4().hex[:12])


# ------------------------------------------------------------ registration

def projector(*types):
    def register(fn):
        for t in types:
            if t in _projectors:
                raise RuntimeError("two projectors claim %r" % t)
            _projectors[t] = fn
        return fn

    return register


def reactor(*types):
    def register(fn):
        for t in types:
            _reactors[t].append(fn)
        return fn

    return register


def listener(*types):
    def register(fn):
        for t in types:
            _listeners[t].append(fn)
        return fn

    return register


def known(type):
    return type in _projectors


# ------------------------------------------------------------ writing

@contextmanager
def unit_of_work():
    """
    One commit, however many appends. Reentrant: an inner unit joins the
    outer one rather than committing early.
    """
    conn = db.connect()
    with db.write_lock:
        depth = getattr(_local, "depth", 0)
        _local.depth = depth + 1
        if depth == 0:
            _local.pending = []
        try:
            yield conn
        except Exception:
            if depth == 0:
                conn.rollback()
                _local.pending = []
            raise
        else:
            if depth == 0:
                conn.commit()
        finally:
            _local.depth = depth

    # Reactors run once the facts they are answering are durable.
    if depth == 0:
        pending, _local.pending = getattr(_local, "pending", []), []
        for event in pending:
            for react in _reactors[event["type"]]:
                react(event)


def append(type, actor_id=None, cell_id=None, subject_id=None, **payload):
    """Record that something happened, then let state catch up."""
    if type not in _projectors:
        raise DomainError("Unknown event type %r." % type)

    with unit_of_work() as conn:
        occurred_at = now()
        cur = conn.execute(
            "INSERT INTO events (type, actor_id, cell_id, subject_id, payload, occurred_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (type, actor_id, cell_id, subject_id, json.dumps(payload), occurred_at),
        )
        event = {
            "id": cur.lastrowid,
            "type": type,
            "actor_id": actor_id,
            "cell_id": cell_id,
            "subject_id": subject_id,
            "payload": payload,
            "occurred_at": occurred_at,
        }
        _projectors[type](conn, event)
        for observe in _listeners[type]:
            observe(event)
        if not _replaying:
            _local.pending.append(event)
    return event


# ------------------------------------------------------------ replay

def replay():
    """Rebuild every projection from the log alone."""
    global _replaying
    conn = db.connect()
    db.drop_projections()
    _replaying = True
    count = 0
    try:
        with db.write_lock:
            for r in conn.execute("SELECT * FROM events ORDER BY id"):
                event = dict(r)
                event["payload"] = json.loads(event["payload"])
                handler = _projectors.get(event["type"])
                if handler is None:
                    raise RuntimeError(
                        "event %s has type %r with no projector; refusing a partial rebuild"
                        % (event["id"], event["type"])
                    )
                handler(conn, event)
                count += 1
            conn.commit()
    finally:
        _replaying = False
    return count


# ------------------------------------------------------------ reading

def history(cell_ids=None, subject_id=None, types=None, limit=200):
    """Read the log back. This is the organizational memory."""
    where, params = [], []
    if cell_ids is not None:
        cell_ids = list(cell_ids)
        if not cell_ids:
            return []
        where.append("cell_id IN (%s)" % db.marks(cell_ids))
        params.extend(cell_ids)
    if subject_id is not None:
        where.append("subject_id = ?")
        params.append(subject_id)
    if types:
        types = list(types)
        where.append("type IN (%s)" % db.marks(types))
        params.extend(types)

    sql = "SELECT * FROM events"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    out = []
    for r in db.rows(sql, params):
        r["payload"] = json.loads(r["payload"])
        out.append(r)
    return out
