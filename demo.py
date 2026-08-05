#!/usr/bin/env python3
"""
Three organisations to poke at: 200, 100 and 30 people.

    Northwind          200   analytics, dashboard, child cells, leader confirms
    The second campus  100   dashboard, child cells, leader confirms -- no analytics
    Version two         30   child cells and leader confirms -- no dashboard

The three sizes are chosen to straddle the thresholds, so the same screen can
be compared either side of each one. Nothing is configured to make them
differ; every difference is a consequence of headcount.

Each org has real material in it: questions still open and waiting on a vote,
questions a leader overruled in writing, work nobody has taken, work taken and
not started, evidence, recorded outcomes, and cells that grew out of work that
was too large for one person.

    python3 run.py demo
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cellos.domains import permission  # noqa: E402
from cellos.domains.cell import service as cell_service  # noqa: E402
from cellos.domains.decision import model as dm, service as decision  # noqa: E402
from cellos.domains.evidence import service as evidence  # noqa: E402
from cellos.domains.governance import rules as governance  # noqa: E402
from cellos.domains.hierarchy import service as hierarchy  # noqa: E402
from cellos.domains.member import service as member  # noqa: E402
from cellos.domains.task import service as task  # noqa: E402

FIRST = ["Adnan", "Beatriz", "Chen", "Dorota", "Emeka", "Freya", "Goran", "Halima", "Ivan",
         "Jun", "Kamal", "Liv", "Marek", "Ngozi", "Otto", "Pia", "Rasmus", "Sanne", "Thabo",
         "Ursula", "Valentin", "Wanda", "Yosef", "Zofia", "Amira", "Bruno"]
LAST = ["Abbas", "Brandt", "Chowdhury", "Delgado", "Ekstrom", "Farrell", "Gruber", "Horvat",
        "Ito", "Jokinen", "Kaur", "Lindholm", "Mendes", "Nagy", "Osei", "Pavlov", "Quintero",
        "Rossi", "Sandhu", "Tamm"]

_n = [0]


def fill(cell_id, admitter, count, role="member"):
    people = []
    for _ in range(count):
        _n[0] += 1
        name = "%s %s" % (FIRST[_n[0] % len(FIRST)], LAST[(_n[0] // len(FIRST)) % len(LAST)])
        people.append(member.admit(admitter, cell_id, name, "d%d@example.org" % _n[0], role))
    return people


def step(actor, decision_id, *preferred, **args):
    """Fire the first offered transition, exactly as the browser would."""
    d = decision.get(decision_id)
    offered = {a["name"] for a in decision.actions(actor["id"], d)}
    for name in preferred:
        if name in offered:
            return decision.act(actor["id"], decision_id, name, **args)
    raise RuntimeError("none of %s on a %s decision (offered %s)"
                       % (list(preferred), d["state"], sorted(offered)))


def doable(cell_id):
    return [t for t in task.in_cells([cell_id]) if t["state"] != "expanded"]


def ask(lead, crew, cell_id, question, options, work, split=None, pick=0, note="",
        detail="", remark=None):
    """Raise a question, let the cell answer it, and settle it however its size says."""
    d = decision.propose(lead["id"], cell_id, question, detail, options, work)
    step(lead, d["id"], "open")
    if remark and len(crew) > 1:
        decision.remark(crew[1]["id"], d["id"], remark)

    if "put_to_cell" not in {a["name"] for a in decision.actions(lead["id"], decision.get(d["id"]))}:
        opts = dm.options_of(d["id"])
        step(lead, d["id"], "resolve", option_id=opts[pick]["id"], note=note or "Agreed.")
        return d

    step(lead, d["id"], "put_to_cell")
    opts = dm.options_of(d["id"])
    for i, m in enumerate(member.members(cell_id)[: sum(split or (6, 4))]):
        which = 0 if i < (split or (6, 4))[0] else 1
        decision.vote(m["id"], d["id"], opts[which]["id"])

    step(lead, d["id"], "send_to_leader", "accept_by_vote")
    if decision.get(d["id"])["state"] == "leader_resolution":
        step(lead, d["id"], "resolve", option_id=opts[pick]["id"], note=note or "Going with it.")
    return d


def work_on(cell_id, crew, percents, leader):
    """Hand the generated work out. Some of it is left untouched on purpose."""
    for t, pct in zip(doable(cell_id), percents):
        if pct is None:
            continue                      # nobody takes it -- shows as blocked
        owner = crew[(percents.index(pct) + 1) % len(crew)]
        task.assign(leader["id"], t["id"], owner["id"])
        if pct:
            task.report_progress(owner["id"], t["id"], pct)


# --------------------------------------------------------------------------

def northwind():
    """200 people. Analytics appears; five divisions, one of them nested deeper."""
    ceo = member.register("Halima Osei", "halima@example.org")
    top = cell_service.create(ceo["id"], "Run Northwind")
    fill(top["id"], ceo["id"], 4, role=permission.LEADER)
    fill(top["id"], ceo["id"], 17)

    divisions = [
        ("Win the mid-market in Europe", 35,
         ["Name the ten accounts", "Hire two more sellers", "Rewrite the pitch"]),
        ("Keep the platform up and cheap", 35,
         ["Cut the cloud bill in half", "Stop paging people at night"]),
        ("Make support worth mentioning", 35,
         ["Answer within an hour", "Fix the twenty recurring questions"]),
        ("Hire forty without lowering the bar", 35,
         ["Write the scorecards", "Train the interviewers", "Fix the first ninety days"]),
        ("Get pricing off the founder's spreadsheet", 35,
         ["Ship usage-based billing", "Migrate everyone onto it"]),
    ]

    for i, (goal, size, jobs) in enumerate(divisions):
        div = cell_service.create(ceo["id"], goal, top["id"])
        crew = fill(div["id"], ceo["id"], size)
        lead = crew[0]
        member.set_role(ceo["id"], div["id"], lead["id"], permission.LEADER)

        against = i % 2 == 0
        d = ask(lead, crew, div["id"], "Where does this quarter go?",
                ["Depth on what we already do", "One new bet"],
                {"0": jobs, "1": jobs[:1]},
                split=(6, 12) if against else (14, 4),
                pick=0,
                remark="We said the same thing last quarter and did not do it.",
                note=("Against the vote: we cannot afford a second bet while the first "
                      "is unfinished.") if against else "Going with the count.")
        evidence.attach(lead["id"], "decision", d["id"], "report",
                        "Last quarter's numbers for this group")

        work_on(div["id"], crew, [90, 40, None][: len(jobs)], lead)

        # One division splits a job that turned out to be a group's work.
        if i == 0:
            big = [t for t in doable(div["id"]) if t["owner_id"]][0]
            grown = task.expand(lead["id"], big["id"])
            inner = fill(grown["id"], lead["id"], 3)
            ask(crew[0], inner, grown["id"], "Which ten accounts?",
                ["The ones already talking to us", "The biggest logos"],
                {"0": ["Draw up the list", "Agree it with the sellers"]},
                split=(3, 1))
            work_on(grown["id"], inner, [60, 0], crew[0])

    # One question deliberately left open, waiting on the cell to answer.
    lead = member.members(top["id"])[0]
    d = decision.propose(ceo["id"], top["id"], "Do we open a second office next year?",
                         "The lease on this one ends in March.",
                         ["Yes, near the university", "No, stay remote"],
                         {"0": ["Find three sites", "Model the cost"]})
    step(ceo, d["id"], "open")
    step(ceo, d["id"], "put_to_cell")
    return top, ceo


def second_campus():
    """100 people. A dashboard, but no analytics -- below the 200 threshold."""
    head = member.register("Marek Delgado", "marek@example.org")
    top = cell_service.create(head["id"], "Open the second campus by autumn")
    fill(top["id"], head["id"], 3, role=permission.LEADER)
    fill(top["id"], head["id"], 16)

    parts = [
        ("Find and fit out the building", 20,
         ["Shortlist three sites", "Get the survey done", "Sign the lease"]),
        ("Hire the teaching staff", 20,
         ["Write the job specs", "Run the first round"]),
        ("Move the systems across", 20,
         ["Map what runs where", "Cut over out of hours"]),
        ("Tell everyone in the right order", 20,
         ["Draft the announcement", "Brief the existing staff"]),
    ]

    for i, (goal, size, jobs) in enumerate(parts):
        sub = cell_service.create(head["id"], goal, top["id"])
        crew = fill(sub["id"], head["id"], size)
        lead = crew[0]
        member.set_role(head["id"], sub["id"], lead["id"], permission.LEADER)

        d = ask(lead, crew, sub["id"], "How do we approach this?",
                ["Do it properly and slip a month", "Do the minimum and hit the date"],
                {"0": jobs, "1": jobs[:1]},
                split=(4, 12) if i == 0 else (13, 3), pick=0,
                remark="The date is the only thing anyone will remember.",
                note=("Against the vote: a building we cannot occupy in October is worse "
                      "than one we open in November.") if i == 0 else "Going with the count.")
        if i == 0:
            evidence.attach(lead["id"], "decision", d["id"], "measurement",
                            "What the last campus opening actually cost")
        work_on(sub["id"], crew, [100, 30, None][: len(jobs)], lead)

    return top, head


def version_two():
    """30 people. Child cells and a leader's signature -- no dashboard, no analytics."""
    head = member.register("Sanne Kaur", "sanne@example.org")
    top = cell_service.create(head["id"], "Ship version two this year")
    fill(top["id"], head["id"], 19)

    d = ask(head, member.members(top["id"]), top["id"],
            "Do we rewrite the billing service or wrap it?",
            ["Rewrite it properly", "Wrap it and move on"],
            {"0": ["Write the migration plan", "Freeze the legacy schema",
                   "Stand up the new service", "Dual-write for a month"]},
            split=(5, 9), pick=0,
            detail="The legacy service works. It is also why nobody can ship a price change.",
            remark="A wrapper leaves the pricing problem exactly where it is.",
            note="The vote is right about the risk and wrong about the horizon. A wrapper "
                 "means we carry this for another two years. I am taking the schedule hit.")
    evidence.attach(head["id"], "decision", d["id"], "link",
                    "The incident that started this", "https://example.org/incident-412")

    crew = member.members(top["id"])
    work_on(top["id"], crew, [100, 65, 0, None], head)

    # Two teams, each grown out of work that was too large for one person.
    for title in ("Redesign the onboarding flow", "Move billing off the legacy service"):
        t = task.create(head["id"], top["id"], title)
        grown = task.expand(head["id"], t["id"])
        people = fill(grown["id"], head["id"], 5)
        lead = people[0]
        member.set_role(head["id"], grown["id"], lead["id"], permission.LEADER)
        sd = ask(lead, people, grown["id"], "What do we finish first?",
                 ["The path most people hit", "The loudest complaint"],
                 {"0": ["Instrument the path", "Ship the first change"]},
                 split=(4, 1))
        work_on(grown["id"], people, [80, 20], lead)

    # Something already all the way through, so there is knowledge to read.
    old = ask(head, crew, top["id"], "Which payment provider?", ["Stripe", "Paddle"],
              {"0": ["Integrate Stripe checkout"]}, split=(10, 3))
    for t in doable(top["id"]):
        if decision.decision_of_task(t["id"]) == old["id"]:
            task.assign(head["id"], t["id"], head["id"])
            task.report_progress(head["id"], t["id"], 100)
    step(head, old["id"], "record",
         outcome="Live in nine days. Two disputes in the first month, both resolved.",
         lesson="We chose on integration speed and never checked payout timing. It cost "
                "three weeks of cash flow. Check payout terms before integration effort.")
    return top, head


