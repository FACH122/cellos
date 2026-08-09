"""Task: HTTP endpoints."""

from ...kernel.routing import route
from . import service


@route("POST", "/api/cells/<cell_id>/tasks")
def create(actor, body, cell_id):
    from ...app import views
    service.create(actor["id"], cell_id, body.get("title"), body.get("owner_id"))
    return views.cell(actor["id"], cell_id)


@route("GET", "/api/tasks/<task_id>")
def read(actor, body, task_id):
    """One piece of work on its own, for the page that is only about it."""
    from ...app import views
    return views.task(actor["id"], task_id)


@route("POST", "/api/tasks/<task_id>/cell")
def expand(actor, body, task_id):
    """This is bigger than one person: the work becomes a cell's mission."""
    from ...app import views
    task = service.get(task_id)
    service.expand(actor["id"], task_id, body.get("goal"))
    return views.cell(actor["id"], task["cell_id"])


@route("POST", "/api/tasks/<task_id>/notes")
def note(actor, body, task_id):
    """Say something while doing the work."""
    from ...app import views
    service.note(actor["id"], task_id, body.get("body"))
    return views.task(actor["id"], task_id)


@route("PATCH", "/api/tasks/<task_id>")
def update(actor, body, task_id):
    from ...app import views
    task = service.get(task_id)
    if "owner_id" in body:
        task = service.assign(actor["id"], task_id, body["owner_id"])
    if "progress" in body:
        task = service.report_progress(actor["id"], task_id, body["progress"])
    if "due_on" in body:
        task = service.set_deadline(actor["id"], task_id, body["due_on"])
    if "cost" in body:
        task = service.record_cost(actor["id"], task_id, body["cost"])
    return views.cell(actor["id"], task["cell_id"])
