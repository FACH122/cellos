"""Evidence: HTTP endpoints."""

from ...kernel.routing import route
from . import service


@route("POST", "/api/evidence")
def attach(actor, body):
    from ...app import views
    attached = service.attach(
        actor["id"], body.get("subject_kind"), body.get("subject_id"),
        body.get("kind", "link"), body.get("label"), body.get("ref", ""),
    )
    return views.cell(actor["id"], attached["cell_id"])
