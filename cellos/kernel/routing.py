"""
The route table.

A neutral registry of (method, pattern, handler) that domains write their own
endpoints into. It knows nothing about sockets, headers or JSON -- the app
layer builds a server on top of it, and could build a different one.
"""

from .errors import DomainError, NotFound

ROUTES = []


def route(method, pattern, public=False):
    """
    Declare an endpoint. `<name>` in a pattern becomes a keyword argument.
    `public` means no signed-in actor is required.
    """
    parts = pattern.strip("/").split("/")

    def register(fn):
        ROUTES.append((method, parts, fn, public, pattern))
        return fn

    return register


def match(method, path):
    """Find the handler for a path, or say why there isn't one."""
    wanted = path.strip("/").split("/")
    other_methods = set()
    for m, parts, fn, public, _pattern in ROUTES:
        if len(parts) != len(wanted):
            continue
        params = {}
        for p, w in zip(parts, wanted):
            if p.startswith("<") and p.endswith(">"):
                params[p[1:-1]] = w
            elif p != w:
                break
        else:
            if m == method:
                return fn, params, public
            other_methods.add(m)
    if other_methods:
        raise DomainError("This address does not answer %s." % method)
    raise NotFound("No such address.")


def table():
    """Every registered endpoint, for documentation and tests."""
    return sorted((m, pattern) for m, _p, _f, _pub, pattern in ROUTES)
