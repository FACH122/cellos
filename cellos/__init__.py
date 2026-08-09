"""
CellOS -- a decision and execution operating system.

    kernel   storage, the event log, the relationship graph, the workflow
             engine, the route table. Knows nothing about cells.
    domains  one package per part of the business, each owning its models,
             rules, events, services and endpoints.
    app      composition and the HTTP server.
"""

__version__ = "2.0"


def boot():
    """Register every domain, then make sure the database matches them."""
    from . import domains  # noqa: F401  (importing registers everything)
    from .kernel import db

    # A changed projection shape means the derived tables were just rebuilt
    # empty. Replay puts them back -- from the log, which never changed.
    if db.init():
        from .kernel import events

        events.replay()
