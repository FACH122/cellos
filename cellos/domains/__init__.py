"""
The domains.

Each owns one part of the business and one part of the schema: its models, its
rules, its events, its services and its endpoints. A domain may read another
through that domain's public model or service; none of them writes another's
tables, and none of them knows what HTTP or HTML are.

Importing this package wires the system together, in a deliberate order:

  1. models      register the tables they own, before the database is created
  2. events      register projectors, without which a replay is incomplete
  3. services    register relationship kinds and workflows
  4. endpoints   register routes
  5. wiring      the few cross-domain registrations, kept visible in one place

Import this before `db.init()` or `events.replay()`.
"""

# 1. Tables ------------------------------------------------------------------
from .member import model as _member_model      # noqa: F401,E402
from .cell import model as _cell_model          # noqa: F401,E402
from .decision import model as _decision_model  # noqa: F401,E402
from .task import model as _task_model          # noqa: F401,E402
from .evidence import model as _evidence_model  # noqa: F401,E402

# 2. Projectors --------------------------------------------------------------
from .member import events as _member_events      # noqa: F401,E402
from .cell import events as _cell_events          # noqa: F401,E402
from .decision import events as _decision_events  # noqa: F401,E402
from .task import events as _task_events          # noqa: F401,E402

# 3. Relationship kinds, workflows, reactors ---------------------------------
from .hierarchy import service as hierarchy      # noqa: F401,E402  (contains)
from .governance import service as governance    # noqa: F401,E402
from . import permission                         # noqa: F401,E402
from .member import service as member            # noqa: F401,E402
from .cell import service as cell                # noqa: F401,E402
from .decision import service as decision        # noqa: F401,E402  (produces)
from .task import service as task                # noqa: F401,E402  (reactors)
from .progress import service as progress        # noqa: F401,E402
from .constraints import service as constraints  # noqa: F401,E402  (budgets, deadlines)
from .evidence import service as evidence        # noqa: F401,E402  (supports)
from .responsibility import service as responsibility  # noqa: F401,E402
from .health import service as health          # noqa: F401,E402  (reads everything, owns nothing)
from .dashboard import service as dashboard      # noqa: F401,E402

# 4. Endpoints ---------------------------------------------------------------
from .member import api as _member_api        # noqa: F401,E402
from .cell import api as _cell_api            # noqa: F401,E402
from .decision import api as _decision_api    # noqa: F401,E402
from .task import api as _task_api            # noqa: F401,E402
from .evidence import api as _evidence_api    # noqa: F401,E402
from .dashboard import api as _dashboard_api  # noqa: F401,E402
from .health import api as _health_api        # noqa: F401,E402

# 5. Wiring ------------------------------------------------------------------
# Evidence does not know what a decision or a task is. Each domain says how to
# find the cell one of its entities lives in, and that is the whole coupling.
evidence.register_subject("decision", lambda i: (_decision_model.get(i) or {}).get("cell_id"))
evidence.register_subject(
    "option", lambda i: (_decision_model.get((_decision_model.option(i) or {}).get("decision_id"))
                         or {}).get("cell_id"))
evidence.register_subject("task", lambda i: (_task_model.get(i) or {}).get("cell_id"))
evidence.register_subject("cell", lambda i: i if _cell_model.exists(i) else None)
