# What is worth measuring in a Cell

**A design paper for Phase 5. No implementation.**

One question: *what are the fundamental measurable properties of a Cell that
remain true regardless of scale or mission?*

The short answer, argued below: **only the properties of the decision loop.**
Everything else CellOS could compute is either an assumption imported from
outside the event log, or a restatement of something the loop already says.

---

## 1. What went wrong in Phase 4

The Health layer began from *Potential → Friction → Capacity*. Three flaws,
demonstrable rather than arguable:

**Potential saturated.** Cells of 50, 100, 200 and 1,000 people all scored 60
out of 60. The metric could not distinguish a department from a corporation.

**Small cells were structurally punished.** A two-person cell had a potential
of 17, so three unclaimed tasks nearly zeroed it. A two-hundred-person cell
needed twelve. The same neglect produced wildly different verdicts, which
breaks the promise that a wedding and a company use the same concepts.

**Evidence outranked people.** Two people with seven attached links scored 57;
eight people with none scored 44. A pair who pasted some URLs read as more
capable than a team four times their size.

The root cause is not the weights. It is that `Capacity = Potential −
Friction` **looks like physics but subtracts two invented scales that happen
to share a range.** Both were 0–100 because I chose them to be. Nothing in the
system made them commensurable.

Underneath that is a deeper error: **CellOS was measuring capability, and it
records nothing about capability.** There are no skills, no hours, no
availability, no budgets-per-person in the event log. Any Potential formula is
therefore a set of assumptions wearing the costume of a derived value — which
violates the one rule the whole system rests on.

---

## 2. The thesis

> Stop modelling what a Cell *could* do. Measure how its decision loop
> actually turns.

CellOS is a Decision Operating System. The loop

```
Question → Evidence → Discussion → Decision → Execution → Knowledge → Question
```

is the only structure every Cell necessarily has. A wedding has it. A
research team has it. A government has it. A cell of one has it. Nothing else
in the system is universal: budgets are optional, votes appear only above five
people, child cells only above twenty, evidence is optional everywhere by
design.

So the universal measurable properties of a Cell are the properties of that
loop, and nothing else qualifies.

This also resolves the capability problem without solving it. **A Cell's
demonstrated capability is the rate at which it actually closes loops.** That
is observed, not modelled — and it is the only honest answer available from an
event log.

---

## 3. The unit of analysis is the question, not the Cell

Every metric below is defined per **question** and aggregated to the Cell.
This matters:

- A question has a birth (`DecisionCreated`) and a death (`KnowledgeRecorded`
  or `DecisionRejected`), so it has a measurable lifetime.
- Every stage transition is already an event with an actor and a timestamp.
- Cell metrics are then aggregations, and parent Cells aggregate over their
  subtree exactly as progress already rolls up.

Verified against the running system: for a single settled question the log
yields the full ordered trace —

```
DecisionCreated → DecisionOpened → RemarkAdded → VotingOpened
→ VoteSubmitted ×7 → DecisionAccepted → ExecutionStarted
→ ExecutionCompleted → KnowledgeRecorded
```

Every stage boundary is reconstructible. No new event type is required for
anything proposed in this paper.

---

## 4. The mathematical spine

Treat each Cell's loop as a queueing system. Questions arrive, dwell, depart.

**Little's Law** applies: for any stable queue, regardless of arrival
distribution, service order, or what is being queued,

```
L = λ · W

  L  questions in flight (open questions)
  λ  arrival rate        (questions raised per unit time)
  W  circulation time    (time from raised to closed)
```

This matters for three reasons.

**It is a theorem, not a heuristic.** It holds for a wedding and for a
parliament, which is precisely the universality the brief demands. No constant
is chosen by anyone.

**It settles independence mathematically.** Of `L`, `λ` and `W`, only two are
free. So reporting all three is reporting a redundancy — the sort of thing
question 4 of the brief's test is designed to catch.

**It separates demand from health.** `λ` is *exogenous*: how many questions
the world throws at a Cell is not a property of the Cell. `W` is *endogenous*:
how long the Cell takes is. Backlog `L` is then a consequence of both. Phase 4
conflated these, which is why a busy healthy cell read as sick.

---

## 5. The candidate metrics, tested

Each is put through the brief's five questions. Those that fail are cut.

### M1 · Circulation time — `W`

