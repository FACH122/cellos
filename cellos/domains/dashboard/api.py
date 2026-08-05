"""
Dashboard: HTTP endpoints.

The cell view already carries whichever map the reader is entitled to, so
this endpoint exists for the case of asking for it alone. What comes back is
responsibility -- what people are expected to accomplish -- not permissions.
"""

from ...kernel.routing import route
from .. import permission
from ..responsibility import service as responsibility


@route("GET", "/api/cells/<cell_id>/children")
def children(actor, body, cell_id):
    """
    The cells directly inside this one. The map calls this when a node is
    expanded, which is why the drawing has no maximum depth: nothing is
    computed for a branch nobody has opened.
    """
    permission.require_sight(actor["id"], cell_id)
    return {"children": responsibility.children_of(actor["id"], cell_id)}


@route("GET", "/api/cells/<cell_id>/dashboard")
def read(actor, body, cell_id):
    permission.require_sight(actor["id"], cell_id)
    return {
        "shape": "leader" if permission.is_leader(actor["id"], cell_id) else "member",
        "cells": responsibility.descendants(actor["id"], cell_id),
        "yours": responsibility.graph(actor["id"], cell_id),
        "responsibility": responsibility.for_cell(cell_id),
    }
