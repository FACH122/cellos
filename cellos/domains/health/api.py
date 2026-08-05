"""
Health: HTTP endpoints.

The cell view already carries the reading. This exists for asking about one
cell on its own, and for the trail, which is too long to send with everything
else.
"""

from ...kernel.routing import route
from .. import permission
from . import service


@route("GET", "/api/cells/<cell_id>/health")
def read(actor, body, cell_id):
    permission.require_sight(actor["id"], cell_id)
    reading = service.of_cell(cell_id)
    reading["trail"] = service.trail(cell_id)
    return reading
