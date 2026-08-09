# CellOS

A decision and execution operating system. One group of people, one goal, and
a record of why every important thing was done that way.

Python standard library only. No dependencies, no build step, no network
install. It runs on the machine it is on.

```bash
python3 run.py seed && python3 run.py
```

Then open <http://127.0.0.1:8420> and sign in as `sara@example.org` (a wedding,
two people), `bahaeddin889@gmail.com` (a company, 211) or `nari@gmail.com` (a
hotel wedding, 23 people across thirteen cells). There is no password.

| command | what it does |
| --- | --- |
| `python3 run.py` | serve on 127.0.0.1:8420 |
| `python3 run.py seed` | five cells at five scales, the hotel wedding among them |
| `python3 run.py rebuild` | drop every projection and replay the log |
| `python3 run.py reset` | delete the database |
| `python3 run.py routes` | every endpoint and every relationship kind |
| `python3 run.py test` | 235 unit tests |
| `python3 smoke.py` | 90 end-to-end checks against a running server |

## Worked examples

The first three all build into the ordinary site on 8420 — a deployment has
one address, so anything meant to be reachable from one has to live there.
The rest take a database and a port of their own, so they can run alongside it
without touching it.

| | | |
| --- | --- | --- |
| `python3 run.py seed` | 8420 | five cells — 2, 6, 33, 211 and 23 people, where every difference between them is a consequence of headcount alone. This is what a deployment serves. |
| `python3 run.py students` | 8420 | eight students and one assignment |
| `python3 run.py demo` | 8420 | three organisations at 200, 100 and 30 |
| `python3 relax.py` | 8424 | Relax Confort — a real Algerian bedding shop run by seven people across seven cells |
| `python3 aures.py` | 8425 | a wedding in the Aurès — three days in a village, six hundred people, eleven cells |
| `python3 wedding.py` | 8426 | the same wedding at a hotel — cortège, traiteur, DJ, negafa, a drone, thirteen cells. Already inside `run.py seed`; this only gives it a port of its own. |

The last three are the ones to read if you want to see the model carry
something real. All three are built entirely by expansion: not one of their
cells was created, because each began too small to be allowed to, and every
cell in them grew out of a task that stopped fitting one person.

The two weddings are the same event run two ways, and the pair is the point.
One is a village, three days and six hundred people; the other is a hotel, one
evening and seventeen suppliers. Neither was configured differently. Both
ended up past twenty people without anyone deciding to, and both changed how
they settle a question when they got there.

## Shape

```
cellos/
  kernel/        knows nothing about cells
    db.py            connection, write lock, the two tables no domain owns
    events.py        the log: append, project, react, replay, units of work
    relationships.py typed edges with a registered kind per edge
    workflow.py      the state machine engine
    routing.py       the route table
    errors.py

  domains/       one package per part of the business
    member/      identity and membership
    cell/        the only container there is
    hierarchy/   containment, subtree, scale
    governance/  what a cell's size makes true
    permission/  responsibility, derived, in one place
    decision/    the lifecycle, declared
    task/        work, and work moving its decision along
    progress/    derived, owns no table
    evidence/    why we believe this is true
    dashboard/   derived, owns no table

  app/           composition and the HTTP server
web/             one page: index.html, app.css, js/ (ES modules, no build)
tests/           unit tests, including the architecture itself
```

A domain owns its `model` (the tables), `rules` (pure functions), `events`
(projectors), `service` (the public interface) and `api` (its endpoints). It
may read another domain through that domain's public accessors. It may not
write another domain's tables, and `tests/test_boundaries.py` fails the build
if it tries.

## The two ideas everything else hangs off

**The log is the only authority.** Every action appends one immutable event.
Every table -- including the relationship graph -- is a projection that can be
dropped and rebuilt from those events alone. `run.py rebuild` does exactly
that, and all ten tables come back byte-identical.

**Capabilities are a function of headcount.** `domains/governance/rules.py` is
the whole of it: at two people voting appears, at twenty child cells and a
leader who confirms, at fifty a dashboard, at two hundred analytics. There is
no settings screen because there is nothing to configure, and a cell that
shrinks gives capabilities back.

## The workflow engine

Every decision moves through one declared lifecycle:

```
draft → open → voting → leader resolution → accepted
                                               ↓
                             executing → completed → knowledge
```

`domains/decision/workflow.py` declares each arrow: which states it comes
from, what it emits, who may fire it, and what it needs from them. Nothing
else may move a decision. No service writes `state`, no endpoint accepts one,
and the interface has no branch that decides what comes next.

Three consequences worth knowing:

- **Transitions are atomic.** The engine reads the state, checks the
  transition, runs the guard and appends the event inside one held lock. Two
  people clicking Decide at the same instant get one 200 and one 409.
- **The server offers the actions.** `available()` returns the transitions
  this person could fire right now, with labels and the fields each needs. The
  browser renders that list and posts back a step name; it does not know what
  "resolve" means.
- **Execution is driven by work, not by clicks.** The task domain fires
  `begin_execution` when work is generated and `finish_execution` when the
  last of it is done. A decision cannot claim to be finished while its work is
  not.

## Typed relationships

Edges live in one table with a registered kind per edge, checked at every
write, rather than in foreign keys:

| kind | from → to | |
| --- | --- | --- |
| `contains` | cell → cell | one parent, many children |
| `produces` | decision → task | the work a decision generated |
| `supports` | evidence → decision \| task \| cell | why we believe this |

A new kind of connection needs a registration, not a migration. Two edges
named in the Phase 2 brief are deliberately not rows: a *progress update* is
an event, not an entity, and the log already records which task it belongs to;
an *outcome* is one-to-one with its decision and has no identity of its own.
Both are documented in `kernel/relationships.py` rather than silently skipped.

## What the interface does not do

`web/js/` is ES modules with no build step and no business logic. It renders
what the server sent and nothing else:

- Sections appear because the payload contains their key. A two-person cell is
  not sent an empty dashboard; it is not sent a dashboard.
- Buttons come from the workflow's `available()`.
- Forms are built from each transition's `asks` declaration, so the UI can
  render a step it has never heard of.
- Permission questions are answered by the server (`you.can_admit`,
  `you.can_create_child`), never re-derived, so the interface can never offer
  something the engine will refuse.

## Two things to know before this leaves your machine

**Authentication is a name and an email.** No passwords, no verification:
anyone who can reach the port can sign in as anyone. It binds to 127.0.0.1 for
that reason. `domains/member/service.py` is the only file that has to change.

**SQLite and in-process recursion set the ceiling.** Progress and subtree
queries recurse per cell on every read -- about 110 statements and 4ms for a
211-person cell. That will need caching, or a real database, well before the
ten thousand people in the long-term vision.

## Still missing

Named honestly, in rough priority order: nothing ever reaches anyone (no
notifications, no cross-cell inbox); nobody can leave a cell and nothing can be
archived; evidence of kind `file` stores a label, not a file; there are no due
dates anywhere; and nothing is paginated.
