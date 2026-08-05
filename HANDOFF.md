# CellOS — handoff

Written for whoever picks this up next, human or model. It describes what
exists, how a request flows through it, and which rules must not be broken.
Everything here was generated from the running code, not from memory.

- **Stack:** Python 3 standard library only. No dependencies, no build step,
  no framework, no Node. SQLite + `http.server` + vanilla ES modules.
- **State:** Phase 4 complete — a derived health layer sits on top of Phase 3 — the model is recursive with no special cases,
  work expands rather than being replaced, and Responsibility is a first-class
  derived domain.

```bash
python3 run.py seed      # four cells at four scales
python3 run.py           # serve on 127.0.0.1:8420
python3 run.py test      # 183 unit tests
python3 smoke.py         # 76 end-to-end checks (server must be running)
python3 run.py demo      # three orgs at 200 / 100 / 30 people, then serve
python3 run.py students  # eight students and one assignment, then serve
python3 run.py rebuild   # drop all projections, replay the log
python3 run.py routes    # every endpoint + every relationship kind
```

---

## 0. The recursion, which is the whole model

```
Cell → holds Questions (internally: Decisions)
     → an accepted Question generates Tasks
     → a Task too large for one person expands into a Cell
     → that Cell repeats this exactly, forever
```

There is no depth limit and no second kind of cell. A cell forty levels down
returns the same payload shape as a root cell, subtree walks are done in
SQLite rather than Python recursion, and `CellCreated` is one event whether
the cell is a root or nested — where it sits is the `contains` relationship's
business.

**Expansion, not replacement.** A task that expands does not disappear and is
not copied. It becomes the *mission* of the new cell: same row, same id, same
evidence, same history, same origin decision. `responsibility.mission(cell_id)`
reads it back from where it always was. The task simply stops being counted as
one person's work, because its progress now comes up from a group.

## 1. What the product is

A group of people pursuing one goal is a **Cell**. That is the only container:
no organisations, no workspaces, no projects. A wedding and a company are the
same row.

Work begins as a **Decision**, which moves through one lifecycle and, once
accepted, turns itself into **Tasks**. Progress reported on those tasks rolls
upward through child cells. Accepted decisions eventually record an outcome
and become the organisation's **Knowledge**.

The single most important behaviour: **capabilities are a function of
headcount, not configuration.** There is no settings screen anywhere.

| people in a cell (itself + descendants) | what appears |
|---|---|
| 1 | tasks, decisions, evidence, knowledge |
| 5 | voting — the cell's count settles a decision |
| 20 | child cells, and a leader who confirms the vote and may overrule it |
| 50 | a dashboard over the child cells |
| 200 | analytics |

A cell that shrinks gives capabilities back. This lives in
`domains/governance/rules.py` and nowhere else.

---

## 2. Layout

```
cellos/
  kernel/            knows nothing about cells
    db.py              connection, write lock, tables no domain owns
    events.py          the log: append, project, react, replay, unit_of_work
    relationships.py   typed edges, one registered kind per edge
    workflow.py        the state machine engine
    routing.py         the route table
    errors.py          DomainError / NotAllowed / NotFound / Conflict

  domains/           one package per part of the business
    member/ cell/ hierarchy/ governance/ permission/
    decision/ task/ progress/ evidence/ constraints/ responsibility/ health/ dashboard/

  app/
    views.py           composes what one person should see
    server.py          http.server; static files + /api dispatch

web/                 index.html, app.css, js/ (ES modules, no build)
tests/               unit tests, including tests of the architecture itself
run.py seed.py smoke.py
```

Each domain contains some of: `model.py` (its tables + accessors),
`rules.py` (pure functions — no db, no events), `events.py` (projectors),
`service.py` (the public interface), `api.py` (its endpoints).

---

## 3. Request flow

