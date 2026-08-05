"""Member: events and their projections."""

from ...kernel import events


@events.projector("UserRegistered")
def _registered(conn, event):
    p = event["payload"]
    conn.execute(
        "INSERT OR REPLACE INTO users (id, name, email, registered_at) VALUES (?, ?, ?, ?)",
        (event["subject_id"], p["name"], p["email"], event["occurred_at"]),
    )


@events.projector("MemberJoined")
def _joined(conn, event):
    conn.execute(
        "INSERT OR IGNORE INTO memberships (cell_id, user_id, role, joined_at)"
        " VALUES (?, ?, ?, ?)",
        (event["cell_id"], event["subject_id"], event["payload"]["role"], event["occurred_at"]),
    )


@events.projector("MemberRoleChanged")
def _role_changed(conn, event):
    conn.execute(
        "UPDATE memberships SET role = ? WHERE cell_id = ? AND user_id = ?",
        (event["payload"]["role"], event["cell_id"], event["subject_id"]),
    )