Time from a question being raised to its loop closing.

| test | answer |
|---|---|
| Real property? | How long this group takes to turn a question into a settled, executed, learned-from answer. |
| Universal? | Yes. Every Cell answers questions; all have clocks. |
| Derivable? | Yes. `DecisionCreated.occurred_at` → terminal event. |
| Independent? | Yes — one free variable of Little's Law. |
| Improves decisions? | **Only when read with M3.** Alone it rewards haste. |

Reported as a distribution, not a mean: the median says what is typical, the
tail says what is stuck. Per-stage dwell times decompose it, which is what
turns a number into a cause.

### M2 · Closure — the fraction of questions that reach a terminal state

| test | answer |
|---|---|
| Real property? | Whether the group finishes what it starts asking. |
| Universal? | Yes. |
| Derivable? | Yes. |
| Independent? | Yes — a Cell can be fast and abandon everything. |
| Improves decisions? | Yes. Unclosed questions are decisions the organisation has silently made by default. |

This is the metric Phase 4 lacked entirely, and it is arguably the most
important one. An organisation drowning in half-asked questions is failing in
a way no progress bar shows.

### M3 · Rework — the fraction of loops that go backwards

Already in the log: `DecisionReturned`, `ExecutionResumed`, `TaskReopened`,
and a question re-raised on a subject already settled.

| test | answer |
|---|---|
| Real property? | How often the group has to redo a step it believed finished. |
| Universal? | Yes. |
| Derivable? | Yes, directly — these are named events. |
| Independent? | Yes. |
| Improves decisions? | Yes, **and it is the counterweight that makes M1 safe to optimise.** |

M1 and M3 must always be shown together. Speed without rework is competence;
speed with rework is thrashing. Neither number means anything alone.

### M4 · Grounding — what a decision was settled against

The fraction of settled questions that had evidence attached, or discussion,
before acceptance.

| test | answer |
|---|---|
| Real property? | Whether decisions rest on anything a person could point at. |
| Universal? | The *property* is. The **expected level is not.** |
| Derivable? | Yes. |
| Independent? | Yes. |
| Improves decisions? | Close to definitional. |

**This one needs care.** The constitution says evidence is optional
everywhere, and two people choosing a caterer owe nobody a citation. So
grounding must be **reported against stakes, never banded against a
constant**. A usable stakes proxy already exists in the log: how many people
took part, and how much work the answer generated. A question that eight
people voted on and that produced six tasks, settled against nothing, is worth
saying out loud. The same question in a cell of two is not.

### M5 · Distribution — where the deciding actually happens

Share of settled questions resolved by the single most frequent decider;
share of eligible people who took part; override rate.

| test | answer |
|---|---|
| Real property? | Whether the loop runs through the group or through one person. |
| Universal? | Yes as a measurement. |
| Derivable? | Yes. |
| Independent? | Yes. |
| Improves decisions? | **Not monotonically — so this is descriptive, not a health input.** |

Concentration is correct in a cell of two and dangerous in a cell of two
hundred. Any threshold would be a smuggled assumption about scale. Report it;
never score it. What *is* meaningful without a constant is its **change**: a
Cell whose deciding is concentrating is telling you something regardless of
where it started.

---

## 6. What is cut, and why

**Potential, as a first-principles metric inside one Cell** — fails test 3
outright. A single Cell's log records nothing about capability, so any formula
is imported assumption. It also fails test 5: raising a hardcoded Potential
score does not improve anybody's decisions.

This is a verdict about *where the quantity can live*, not about whether it is
real. Potential is not deleted; it is **relocated and reclassified** — see §8.
Within a Cell, its place is taken by observed closure rate, which is measured
capability rather than modelled capability.

**Capacity as `Potential − Friction`** — fails test 1. It represents no real
property; it is arithmetic on two invented scales. *Replaced by:* nothing. The
gap it was filling was not real.

**A single Health score on an absolute band** — fails test 2. Every threshold
("75 is excellent") is a scale- or mission-dependent constant. *Replaced by:*
see §7.

**Friction as a number** — fails test 4. Friction is not independent of the
others; it is the *cause* of high `W` and high rework. Demoting it from metric
to explanation loses nothing and removes a fake quantity. **The Attention list
survives untouched** — it was always the useful half, and it becomes the
explanation attached to M1 and M3 rather than a score in its own right.