```
browser  ──POST /api/decisions/<id>/steps/resolve──►  app/server.py
                                                       │  parse JSON, read Bearer token
                                                       ▼
                                              kernel/routing.match()
                                                       │  → the domain's handler
                                                       ▼
                                            domains/decision/api.py
                                                       │
                                                       ▼
                                          domains/decision/service.act()
                                              │ permission.require_member
                                              │ build ctx (standing + governance + tally)
                                              │ flow.can(...)  → 403 or 409 if not
                                              ▼
                                        kernel/workflow.fire()
                                          ┌── under db.write_lock ──────────┐
                                          │ read current state              │
                                          │ check transition is legal       │
                                          │ run guard  → payload            │
                                          │ append extra events (override)  │
                                          │ append the transition event     │
                                          └─────────────────────────────────┘
                                                       │  commit
                                                       ▼
                                        reactors run (task generation)
                                                       │
                                                       ▼
                                              app/views.cell()
                                                       │  the whole refreshed cell
                                                       ▼
browser  ◄────────────────── JSON ──────────────────────┘
```

Every mutation answers with the **entire refreshed cell**, so the interface
never has to work out what changed.

---

## 4. The event log is the only authority

Every action appends one immutable event. Every table — including the
relationship graph — is a projection that can be dropped and rebuilt from
those events alone. `run.py rebuild` does exactly that; all ten tables come
back byte-identical.

Three handler kinds attach to an event type:

- **projector** — restates the event as current state. Never appends. Runs on
  live writes *and* on replay.
- **reactor** — one domain answering another's event by appending its own
  (accepted decision → tasks). Runs on live writes **only**; on replay its
  output is already in the log.
- **listener** — read-only observation.

`events.unit_of_work()` groups several appends into one commit and is
reentrant. Reactors fire after the outermost commit.

### Event catalogue (28)

```
UserRegistered  MemberJoined  MemberRoleChanged
CellCreated  GoalRefined
DecisionCreated  DecisionOpened  VotingOpened  ResolutionRequested
VoteSubmitted  RemarkAdded
DecisionAccepted  LeaderOverride  DecisionReturned  DecisionRejected
ExecutionStarted  ExecutionCompleted  ExecutionResumed  KnowledgeRecorded
TaskCreated  TaskGenerated  TaskAssigned  ProgressUpdated
TaskCompleted  TaskReopened  TaskExpanded
BudgetSet  CellDeadlineSet  DeadlineSet  CostRecorded
EvidenceAttached  RelationshipFormed
```

`LeaderOverride` and `TaskPromoted` have deliberately empty projectors. They
exist so the permanent record can *name* an act rather than leave it to be
inferred; the state they imply is carried by the event beside them.

---

## 5. The workflow engine

`domains/decision/workflow.py` declares the lifecycle as data. **Nothing else
may move a decision.** No service writes `state`; no endpoint accepts one.

```
draft → open → voting → leader_resolution → accepted
                                               ↓
                             executing → completed → knowledge
                                            (rejected is terminal)
```

| step | from | to | event |
|---|---|---|---|
| `open` | draft | open | DecisionOpened |
| `put_to_cell` | draft, open | voting | VotingOpened |
| `ask_leader` | draft, open | leader_resolution | ResolutionRequested |
| `accept_by_vote` | voting | accepted | DecisionAccepted |
| `send_to_leader` | voting | leader_resolution | ResolutionRequested |
| `resolve` | draft, open, voting, leader_resolution | accepted | DecisionAccepted |
| `return` | voting, leader_resolution | open | DecisionReturned |
| `reject` | draft, open, voting, leader_resolution | rejected | DecisionRejected |
| `begin_execution` | accepted | executing | ExecutionStarted |
| `finish_execution` | executing | completed | ExecutionCompleted |
| `resume_execution` | completed | executing | ExecutionResumed |
| `record` | accepted, executing, completed | knowledge | KnowledgeRecorded |

Three properties that matter:

