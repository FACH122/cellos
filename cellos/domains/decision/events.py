"""
Decision: events and their projections.

Every state-bearing event goes through the shared state projector, so a
transition's target is applied the same way whichever transition fired it.
The events that carry more than a state add their own columns on top.
"""

import json

from ...kernel import events, workflow

_apply_state = workflow.state_projector("decisions")


@events.projector("DecisionCreated")
def _created(conn, event):
    p = event["payload"]
    conn.execute(
        "INSERT INTO decisions (id, cell_id, question, detail, state, created_by, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            event["subject_id"], event["cell_id"], p["question"], p.get("detail", ""),
            p["state"], event["actor_id"], event["occurred_at"],
        ),
    )
    for i, opt in enumerate(p["options"]):
        conn.execute(
            "INSERT INTO options (id, decision_id, text, position, work) VALUES (?, ?, ?, ?, ?)",
            (opt["id"], event["subject_id"], opt["text"], i, json.dumps(opt.get("work", []))),
        )


@events.projector(
    "DecisionOpened", "VotingOpened", "ResolutionRequested",
    "ExecutionStarted", "ExecutionCompleted", "ExecutionResumed",
)
def _state_only(conn, event):
    _apply_state(conn, event)


@events.projector("DecisionReturned")
def _returned(conn, event):
    """The reason a decision was sent back is kept, and shown to whoever has to redo it."""
    _apply_state(conn, event)
    conn.execute(
        "UPDATE decisions SET revision_note = ? WHERE id = ?",
        (event["payload"].get("note", ""), event["subject_id"]),
    )


@events.projector("DecisionAccepted")
def _accepted(conn, event):
    _apply_state(conn, event)
    p = event["payload"]
    conn.execute(
        "UPDATE decisions SET chosen_option = ?, decided_by = ?, decided_at = ?,"
        " decided_how = ?, resolution_note = ?, revision_note = '' WHERE id = ?",
        (
            p.get("option_id"), event["actor_id"], event["occurred_at"],
            p.get("how"), p.get("note", ""), event["subject_id"],
        ),
    )


@events.projector("DecisionRejected")
def _rejected(conn, event):
    _apply_state(conn, event)
    conn.execute(
        "UPDATE decisions SET decided_by = ?, decided_at = ?, resolution_note = ? WHERE id = ?",
        (event["actor_id"], event["occurred_at"],
         event["payload"].get("note", ""), event["subject_id"]),
    )


@events.projector("LeaderOverride")
def _override(conn, event):
    """
    Recorded for its own sake. The accountability fact -- who overruled the
    cell and why -- is carried by the DecisionAccepted event that follows it
    in the same unit of work, so there is nothing to project here. This event
    exists so the permanent record can name the act rather than infer it.
    """


@events.projector("KnowledgeRecorded")
def _knowledge(conn, event):
    _apply_state(conn, event)
    p = event["payload"]
    conn.execute(
        "UPDATE decisions SET outcome = ?, lesson = ?, closed_at = ? WHERE id = ?",
        (p["outcome"], p.get("lesson", ""), event["occurred_at"], event["subject_id"]),
    )


@events.projector("RemarkAdded")
def _remark(conn, event):
    conn.execute(
        "INSERT INTO remarks (id, decision_id, option_id, author_id, body, said_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (event["id"], event["subject_id"], event["payload"].get("option_id"),
         event["actor_id"], event["payload"]["body"], event["occurred_at"]),
    )


@events.projector("VoteSubmitted")
def _vote(conn, event):
    conn.execute(
        "INSERT OR REPLACE INTO votes (decision_id, user_id, option_id, cast_at)"
        " VALUES (?, ?, ?, ?)",
        (event["subject_id"], event["actor_id"],
         event["payload"]["option_id"], event["occurred_at"]),
    )
