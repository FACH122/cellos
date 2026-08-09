"""Task: events and their projections."""

from ...kernel import events


@events.projector("TaskCreated", "TaskGenerated")
def _created(conn, event):
    """
    `TaskGenerated` is work an accepted decision produced; `TaskCreated` is
    work somebody added directly. Same row, different fact about where it
    came from -- which the permanent record should not have to infer.
    """
    p = event["payload"]
    conn.execute(
        "INSERT INTO tasks (id, cell_id, title, owner_id, progress, created_at)"
        " VALUES (?, ?, ?, ?, 0, ?)",
        (event["subject_id"], event["cell_id"], p["title"],
         p.get("owner_id"), event["occurred_at"]),
    )


@events.projector("TaskAssigned")
def _assigned(conn, event):
    conn.execute(
        "UPDATE tasks SET owner_id = ? WHERE id = ?",
        (event["payload"].get("owner_id"), event["subject_id"]),
    )


@events.projector("ProgressUpdated")
def _progress(conn, event):
    conn.execute(
        "UPDATE tasks SET progress = ? WHERE id = ?",
        (event["payload"]["progress"], event["subject_id"]),
    )


@events.projector("TaskCompleted")
def _completed(conn, event):
    conn.execute(
        "UPDATE tasks SET progress = 100, completed_at = ? WHERE id = ?",
        (event["occurred_at"], event["subject_id"]),
    )


@events.projector("TaskReopened")
def _reopened(conn, event):
    conn.execute(
        "UPDATE tasks SET progress = ?, completed_at = NULL WHERE id = ?",
        (event["payload"]["progress"], event["subject_id"]),
    )


@events.projector("TaskExpanded")
def _expanded(conn, event):
    """
    Nothing to write. The task row is untouched -- that is the point: the work
    did not become something else, it grew, and the `expands_into`
    relationship formed in the same unit of work says what it grew into.

    The event exists so the permanent record can say a leader judged the work
    too large for one person, rather than leave that to be inferred from a
    relationship quietly appearing.
    """



@events.projector("DeadlineSet")
def _deadline(conn, event):
    conn.execute("UPDATE tasks SET due_on = ? WHERE id = ?",
                 (event["payload"].get("due_on"), event["subject_id"]))


@events.projector("CostRecorded")
def _cost(conn, event):
    conn.execute("UPDATE tasks SET cost = ? WHERE id = ?",
                 (event["payload"].get("cost"), event["subject_id"]))


@events.projector("TaskNoted")
def _noted(conn, event):
    conn.execute(
        "INSERT INTO notes (id, task_id, author_id, body, said_at) VALUES (?, ?, ?, ?, ?)",
        (event["id"], event["subject_id"], event["actor_id"],
         event["payload"]["body"], event["occurred_at"]),
    )
