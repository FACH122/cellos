"""
Evidence: the public interface of this domain.

Evidence answers one question -- why do we believe this is true? It is
optional everywhere and required nowhere: two people choosing a caterer owe
nobody a citation. A decision that does carry evidence carries it forever.

This domain does not know what a decision or a task is. Other domains register
how to find the cell an entity of their kind lives in, and evidence attaches
to it through the relationship graph.
"""

from ...kernel import events, relationships
from ...kernel.errors import NotFound
from .. import permission
from . import model, rules

SUPPORTS = relationships.register(
    "supports", "evidence", rules.SUBJECTS,
    description="A piece of evidence and the thing it is offered in support of.",
)

_locators = {}


def register_subject(kind, locate_cell):
    """A domain declaring that evidence may attach to its entities."""
    _locators[kind] = locate_cell


def _cell_of(subject_kind, subject_id):
    rules.check_subject(subject_kind)
    locate = _locators.get(subject_kind)
    cell_id = locate(subject_id) if locate else None
    if cell_id is None:
        raise NotFound("There is nothing there to attach evidence to.")
    return cell_id


@events.projector("EvidenceAttached")
def _attached(conn, event):
    p = event["payload"]
    conn.execute(
        "INSERT INTO evidence (id, cell_id, kind, label, ref, added_by, added_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (event["subject_id"], event["cell_id"], p["kind"], p["label"],
         p.get("ref", ""), event["actor_id"], event["occurred_at"]),
    )


def attach(actor_id, subject_kind, subject_id, kind, label, ref=""):
    cell_id = _cell_of(subject_kind, subject_id)
    permission.require_member(actor_id, cell_id)
    kind = rules.check_kind(kind)
    label = rules.clean_label(label)

    evidence_id = events.new_id("ev")
    with events.unit_of_work():
        events.append("EvidenceAttached", actor_id=actor_id, cell_id=cell_id,
                      subject_id=evidence_id, kind=kind, label=label,
                      ref=(ref or "").strip(),
                      supports_kind=subject_kind, supports_id=subject_id)
        relationships.form(SUPPORTS, "evidence", evidence_id, subject_kind, subject_id,
                           actor_id=actor_id, cell_id=cell_id)
    return model.get(evidence_id)


def supporting(subject_kind, subject_id):
    """Everything offered in support of one thing."""
    rules.check_subject(subject_kind)
    return model.many(relationships.tails(SUPPORTS, subject_id))


def used_in(cell_ids):
    """Whether this part of the organisation uses evidence at all."""
    return model.count_in(cell_ids) > 0