# --------------------------------------------------------------------------

WANTED = {"Run Northwind": 200,
          "Open the second campus by autumn": 100,
          "Ship version two this year": 30}


def build():
    """
    The three sizes are the point of this file, so they are checked rather
    than hoped for: 200 sits on the analytics threshold, 100 between dashboard
    and analytics, 30 between child cells and dashboard.
    """
    made = []
    for fn in (northwind, second_campus, version_two):
        cell, owner = fn()
        got = hierarchy.scale(cell["id"])
        want = WANTED[cell["goal"]]
        if got != want:
            raise AssertionError("%s came out at %d people, not %d" % (cell["goal"], got, want))
        made.append((cell, owner))
    return made


def report(made):
    print()
    print("%-42s %6s  %-22s %s" % ("GOAL", "PEOPLE", "GOVERNANCE", "WHAT APPEARS"))
    for cell, owner in made:
        n = hierarchy.scale(cell["id"])
        caps = sorted(governance.capabilities(n) - set(governance.ALWAYS))
        print("%-42s %6d  %-22s %s"
              % (cell["goal"][:42], n, governance.model(n), ", ".join(caps)))
    print("\nsign in with any of these — there is no password:")
    for cell, owner in made:
        print("  %-24s leads %s" % (owner["email"], cell["goal"]))
    print("\nor as anyone else, e.g. d5@example.org, to see a plain member's view.")