**Momentum as a separate concept** — subsumed. It is the time derivative of
M1–M4, not a fifth thing.

---

## 7. Health, redefined: comparison without constants

The deepest problem with Phase 4 was not any single weight. It was that a
banded score requires a universal constant, and no such constant exists across
weddings and governments.

**Proposal: every metric is compared to the Cell's own history, never to an
absolute.**

- *"This Cell is settling questions more slowly than it was"* is true and
  meaningful for a wedding and for a parliament.
- *"Latency under three days is good"* is true for a startup and absurd for a
  legislature.

Self-comparison needs no configuration, no threshold, and no mission model. It
is scale-free by construction rather than by careful weighting.

It is also the natural on-ramp to the Organizational Genome. Three stages, in
order of the evidence available:

1. **Now** — compare a Cell to its own past. Needs one Cell's history.
2. **Later** — compare a Cell to Cells with similar loop signatures. Needs a
   corpus.
3. **Eventually** — mission-specific capability models, *learned* from which
   loop shapes preceded good outcomes.

Stages 2 and 3 belong to a different layer, with a different epistemic status.
That separation is the subject of the next section.

---

## 8. Two layers, and the wall between them

The paper so far has answered *what can be measured inside one Cell*. That is
not the whole of what CellOS will eventually know, and the difference is not
one of maturity — it is a difference in **kind of knowledge**.

| | **Health** | **Genome** |
|---|---|---|
| scope | one Cell | many Cells, over time |
| input | that Cell's own event log | a corpus of closed Cells |
| output | **derived** quantities | **inferred** predictions |
| nature | deterministic, reproducible | probabilistic, carries `n` and spread |
| needs | nothing but the log | a corpus, and outcomes to learn from |
| answers | *how is this loop turning?* | *how have loops like this one turned out?* |
| voice | observation | suggestion |

Two words, used precisely from here on:

- **Derived** — computable from this Cell's own log. Deterministic. Survives
  `run.py rebuild`. Needs no other Cell to exist.
- **Inferred** — estimated from patterns across many Cells. Probabilistic.
  Meaningless without a sample size. Requires a corpus that may not exist yet.

**Health may only ever contain derived quantities. Genome may only ever
produce inferred ones.**

### Where Potential goes

Potential is an *inferred* quantity, and always was. That is why it could not
be made to work inside Health: it was being asked to be deterministic when its
nature is statistical.

Restated correctly:

> Potential cannot exist as a first-principles metric inside an individual
> Cell. It may later emerge as a learned property of the Organizational
> Genome — not a formula, but an empirical prediction: *Cells with comparable
> goals and comparable decision-loop signatures historically evolved this way.*

The difference is not cosmetic. A hardcoded Potential asserts a claim about
organisations that nobody verified. An inferred Potential reports a
correlation with a sample size attached, and can be wrong out loud.

### The rule that keeps them independent

The dependency arrow runs one way and **must never close into a cycle**:

```
domain facts ──► Health (one Cell, now) ──► interface
       │                  │
       │                  ▼  loop signatures
       └──────────────► Genome (many Cells, over time) ──► suggestions ──► interface
```

- Genome reads facts and reads Health's derived signatures across many Cells.
- **Health never reads Genome.** Nothing inferred may enter a Cell's own
  reading.

Three reasons that wall matters, in increasing order of seriousness:

1. **Reproducibility.** A Cell's Health must be recomputable from its own log
   alone. If a prediction entered it, `rebuild` would no longer reproduce it
   without also reproducing a trained model.
2. **Comparability.** A diagnosis that depends on other organisations' data is
   no longer a statement about this organisation.
3. **Entrenchment.** A Cell judged against a model trained on past Cells is
   judged against the past. The prediction becomes self-fulfilling, and the
   system quietly stops observing organisations and starts enforcing a norm —
   which is the exact opposite of *the software observes, the organisation
   decides.*

The interface may show both, and should keep them typographically and
grammatically distinct: Health states, Genome suggests. A reader must never
have to work out which kind of claim they are looking at.

### What the Genome needs that does not exist yet

Two prerequisites, both worth naming now because they change what should be
built earlier.

**Outcomes.** A corpus of *successful* Cells teaches nothing on its own —
without failures it cannot distinguish "this pattern caused success" from
"this pattern is common". Survivorship bias would be baked into the first
model trained. The Genome therefore needs Cells that ended, **including badly.**