**Transitions are atomic.** Read, check, guard and append all happen inside
one held `db.write_lock`. Two people resolving the same decision at the same
instant get one `200` and one `409`. This was a real bug in Phase 1 — both
succeeded and the decision generated work for two contradicting options.

**The server offers the actions.** `flow.available(subject_id, ctx)` returns
the transitions this person could fire *right now*, each with a label and an
`asks` list describing the fields it needs. The browser renders that and posts
back a step name. It does not know what "resolve" means.

**Which steps exist depends on scale, not configuration.** The `requires`
callbacks read the cell's governance:

- alone → `resolve` directly, `put_to_cell` never offered
- 5–19 → `put_to_cell`, then `accept_by_vote` (the count decides)
- 20+ → `put_to_cell`, then `send_to_leader` (a leader signs, and may overrule)
- a tie always needs a person, at any size

The last three transitions are fired by the **task** domain, never by a
person: work starting makes a decision `executing`, the last task finishing
makes it `completed`.

---

## 6. Typed relationships

Edges live in one table with a registered kind, validated on every write,
instead of foreign keys. `kernel/relationships.py`.

| kind | from → to | notes |
|---|---|---|
| `contains` | cell → cell | one parent, many children |
| `produces` | decision → task | the work a decision generated |
| `supports` | evidence → decision \| task \| cell | why we believe this |
| `expands_into` | task → cell | work that outgrew one person; the cell's mission |

A new kind of connection needs a registration, not a migration. Rows are
projected from `RelationshipFormed` events like any other state.

Two edges are deliberately *not* rows, documented in the module: a **progress
update** is an event, not an entity (the log already records its task), and an
**outcome** is one-to-one with its decision with no identity of its own.

---

## 7. Public API of each domain

Call these; do not reach into another domain's tables.

### member — identity and membership
```
register(name, email)                         find or create a person
sign_in(name, email) -> (token, user)         no password; local only
sign_out(token) / user_for_token(token)
admit(actor_id, cell_id, name, email, role='member')
may_admit(actor_id, cell_id) -> bool          ask before offering
join(actor_id, cell_id, user_id, role)        used by cell.create
set_role(actor_id, cell_id, user_id, role)
members(cell_id)
```

### cell — the only container
```
create(actor_id, goal, parent_id=None)        parent needs the children capability
split_off_work(actor_id, goal, parent_id, leader_id=None)
                                              bypasses the headcount rule;
                                              only task.promote calls it
may_create_child(actor_id, parent_id) -> bool
refine_goal(actor_id, cell_id, goal)
get(cell_id)
```

### hierarchy — the shape, owns no table
```
parent_id / child_ids / children (cell_id)
subtree_ids(cell_id)    this cell and everything beneath
ancestor_ids(cell_id)   upward; for depth and cycle checks only
path(cell_id)           ordered root→cell, prune to what the reader may see
scale(cell_id)          distinct people in the subtree — drives everything
depth / check_placement / place_under / tree
```

### governance — what size makes true
```
capabilities(cell_id, scale=None) -> set
has(cell_id, capability, scale=None) -> bool
model(cell_id) -> 'informal' | 'vote_decides' | 'leader_confirms_vote'
votes(cell_id) -> bool
```
Pure versions in `governance/rules.py` take a headcount directly.

### permission — responsibility, one place
```
visible_cell_ids(user_id)     cells they belong to + everything beneath
home_cell_ids(user_id)        where their view starts
require_sight / require_member / require_leader(user_id, cell_id, action)
is_member / is_leader / can_see / membership
standing(user_id, cell_id)    role, is_member, acts_here, is_leader
allows(check, *args) -> bool  ask any requirement as a question
```

