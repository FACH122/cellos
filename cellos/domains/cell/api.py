"""Cell: HTTP endpoints."""

from ...kernel.routing import route
from . import service


@route("GET", "/api/home")
def home(actor, body):
    from ...app import views
    return views.home(actor["id"])


@route("POST", "/api/cells")
def create(actor, body):
    from ...app import views
    created = service.create(actor["id"], body.get("goal"), body.get("parent_id"))
    return views.cell(actor["id"], created["id"])


@route("GET", "/api/cells/<cell_id>")
def read(actor, body, cell_id):
    from ...app import views
    return views.cell(actor["id"], cell_id)


@route("PATCH", "/api/cells/<cell_id>")
def refine(actor, body, cell_id):
    from ...app import views
    service.refine_goal(actor["id"], cell_id, body.get("goal"))
    return views.cell(actor["id"], cell_id)


@route("PUT", "/api/cells/<cell_id>/commitments")
def commitments(actor, body, cell_id):
    """
    What this cell has committed to: a budget, a date, either or neither.
    Both optional and absent by default; passing nothing for one clears it.
    """
    from ...app import views
    if "amount" in body or "currency" in body:
        service.set_budget(actor["id"], cell_id, body.get("amount"), body.get("currency"))
    if "due_on" in body:
        service.set_deadline(actor["id"], cell_id, body.get("due_on"))
    return views.cell(actor["id"], cell_id)


@route("GET", "/api/cells/<cell_id>/history")
def history(actor, body, cell_id):
    from ...app import views
    return {"events": views.history(actor["id"], cell_id)}
