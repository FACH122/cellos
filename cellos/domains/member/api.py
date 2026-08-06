"""
Member: HTTP endpoints.

Translation only. Every rule these handlers appear to enforce is enforced in
`service`; if a check ever appears here that is not about HTTP, it is in the
wrong file.

Mutations answer with the whole refreshed cell, because the interface is one
screen and would otherwise have to guess what changed. Composing that view is
the app layer's job, so it is imported inside the handler -- domains do not
depend on the app at import time.
"""

from ...kernel.routing import route
from . import service


@route("POST", "/api/session", public=True)
def sign_in(_actor, body):
    token, user = service.sign_in(body.get("name"), body.get("email"))
    return {"token": token, "user": _person(user)}


@route("DELETE", "/api/session")
def sign_out(actor, body):
    service.sign_out(body.get("token"))
    return {"ok": True}


@route("GET", "/api/yours")
def yours(actor, body):
    """One person across every cell they can see, and what has happened to it."""
    from ...app import views
    return views.yours(actor["id"])


@route("GET", "/api/me")
def me(actor, body):
    return {"user": _person(actor)}


@route("POST", "/api/cells/<cell_id>/members")
def admit(actor, body, cell_id):
    from ...app import views
    service.admit(actor["id"], cell_id, body.get("name"), body.get("email"),
                  body.get("role", service.MEMBER))
    return views.cell(actor["id"], cell_id)


@route("PATCH", "/api/cells/<cell_id>/members/<user_id>")
def change_role(actor, body, cell_id, user_id):
    from ...app import views
    service.set_role(actor["id"], cell_id, user_id, body.get("role"))
    return views.cell(actor["id"], cell_id)


def _person(user):
    return {"id": user["id"], "name": user["name"], "email": user["email"]}
