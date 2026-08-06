# Versions

Every milestone leaves a trace you can go back to. A milestone is a **tag** on
a commit where the whole thing was verified green — not a snapshot of
work-in-progress.

---

## v1 — the first version

*Phases 1–4 complete, plus the Phase 5 design paper.*

The recursive Cell model, event sourcing, the workflow engine, typed
relationships, governance by headcount, the responsibility layer, the
structural map, the derived health layer, and optional constraints.

Verified at the moment it was tagged:

```
183 unit tests          pass   (including tests of the architecture itself)
 76 end-to-end checks   pass
1470 events             replay to byte-identical projections
```

What is in it, in one line each:

| | |
|---|---|
| **Kernel** | storage, the event log, the relationship graph, the workflow engine, the route table |
| **Domains** | member, cell, hierarchy, governance, permission, decision, task, progress, evidence, constraints, responsibility, health, dashboard |
| **Recursion** | no depth limit anywhere; a task that outgrows one person expands into a cell whose mission it becomes |
| **Interface** | one page, ES modules, no build step; a structural map with unlimited depth, fetched a ring at a time |
| **Paper** | `MEASUREMENT.md` — what is worth measuring in a Cell, and why Potential belongs to the Genome rather than to Health |

Known gaps at this version are listed at the end of `HANDOFF.md`. The largest
is that **a Cell cannot end** — which `MEASUREMENT.md` §8 identifies as the
precondition for the Organizational Genome ever starting.

---

## v2 — the version you can live in

*No new domain. The system learned to be looked at every day.*

v1 proved the model. v2 is about what happens after the tenth time you open a
cell: the page stopped weighting everything the same, learned what a cell has
committed to, and let a person choose the light they read it in.

Verified at the moment it was tagged:

```
195 unit tests          pass   (12 more than v1, all on constraints)
 76 end-to-end checks   pass
1673 events             replay to byte-identical projections (12 tables)
```

What v2 added, in one line each:

| | |
|---|---|
| **Constraints on a cell** | a cell may commit to a date as quietly as it commits to a budget — optional everywhere, enforced nowhere, and a child due after its parent is said out loud rather than blocked |
| **One control for a commitment** | `···` wherever something has a date or a cost; it shows what is there and edits it in place, on a cell and on a task alike |
| **Weight by whether you act** | people, answered questions and the record step back; open questions, tasks, yours and inside stay forward |
| **Health as a dot** | one circle beside the goal, coloured by the verdict, saying all of itself on hover, focus or tap |
| **People that scale** | eight names is a group you know; thirty is a number and whoever leads |
| **A theme choice** | auto, light or dark, resolved before first paint, with one palette and no duplicate colours |

The domain model is unchanged from v1 apart from two optional columns. Every
number on the page is still derived and still never stored.

Known gaps are unchanged and still listed at the end of `HANDOFF.md`: **a Cell
cannot end**, and the health arithmetic is still the flawed Phase 4 version
that `MEASUREMENT.md` was written to replace.

---

## v3 — the version that was used

*The first one strangers drove, and the first one to be fixed by what they
found.*

v1 proved the model, v2 made it liveable. v3 is what happened when fifteen
people who had never seen it were given accounts and a real question to
settle — ten on a battery chemistry for a grid prototype, five on replacing
Wise for multi-currency accounts. They settled both, and on the way they
found four places where the system broke its own rules.

Verified at the moment it was tagged:

```
212 unit tests          pass   (17 more than v2, all on what the use exposed)
 76 end-to-end checks   pass
1964 events             replay to byte-identical projections (12 tables)
```

**What the use found, and what was fixed:**

| | |
|---|---|
| **Work could be silently taken** | three people had "taken" the same task in turn, each displacing the last, and two believed it was theirs. `assign` never looked at whether anybody was holding it. Unheld work is still free to pick up; taking it out of somebody's hands is a leader's call, and the refusal names them. |
| **Voting was never offered** | it is not a state change, so it was not a transition, so it never appeared in `actions` — leaving the commonest action in the system as the one thing the server did not mention. A decision now says `can_vote`. |
| **Ratifying a vote recorded no reason** | the cheapest way to close a question was the only silent one. It now records the count, which *is* the reason. |
| **An error described a rule nobody was applying** | a goal refused for being "an essay" by a check that counts characters. |

**What was built:**

| | |
|---|---|
| **A page per task** | why it exists — traced to the decision that produced it — who is expected to do what, what it grew into, and evidence, which could never be attached to work before because there was no page to do it on. Opens in its own tab. `GET /api/tasks/<id>` did not exist until somebody using the API said so. |
| **A page per person** | `#yours` asks "what is on me" of every cell at once, instead of once per cell and half an answer each time. |
| **What has happened** | derived from the log — events other people caused, touching your work. No table, no unread flag, no badge. This reverses Phase 2's "no notifications" without building one. |
| **The map, given a page** | it grows into the window up to twice size, then scrolls. |
| **A visual grammar** | ◎ gold for a cell, ○ metal for a task, on rows and page titles alike; the goal in a serif, because it is the one piece of writing on a page of interface. |
| **A calmer page** | health is a dot on the pulse line; what is settled, known and recorded sits behind one word. |

The domain model is unchanged again. Every number is still derived and still
never stored.

Known gaps: **a Cell cannot end**, the Phase 4 health arithmetic is still the
one `MEASUREMENT.md` was written to replace, and three things the users hit
are not fixed — every write still answers with the whole cell (a 34KB reply
to a one-line remark broke one person's tooling), nothing can say "this work
is waiting on that question", and duplicate work is neither detected nor
removable.

---

## Going back

```bash
git tag                          # every milestone
git show v3 --stat               # what a milestone contains
git diff --stat v2 v3            # what one milestone changed from the last
```

**To look at a version without changing anything:**

```bash
git checkout v3                  # detached; look around freely
git switch -                     # come back
```

**To work from an old version:**

```bash
git switch -c from-v3 v3         # a branch starting there
```

**To bring back one file:**

```bash
git restore --source=v1 -- cellos/domains/health/rules.py
```

**To throw away everything since a version:**

```bash
git reset --hard v1              # destroys uncommitted work — check `git status` first
```

The database is not tracked, and does not need to be: every state it can hold
is regenerated by `run.py seed`, `run.py demo` or `run.py students`. Going back
a version never loses data, because the data was never in the version.

---

## Making the next one

A tag is a claim that the tree was working. Earn it before making it:

```bash
python3 run.py test              # must pass
python3 run.py &                 # then, against it:
python3 smoke.py                 # must pass
python3 run.py rebuild           # drops every projection and replays the log
```

`rebuild` prints how many events it replayed; it does not check the result.
To claim the projections came back identical, fingerprint them either side of
it — hash every table's rows in a fixed order before and after, and diff the
two. A single differing hash means a projector is not a pure function of the
log, which is the one invariant the whole design rests on.

Then:

```bash
git add -A
git commit -m "what changed, and why"
git tag -a v4 -m "v4 — <the milestone in one line>

<what it added>
<the verification numbers at the moment of tagging>"
```

Add a section to this file in the same shape as v1 above. The numbers matter:
a version that does not record what passed is a version nobody can trust
later.