### decision — the lifecycle
```
propose(actor_id, cell_id, question, detail='', option_texts=None, work=None)
remark(actor_id, decision_id, body)
vote(actor_id, decision_id, option_id)
act(actor_id, decision_id, step, **args)      THE ONLY WAY STATE CHANGES
actions(actor_id, decision)                   what this person could do now
record(actor_id, decision_id)                 the whole decision, assembled
open_in(cell_id) / settled_in(cell_ids, limit)
tasks_of(decision_id) / decision_of_task(task_id)
advance_execution(actor_id, decision_id, step)  called by the task domain
```

### task — work
```
create(actor_id, cell_id, title, owner_id=None)
assign(actor_id, task_id, owner_id)             unheld work is free to take;
                                                work already in someone's hands
                                                moves only by a leader
report_progress(actor_id, task_id, progress)   0–100
promote(actor_id, task_id, goal=None)          "too large" → becomes a cell
may_promote(actor_id, task_id) -> bool
cell_it_became(task_id)
in_cells(cell_ids, owner_id=None, unfinished_only=False)
get(task_id)
```
State is **derived**, never stored: `promoted` if it became a cell, else
`done` at 100, else `active` if held, else `open`.

### progress — derived, owns no table
```
of_cell(cell_id)     recursive rollup, weighted by how much work each holds
of_tasks(tasks)      for one person's own list
```

### evidence — why we believe this
```
attach(actor_id, subject_kind, subject_id, kind, label, ref='')
supporting(subject_kind, subject_id)
used_in(cell_ids) -> bool
register_subject(kind, locate_cell)   a domain declaring evidence may attach
```

### dashboard — derived, owns no table
```
for_leader(user_id, cell_id)   one row per child: people, progress, open,
                               remaining, unowned, stalled
for_member(user_id, cell_id)   their work, progress, unclaimed, awaiting_you
metrics(cell_id)               people, cells, decisions, override_rate, ...
knowledge(cell_ids, limit)     decisions that recorded an outcome
```

---

## 8. HTTP endpoints

```
POST   /api/session                       sign in (public)
DELETE /api/session                       sign out
GET    /api/me

GET    /api/home                          cells this person belongs to
POST   /api/cells                         {goal, parent_id?}
GET    /api/cells/<id>                    the whole cell view
PATCH  /api/cells/<id>                    {goal}
GET    /api/cells/<id>/history            the permanent record
GET    /api/cells/<id>/children           one ring of the map, fetched on expand
GET    /api/cells/<id>/dashboard          leader or member shape
GET    /api/cells/<id>/health             potential, friction, capacity, momentum, attention

POST   /api/cells/<id>/members            {name, email, role?}
PATCH  /api/cells/<id>/members/<user_id>  {role}

POST   /api/cells/<id>/decisions          {question, detail?, options?, work?}
GET    /api/decisions/<id>
POST   /api/decisions/<id>/remarks        {body}
POST   /api/decisions/<id>/votes          {option_id}
POST   /api/decisions/<id>/steps/<step>   THE state-change endpoint

POST   /api/cells/<id>/tasks              {title, owner_id?}
PATCH  /api/tasks/<id>                    {owner_id?, progress?, due_on?, cost?}
PUT    /api/cells/<id>/commitments        {amount?, currency?, due_on?} — empty clears one
POST   /api/tasks/<id>/cell               {goal?}  — split off too-large work

POST   /api/evidence                      {subject_kind, subject_id, kind, label, ref?}
```

Errors: `400` DomainError · `403` NotAllowed · `404` NotFound ·
`409` Conflict (someone moved it first).

---

## 9. The cell view payload

`GET /api/cells/<id>` — always present:

```
cell {id, goal, created_at}   path[]        scale        capabilities[]
governance                    you{}         members[]    open_decisions[]
tasks[]                       progress{}    settled_decisions[]
```

Conditionally present — **a missing key is a section the UI cannot draw**:

