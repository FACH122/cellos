#!/usr/bin/env python3
"""
CellOS.

    python3 run.py demo       three orgs (200, 100, 30 people) and serve
    python3 run.py students   eight students and one assignment, and serve
    python3 run.py            start the server on http://127.0.0.1:8420
    python3 run.py seed       fill the log with cells at four different scales
    python3 run.py rebuild    throw every projection away and replay the log
    python3 run.py reset      delete the database entirely
    python3 run.py routes     list every endpoint and which domain owns it
    python3 run.py test       run the unit tests
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cellos  # noqa: E402
from cellos.app import server  # noqa: E402
from cellos.kernel import db, events, relationships, routing  # noqa: E402

HOST = os.environ.get("CELLOS_HOST", "127.0.0.1")
PORT = int(os.environ.get("CELLOS_PORT", "8420"))


def cmd_serve():
    cellos.boot()
    try:
        httpd = server.serve(HOST, PORT)
    except OSError as e:
        if e.errno != 98:
            raise
        print("Something is already listening on port %d." % PORT)
        print("Either it is CellOS already running -- open http://%s:%d --" % (HOST, PORT))
        print("or stop it, or start this one elsewhere:  CELLOS_PORT=8421 python3 run.py")
        sys.exit(1)
    print("CellOS %s on http://%s:%d" % (cellos.__version__, HOST, PORT))
    print("database: %s" % db.DB_PATH)
    if not db.value("SELECT count(*) FROM events", default=0):
        print("the log is empty -- `python3 run.py seed` if you want something to look at")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()


def cmd_students():
    """Eight students and one assignment: the small end, where most groups live."""
    cmd_reset()
    cellos.boot()
    from assignment import build, report

    report(*build())
    print()
    sys.stdout.flush()
    cmd_serve()


def cmd_rebuild():
    """
    Proof that the log is the only thing that matters: drop every projection
    and reconstruct all current state -- including the relationship graph --
    from the events alone.
    """
    cellos.boot()
    print("replayed %d events" % events.replay())


def cmd_seed():
    cellos.boot()
    from seed import seed

    seed()


def cmd_demo():
    """
    Wipe, build three organisations at 200, 100 and 30 people, and serve.
    One command, so there is something real to click on immediately.
    """
    cmd_reset()
    cellos.boot()
    from demo import build, report

    print("building three organisations...")
    report(build())
    print()
    # The server blocks from here, so make sure the banner is on screen first
    # even when the output is piped rather than going to a terminal.
    sys.stdout.flush()
    cmd_serve()


def cmd_reset():
    for suffix in ("", "-wal", "-shm"):
        path = db.DB_PATH + suffix
        if os.path.exists(path):
            os.remove(path)
    print("deleted %s" % db.DB_PATH)


def cmd_routes():
    cellos.boot()
    for method, pattern in routing.table():
        print("  %-6s %s" % (method, pattern))
    print("\nrelationship kinds:")
    for name, spec in sorted(relationships.kinds().items()):
        print("  %-10s %s -> %s   %s"
              % (name, "|".join(spec.tail), "|".join(spec.head), spec.description))


def cmd_test():
    import tempfile
    import unittest

    # Tests get their own database. They must never touch the real one.
    db.use(os.path.join(tempfile.mkdtemp(prefix="cellos-test-"), "test.db"))
    cellos.boot()
    loader = unittest.TestLoader()
    suite = loader.discover("tests", top_level_dir=".")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


COMMANDS = {
    "serve": cmd_serve, "seed": cmd_seed, "demo": cmd_demo, "students": cmd_students,
    "rebuild": cmd_rebuild, "reset": cmd_reset, "routes": cmd_routes, "test": cmd_test,
}

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "serve"
    if name not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[name]()
