"""
Member: business rules.

Pure functions. No storage, no events, no HTTP -- everything here can be
tested by calling it, which is the point of keeping it separate.
"""

from ...kernel.errors import DomainError

LEADER = "leader"
MEMBER = "member"
ROLES = (LEADER, MEMBER)

# Below this many people a cell is informal and anyone inside it may bring
# someone else in. Above it, admitting people becomes a leader's act.
INFORMAL_BELOW = 5


def clean_name(name):
    name = (name or "").strip()
    if not name:
        raise DomainError("A name is required.")
    return name


def clean_email(email):
    email = (email or "").strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise DomainError("An email address is required.")
    return email


def check_role(role):
    if role not in ROLES:
        raise DomainError("A person is either a member or a leader.")
    return role


def admitting_needs_leader(cell_scale):
    """Formality arrives with size, not with configuration."""
    return cell_scale >= INFORMAL_BELOW


def check_last_leader(role, leader_count):
    """A cell cannot be left with nobody accountable for it."""
    if role == MEMBER and leader_count <= 1:
        raise DomainError("A cell cannot be left without a leader.")
