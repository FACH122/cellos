"""
Member: the public interface of this domain.

Identity (who is acting) and membership (where they belong). Authorisation --
what they may do there -- belongs to the permission domain, which reads this
one but never writes it.

Authentication here is a name and an email with no password. It is local
development identity; see README.
"""

import uuid

from ...kernel import db, events
from ...kernel.errors import DomainError, NotFound
from .. import permission
from ..hierarchy import service as hierarchy
from . import model, rules

LEADER = rules.LEADER
MEMBER = rules.MEMBER


# ---------------------------------------------------------------- identity

def register(name, email):
    """Find the person, or record that they now exist."""
    name = rules.clean_name(name)
    email = rules.clean_email(email)

    existing = model.user_by_email(email)
    if existing:
        return existing

    user_id = events.new_id("user")
    events.append("UserRegistered", actor_id=user_id, subject_id=user_id,
                  name=name, email=email)
    return model.user(user_id)


def sign_in(name, email):
    user = register(name, email)
    token = uuid.uuid4().hex
    conn = db.connect()
    with db.write_lock:
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, user["id"], events.now()),
        )
        conn.commit()
    return token, user


def sign_out(token):
    conn = db.connect()
    with db.write_lock:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()


def user_for_token(token):
    if not token:
        return None
    return db.row(
        "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token = ?",
        (token,),
    )


def get(user_id):
    user = model.user(user_id)
    if user is None:
        raise NotFound("No such person.")
    return user


# -------------------------------------------------------------- membership

def require_admitter(actor_id, cell_id):
    """Who may bring someone in: anyone while the cell is small, a leader after."""
    if rules.admitting_needs_leader(hierarchy.scale(cell_id)):
        permission.require_leader(actor_id, cell_id, "bring someone into this cell")
    else:
        permission.require_member(actor_id, cell_id)


def may_admit(actor_id, cell_id):
    """The same rule asked ahead of time, so nothing is offered that would be refused."""
    return permission.allows(require_admitter, actor_id, cell_id)


def join(actor_id, cell_id, user_id, role=MEMBER):
    """Record a membership. Used by the cell domain when a cell is created."""
    rules.check_role(role)
    events.append("MemberJoined", actor_id=actor_id, cell_id=cell_id,
                  subject_id=user_id, role=role)


def admit(actor_id, cell_id, name, email, role=MEMBER):
    """Bring a person into a cell, registering them if they are new."""
    require_admitter(actor_id, cell_id)
    rules.check_role(role)

    person = register(name, email)
    if model.membership(person["id"], cell_id):
        raise DomainError("%s is already here." % person["name"])

    join(actor_id, cell_id, person["id"], role)
    return person


def set_role(actor_id, cell_id, user_id, role):
    permission.require_leader(actor_id, cell_id, "change who leads")
    rules.check_role(role)
    if not model.membership(user_id, cell_id):
        raise DomainError("That person is not in this cell.")
    rules.check_last_leader(role, model.leader_count(cell_id))
    events.append("MemberRoleChanged", actor_id=actor_id, cell_id=cell_id,
                  subject_id=user_id, role=role)


def members(cell_id):
    return model.members_of(cell_id)
