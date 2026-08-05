"""
Dashboard: derived, never stored.

What is left here is the shape of the work at a scale nobody can see by
looking: counts, rates and rollups. Who is responsible for what moved to the
responsibility domain, which is what the interface actually shows.
"""

from ...kernel import db
from .. import permission
from ..decision import model as decision_model
from ..decision.workflow import UNSETTLED
from ..evidence import model as evidence_model
from ..hierarchy import service as hierarchy
from ..progress import service as progress
from ..task import model as task_model


def for_leader(user_id, cell_id):
    """One row per child cell, each derived from the work inside it."""
    visible = permission.visible_cell_ids(user_id)
    rows = []
    for child in hierarchy.children(cell_id):
        if child["id"] not in visible:
            continue
        below = hierarchy.subtree_ids(child["id"])
        p = progress.of_cell(child["id"])
        rows.append({
            "id": child["id"],
            "goal": child["goal"],
            "people": hierarchy.scale(child["id"]),
            "percent": p["percent"],
            "task_count": p["task_count"],
            "remaining": p["remaining"],
            "open_decisions": len(decision_model.in_cells(below, states=UNSETTLED)),
            "unowned": task_model.unowned_count(below),
            "stalled": task_model.stalled_count(below),
        })
    return rows


def metrics(cell_id):
    """The shape of the work, once a cell is too big to see it directly."""
    below = hierarchy.subtree_ids(cell_id)
    states = decision_model.count_by_state(below)
    how = decision_model.count_by_how(below)
    settled = sum(how.values())

    return {
        "people": hierarchy.scale(cell_id),
        "cells": len(below),
        "decisions": sum(states.values()),
        "decisions_by_state": states,
        "resolved_by": how,
        # How often leadership went against the cell. Worth watching in either
        # direction: always zero can mean the vote is theatre.
        "override_rate": round(100 * how.get("override", 0) / settled) if settled else 0,
        "knowledge_recorded": states.get("knowledge", 0),
        "evidence": evidence_model.count_in(below),
        "work": progress.of_cell(cell_id),
        "unowned_tasks": task_model.unowned_count(below),
        "stalled_tasks": task_model.stalled_count(below),
    }


def knowledge(cell_ids, limit=25):
    """Decisions in a subtree that have an outcome. This is what a cell knows."""
    cell_ids = list(cell_ids)
    if not cell_ids:
        return []
    return db.rows(
        """
        SELECT d.id, d.question, d.outcome, d.lesson, d.closed_at, d.cell_id,
               c.goal AS cell_goal, u.name AS decided_by_name
        FROM decisions d
        JOIN cells c ON c.id = d.cell_id
        LEFT JOIN users u ON u.id = d.decided_by
        WHERE d.cell_id IN (%s) AND d.state = 'knowledge'
        ORDER BY d.closed_at DESC LIMIT ?
        """ % db.marks(cell_ids),
        cell_ids + [limit],
    )
