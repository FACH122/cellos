"""
Decision: HTTP endpoints.

There is one endpoint for moving a decision, and it names a workflow step. The
server tells the client which steps are available; the client fires one by
name. No endpoint accepts a state, and no handler decides which transition
applies -- that is the workflow engine's job.
"""

from ...kernel.routing import route
from . import service


@route("POST", "/api/cells/<cell_id>/decisions")
def propose(actor, body, cell_id):
    from ...app import views
    service.propose(
        actor["id"], cell_id, body.get("question"), body.get("detail", ""),
        body.get("options") or [], body.get("work") or {},
        about=body.get("about"),
    )
    return views.cell(actor["id"], cell_id)


@route("GET", "/api/decisions/<decision_id>")
def read(actor, body, decision_id):
    from ...app import views
    return views.decision(actor["id"], decision_id)


@route("POST", "/api/decisions/<decision_id>/remarks")
def remark(actor, body, decision_id):
    service.remark(actor["id"], decision_id, body.get("body"))
    return _cell_after(actor, decision_id)


@route("POST", "/api/decisions/<decision_id>/votes")
def vote(actor, body, decision_id):
    service.vote(actor["id"], decision_id, body.get("option_id"))
    return _cell_after(actor, decision_id)


@route("POST", "/api/decisions/<decision_id>/steps/<step>")
def advance(actor, body, decision_id, step):
    service.act(actor["id"], decision_id, step, **body)
    return _cell_after(actor, decision_id)


def _cell_after(actor, decision_id):
    from ...app import views
    return views.cell(actor["id"], service.get(decision_id)["cell_id"])