| key | appears when |
|---|---|
| `structure` | the cell has children: the root and the ring inside it, each node carrying progress, attention, health and *why it exists*, plus `child_count`. Deeper rings are fetched on expand — **there is no maximum depth anywhere** |
| `analytics` | 200+ people |
| `yours` | you act here, cell ≥5, and you have work or a pending vote |
| `knowledge` | some decision in the subtree recorded an outcome |
| `evidence_in_use` | this part of the organisation has ever used evidence |
| `constraints` | the cell committed to a budget, or some work has a date. Absent when it committed to nothing |
| `health` | always — potential, friction, capacity, momentum, attention |

`you` carries `role, is_member, acts_here, is_leader, can_admit,
can_create_child`. Each decision carries `actions[]` from the workflow and
`position` / `lifecycle_length` for the progress rail. Each task carries
`state`, `can_split`, and `became_cell_id` when it grew into a cell.

---

## 10. Front-end flow

`web/js/` — ES modules, no build step, **no business logic**.

```
main.js      wiring; owns render(); holds scroll position across re-renders
store.js     S (the state), go(cellId), absorb(payload), form open/close
api.js       the only place that calls fetch
actions.js   click / change / submit delegation
dom.js       esc, plural, meter, toast
labels.js    state → English, event type → English (the only translation)
render/
  shell.js     sign-in, home, breadcrumbs
  cell.js      the sections, in order
  decision.js  a decision card, its options, and its actions
```

The loop: a click calls one `api.*` method → the server answers with the whole
refreshed cell → `absorb()` → `render()` rebuilds `#app` → scroll is restored.

**Rules the front end obeys:**
- A section renders because the payload has its key. Never `if (scale > 50)`.
- Buttons come from `decision.actions[]`.
- Forms are built from each action's `asks[]`, so the UI can render a step it
  has never heard of.
- Permission questions are answered by the server (`you.can_admit`,
  `task.can_split`) and never re-derived.

---

## 10a. The structural map

`Inside` is not a table. It is an SVG tree drawn by `web/js/render/structure.js`
from `responsibility.structure()`, and it encodes exactly two things per node:
the ring is progress, a warm dot on the rim means something below needs
attention. A third encoding would turn a picture you read at a glance into a
chart you have to study.

Each node also carries **why it exists** — the question whose answer produced
the work that expanded into it — which is in the node's `title`. Nothing else
in the system records that, which is why nothing else could draw this.

Two rules it obeys:

- **Structure that exists is always drawn**, at any headcount. Work can expand
  into a cell in a three-person team, so gating the picture on the twenty-person
  threshold would hide a real shape. The threshold gates only whether *starting*
  a group is offered.
- **Two levels deep.** Anything below is counted on the node (`+N inside`), not
  drawn, because a node-link diagram stops meaning anything past a few dozen
  circles.

## 10b. Health — the interpretation layer

    Potential  →  Friction  →  Effective Capacity  →  Momentum  →  Health

`domains/health/` owns no table, appends no event and is a source of truth for
nothing. It reads what other domains recorded, asks each of them what its own
objects are costing (`decision.rules.friction`, `task.rules.friction`,
`evidence.rules.friction` — all pure), and composes.

- **Potential** is optimistic by definition: people (with diminishing returns),
  what the cell has learned, what evidence it holds. It ignores every delay.
- **Friction** is the sum of the signals, capped at potential — a cell cannot
  lose more than it has.
- **Capacity** = potential − friction.
- **Momentum** compares two stretches of the cell's *own event history*, not
  the calendar, so a group that works in bursts is not called dying on a
  Tuesday. Too little history returns `unknown` rather than a guess.
- **Attention** is friction said in human words. It is what people actually
  see; the numbers sit behind one click.

The arrow points one way and `tests/test_boundaries.py` enforces it: nothing
imports health, and health writes nothing. The moment a domain acted on a
health number, that number would stop describing the organisation and start
steering it.

## 10c. Constraints — optional commitments

