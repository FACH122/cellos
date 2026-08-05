"""Cell: events and their projections."""

from ...kernel import events


@events.projector("CellCreated")
def _created(conn, event):
    """
    One event, whatever the cell's depth. A cell inside a cell is not a
    different kind of thing: where it sits is the `contains` relationship's
    business, not this event's.
    """
    conn.execute(
        "INSERT INTO cells (id, goal, created_by, created_at) VALUES (?, ?, ?, ?)",
        (event["subject_id"], event["payload"]["goal"], event["actor_id"], event["occurred_at"]),
    )


@events.projector("GoalRefined")
def _goal_refined(conn, event):
    conn.execute(
        "UPDATE cells SET goal = ? WHERE id = ?",
        (event["payload"]["goal"], event["subject_id"]),
    )


@events.projector("BudgetSet")
def _budget(conn, event):
    """
    A commitment, recorded like any other. Clearing it writes null rather than
    deleting anything: the log still says the cell once had a budget and chose
    to drop it.
    """
    p = event["payload"]
    conn.execute("UPDATE cells SET budget = ?, currency = ? WHERE id = ?",
                 (p.get("amount"), p.get("currency"), event["subject_id"]))