**A way for a Cell to end.** CellOS currently has none: no archive, no
completion, no post-mortem, no `MemberLeft`. This was already on the known-gaps
list as an ordinary omission. It is now a **precondition for the Genome**, and
that reprioritises it: the corpus cannot begin accumulating until Cells can
close and say how they went.

### One thing the Genome must inherit

A trained model is a derived artifact, so it obeys the same discipline as
every projection in the system: **it must be reproducible from the corpus and
throwable away.** A model that cannot be retrained from the logs is a stored
value nobody can verify — the same error as a stored progress column, one
level up.

---

## 9. Honest limits

**Statistics need n.** With three closed questions, a median circulation time
is noise. The system should report counts beside every rate and **decline to
characterise a Cell below a minimum**, saying "not enough has happened yet"
rather than inventing a band. This is the same discipline as `momentum:
unknown` in Phase 4, applied everywhere.

**A Cell with no closed loop has no measurement.** Correct and worth stating
plainly. A new Cell is not unhealthy; it is unmeasured.

**Wall-clock time is the right unit and the seeds do not have it.** Verified:
every event in a generated dataset shares one timestamp, so `W` collapses to
zero. Real deployments have real clocks. Demonstration data will need
backdating, or a documented fallback to event-ordinal distance. This is a
fixture problem, not a model problem, but it will look like a model problem if
left unaddressed.

**Grounding is a proxy for reasoning quality, not a measure of it.** A link
attached to a decision proves someone attached a link. The system can measure
whether a decision was grounded *in anything*; it cannot measure whether the
reasoning was good. Overclaiming here would be the same mistake as Potential.

**Grouping Cells by mission is unsolved.** The Genome needs to know which
Cells are "like this one". Grouping by goal text needs semantics the system
does not have and will not have without dependencies. Grouping by *loop
signature* — the M1–M5 vector, scale band, structure shape — is derivable
today and mission-agnostic, which makes it the honest first attempt. Whether
loop shape alone is a good enough proxy for mission is an empirical question
that only a corpus can answer.

**Rework is not always failure.** A decision sent back because new evidence
arrived is the loop working. Rework should be counted and shown, never scored
as a defect on its own.

---

## 10. What this implies for implementation

Deliberately deferred until this model is agreed, but the shape:

- The architecture does not move. Health stays a derived domain that owns no
  table, depends on everything and is depended on by nothing.
- Each domain keeps contributing pure signals; those signals become the
  *explanations* attached to M1 and M3 rather than points on a scale.
- The new primitive is a **question trace** — the ordered events of one
  decision — from which every metric above is an aggregation.
- `health/rules.py` becomes statistics over traces rather than weighted sums,
  and the arbitrary constants disappear. The one place judgement remains is
  the minimum-`n` threshold, which is a statistical choice rather than an
  organisational one.
- The Genome, when it comes, is a **separate domain that Health does not
  import** — enforceable by the same boundary test that already asserts
  nothing imports Health. The rule to add is: `health` must not import
  `genome`, and neither may write to the other.
- Before any of that: Cells need a way to end, and to record how they went.
  Without it there is no corpus, and without a corpus the Genome is a
  hardcoded formula wearing a new name.

---

## 11. The answer, stated plainly

The fundamental measurable properties of a Cell, true at every scale and for
every mission, are the properties of its decision loop:

| | property | what it asks |
|---|---|---|
| **M1** | Circulation time | How long does a question take to become an answer? |
| **M2** | Closure | Do questions get finished, or abandoned? |
| **M3** | Rework | How often does the loop run backwards? |
| **M4** | Grounding | Is anything behind the answers? |
| **M5** | Distribution | Where does the deciding happen? *(descriptive)* |

`λ` (demand) is recorded but is not a property of the Cell. `L` (backlog)
follows from `λ` and `W` by Little's Law and is shown as load, not health.

Everything else a **single Cell** can compute is either downstream of these, or
an assumption its own event log cannot support.

That last clause is the boundary of this paper, not the boundary of CellOS.
Properties that no single Cell can derive are not thereby unreal — they are
**inferred rather than derived**, and they belong to the Genome, which learns
across many Cells and speaks in predictions rather than measurements. Potential
is the first of these. The two layers stay independent, and the arrow between
them never reverses.