A cell may commit to a **budget** and a **date**; a task may commit to a
**date** and record a **cost**. All of them are optional everywhere and
required nowhere, like evidence. A cell that never set a budget is not a cell at 0% spent — it is a
cell the question does not apply to, and `constraints` is absent from its
payload entirely.

- **Spend is not stored.** It is the sum of what the work cost, rolled up
  through the child cells exactly the way progress is.
- **Nothing is enforced.** CellOS will not block a spend or refuse a late
  task. It notices, and says so, and the organisation decides — which is why
  these feed `health` as ordinary friction and get no special treatment for
  having been chosen deliberately.
- **Clearing is not zero.** Passing an empty value drops that commitment; the
  log still records that the cell once had one.
- **Contradictions are said, not blocked.** A task or child cell promised for
  later than the cell it sits inside is a pair of dates that cannot both hold.
  CellOS notices and says so; it refuses nothing.

## 11. Invariants — break these and the design is gone

1. **Only the workflow engine changes a decision's state.** No service writes
   `state`; no endpoint accepts one. `tests/test_boundaries.py` enforces it.
2. **No domain writes another domain's tables.** Same test file enforces it by
   parsing every INSERT/UPDATE/DELETE against the schema that declares it.
3. **`rules.py` modules stay pure** — no `db`, no `events`, no `model`. That is
   what makes the interesting logic testable as arithmetic.
4. **The kernel knows nothing about domains.**
5. **Nothing derivable is stored.** No cell-progress column, no task-state
   column, no dashboard totals. If you add one, `run.py rebuild` stops being
   proof of anything.
6. **A capability is a function of headcount alone.** If you find yourself
   adding a settings flag, the answer is a threshold in `governance/rules.py`.
7. **Health stays a diagnostic.** Nothing may depend on it, and it may never
   be stored, targeted or optimised against.
8. **Every event type needs a projector**, or `replay()` refuses to run rather
   than rebuild partially.

---

## 12. Verification

```
python3 run.py test      128 tests, ~0.2s   (incl. tests of the architecture)
python3 smoke.py          76 end-to-end checks against a running server
python3 run.py rebuild    replays the log; all 10 tables must be identical
```

`tests/test_boundaries.py` is unusual and worth keeping: it reads the source
and fails if the layering erodes.

---

## 13. Known gaps, in priority order

1. **Nothing ever reaches anyone.** No notifications, no cross-cell inbox. A
   decision sitting in `leader_resolution` waits forever unless someone opens
   that cell. The `yours` payload is the seed of the fix.
2. **Nobody can leave and nothing can end.** There is `MemberJoined` and no
   `MemberLeft`; no way to archive a cell, withdraw a draft decision, drop a
   task, or remove evidence added by mistake.
3. **Evidence of kind `file` stores a label, not a file.** No upload.
4. **Authentication is a name and an email.** No passwords, no verification —
   anyone who reaches the port can sign in as anyone. Binds to 127.0.0.1 for
   that reason. `domains/member/service.py` is the only file to change.
5. **Performance shape.** One view of a 300-person cell is ~7ms and ~203 SQL
   statements: recursion per cell, not a join. Fine now, wrong at thousands.
   The fix is a progress rollup cached and invalidated by task events.
6. **No time anywhere.** No due dates, no overdue. Deliberate — the
   constitution never asked for it — but it is the first thing a real user
   reaches for and does not find.
7. **Nothing is paginated.** Tasks, members and dashboards return everything.

---

## 14. If you are adding a feature

- New state change on an existing object → a `transition` in that domain's
  workflow. Never a new endpoint that sets a field.
- New kind of connection → `relationships.register(...)`. Never a new foreign
  key column.
- New rule → a pure function in that domain's `rules.py`, with a unit test.
- New thing the UI shows → a key in `app/views.py`, present only when it says
  something. Never a conditional in the JavaScript.
- New capability that should appear with size → a threshold in
  `governance/rules.py`. Never a settings flag.
