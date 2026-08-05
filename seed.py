#!/usr/bin/env python3
"""
Four cells at four scales, so the same workflow can be watched changing shape.

    a wedding      2 people    no votes; one person decides and writes down why
    a beta launch  6 people    the cell votes, and the count decides
    a product      33 people   child cells appear, and a leader confirms the vote
    a company      211 people  a dashboard, then analytics

Nothing here configures anything. Every difference between these four cells is
a consequence of how many people are in them.

The seed drives the same workflow steps a browser would: it asks which
transitions are available and fires one by name, rather than calling a private
method the interface could not reach.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cellos  # noqa: E402
from cellos.kernel import db  # noqa: E402
from cellos.domains import permission  # noqa: E402
from cellos.domains.cell import service as cell_service  # noqa: E402
from cellos.domains.decision import model as dm, service as decision  # noqa: E402
from cellos.domains.evidence import service as evidence  # noqa: E402
from cellos.domains.governance import rules as governance  # noqa: E402
from cellos.domains.hierarchy import service as hierarchy  # noqa: E402
from cellos.domains.member import service as member  # noqa: E402
from cellos.domains.task import service as task  # noqa: E402

FIRST = ["Amina", "Bahaeddin", "Chloe", "Diego", "Eun-ji", "Farid", "Grace", "Hana", "Ibrahim",
         "Jonas", "Keiko", "Lars", "Mariam", "Noor", "Omar", "Priya", "Quentin", "Rania",
         "Sofia", "Tomas", "Ulrike", "Viktor", "Wren", "Xiulan", "Yusuf", "Zara"]
LAST = ["Adler", "Bakr", "Costa", "Duval", "Eriksen", "Faris", "Gomez", "Haddad", "Ivanov",
        "Jensen", "Khan", "Lindqvist", "Moreau", "Nakamura", "Okafor", "Petrov", "Rahman",
        "Silva", "Tanaka", "Ueda", "Varga", "Weber", "Yilmaz", "Zhou"]

_counter = [0]


def person(n):
    return ("%s %s" % (FIRST[n % len(FIRST)], LAST[(n // len(FIRST)) % len(LAST)]),
            "p%d@example.org" % n)


def fill(cell_id, admitter, count, role="member"):
    people = []
    for _ in range(count):
        _counter[0] += 1
        name, email = person(_counter[0])
        people.append(member.admit(admitter, cell_id, name, email, role))
    return people


def step(actor, decision_id, *preferred, **args):
    """Fire the first offered transition among `preferred`, as a client would."""
    d = decision.get(decision_id)
    offered = {a["name"] for a in decision.actions(actor["id"], d)}
    for name in preferred:
        if name in offered:
            return decision.act(actor["id"], decision_id, name, **args)
    raise RuntimeError(
        "none of %s available on a %s decision (offered: %s)"
        % (list(preferred), d["state"], sorted(offered))
    )


def doable(cell_id):
    """
    Work that is still one person's to do. A cell created inside this one is
    an expanded task, so it appears here too -- and it is not something anyone
    reports a percentage on any more.
    """
    return [t for t in task.in_cells([cell_id]) if t["state"] != "expanded"]


def carry_out(cell_id, people, percents):
    """Hand the generated work out and let people report on it."""
    for t, who, pct in zip(doable(cell_id), people, percents):
        task.assign(who["id"], t["id"], who["id"])
        if pct:
            task.report_progress(who["id"], t["id"], pct)


# --------------------------------------------------------------------------

def wedding():
    """Two people. No votes, no dashboard, no hierarchy -- and none missed."""
    sara = member.register("Sara Belkacem", "sara@example.org")
    c = cell_service.create(sara["id"], "Get married in September without losing our minds")
    omar = member.admit(sara["id"], c["id"], "Omar Belkacem", "omar@example.org")

    d = decision.propose(
        sara["id"], c["id"],
        "Where do we hold the ceremony?",
        "Both families travel either way. The question is really cost against how far people drive.",
        ["The garden venue outside town", "Her parents' house", "The old town hall"],
        work={"0": ["Put down the deposit", "Confirm the date with both families",
                    "Arrange parking for out-of-town guests"]},
    )
    step(sara, d["id"], "open")
    decision.remark(omar["id"], d["id"], "The hall is cheaper but nobody can park.")
    decision.remark(sara["id"], d["id"], "The garden holds 80. That is the whole list.")
    evidence.attach(sara["id"], "decision", d["id"], "measurement", "Guest list: 78 confirmed")
    evidence.attach(omar["id"], "decision", d["id"], "link", "Garden venue pricing",
                    "https://example.org/garden-venue")

    # Two people do not vote. One of them decides, and writes down why.
    options = dm.options_of(d["id"])
    step(sara, d["id"], "resolve", option_id=options[0]["id"],
         note="It fits everyone and we stop arguing about parking.")
    carry_out(c["id"], [sara, sara, omar], [100, 60, 0])
    return c


def beta_launch():
    """Six people. Big enough that agreement stops being obvious."""
    lead = member.register("Priya Raman", "priya@example.org")
    c = cell_service.create(lead["id"], "Get the beta in front of 100 real users by March")
    team = fill(c["id"], lead["id"], 5)

    d = decision.propose(
        lead["id"], c["id"],
        "Do we launch with the mobile app, or web only?",
        "Mobile is four weeks out. Web is ready now but half the interest came from phones.",
        ["Web only, launch in two weeks", "Wait for mobile, launch in six weeks",
         "Web now, mobile as a fast follow"],
        work={"2": ["Ship the web beta", "Open the waitlist", "Set up crash reporting",
                    "Write the mobile follow-up plan"]},
    )
    step(lead, d["id"], "open")
    decision.remark(team[0]["id"], d["id"], "Six weeks of silence will cost us the waitlist.")
    decision.remark(team[2]["id"], d["id"], "Fast follow only works if we actually staff it.")
    evidence.attach(team[1]["id"], "decision", d["id"], "report",
                    "Signup survey: 61% arrived from a phone")

    step(lead, d["id"], "put_to_cell")
    options = dm.options_of(d["id"])
    for who, choice in zip([lead] + team, [2, 2, 0, 2, 1, 2]):
        decision.vote(who["id"], d["id"], options[choice]["id"])
    # Six people are small enough to trust their own count. No leader step.
    step(lead, d["id"], "accept_by_vote")
    carry_out(c["id"], team, [100, 100, 45, 0])

    # An older decision that has already been all the way through.
    old = decision.propose(lead["id"], c["id"], "Which payment provider?", "",
                           ["Stripe", "Paddle"], work={"0": ["Integrate Stripe checkout"]})
    step(lead, old["id"], "open")
    step(lead, old["id"], "put_to_cell")
    old_options = dm.options_of(old["id"])
    for who in [lead] + team[:3]:
        decision.vote(who["id"], old["id"], old_options[0]["id"])
    step(lead, old["id"], "accept_by_vote")
    for t in doable(c["id"]):
        if decision.decision_of_task(t["id"]) == old["id"]:
            task.assign(lead["id"], t["id"], lead["id"])
            task.report_progress(lead["id"], t["id"], 100)
    step(lead, old["id"], "record",
         outcome="Live in nine days. Two disputes in the first month, both resolved.",
         lesson="We picked on integration speed and never checked payout timing. It cost us "
                "three weeks of cash flow. Check payout terms before integration effort.")
    return c


def product_org():
    """Thirty-three people. Child cells appear, and so does a leader's signature."""
    head = member.register("Mariam Diallo", "mariam@example.org")
    c = cell_service.create(head["id"], "Ship version 2 of the product this year")
    fill(c["id"], head["id"], 23)

    design = cell_service.create(head["id"], "Redesign the onboarding flow", c["id"])
    platform = cell_service.create(head["id"], "Move billing off the legacy service", c["id"])
    fill(design["id"], head["id"], 4)
    fill(platform["id"], head["id"], 5)

    d = decision.propose(
        head["id"], c["id"],
        "Do we rewrite the billing service or wrap it?",
        "The legacy service works. It is also the reason nobody can ship a price change.",
        ["Rewrite it properly", "Wrap it behind an interface and move on"],
        work={"0": ["Write the migration plan", "Freeze legacy schema changes",
                    "Stand up the new service", "Dual-write for one month"]},
    )
    step(head, d["id"], "open")
    decision.remark(head["id"], d["id"], "A wrapper leaves the pricing problem in place.")
    step(head, d["id"], "put_to_cell")

    options = dm.options_of(d["id"])
    people = member.members(c["id"])
    for i, m in enumerate(people[:14]):
        decision.vote(m["id"], d["id"], options[1 if i % 3 else 0]["id"])

    # Thirty people: the count no longer settles it on its own...
    step(head, d["id"], "send_to_leader")
    # ...and the person accountable overrules it, in writing, permanently.
    step(head, d["id"], "resolve", option_id=options[0]["id"],
         note="The vote is right about the risk and wrong about the horizon. A wrapper means "
              "we carry this for another two years. I am taking the schedule hit.")

    for i, t in enumerate(doable(c["id"])):
        owner = people[(i + 1) % len(people)]
        task.assign(head["id"], t["id"], owner["id"])
        task.report_progress(owner["id"], t["id"], [100, 70, 25, 0][i % 4])

    for sub in (design, platform):
        crew = member.members(sub["id"])
        lead = crew[0]
        sd = decision.propose(lead["id"], sub["id"], "What do we finish first?", "",
                              ["The highest-traffic path", "The loudest complaint"],
                              work={"0": ["Instrument the path", "Ship the first change"]})
        step(lead, sd["id"], "open")
        step(lead, sd["id"], "put_to_cell")
        sub_options = dm.options_of(sd["id"])
        for m in crew:
            decision.vote(m["id"], sd["id"], sub_options[0]["id"])
        # A five-person cell inside a thirty-three-person cell is still a
        # five-person cell: its own count settles this, with no leader step.
        step(lead, sd["id"], "accept_by_vote")
        for j, t in enumerate(doable(sub["id"])):
            o = crew[j % len(crew)]
            task.assign(head["id"], t["id"], o["id"])
            task.report_progress(o["id"], t["id"], [80, 30][j % 2])
    return c


def company():
    """Two hundred people. A dashboard, because nobody can see this by looking."""
    ceo = member.register("Bahaeddin Saoudi", "bahaeddin889@gmail.com")
    c = cell_service.create(ceo["id"], "Run Northwind")
    fill(c["id"], ceo["id"], 11, role=permission.LEADER)
    fill(c["id"], ceo["id"], 12)

    divisions = [
        ("Win the mid-market in Europe", 46),
        ("Keep the platform up and cheap", 38),
        ("Make support something people mention unprompted", 41),
        ("Hire 60 people without lowering the bar", 33),
        ("Get the new pricing model live", 29),
    ]
    for goal, size in divisions:
        sub = cell_service.create(ceo["id"], goal, c["id"])
        crew = fill(sub["id"], ceo["id"], size)
        lead = crew[0]
        member.set_role(ceo["id"], sub["id"], lead["id"], permission.LEADER)

        d = decision.propose(lead["id"], sub["id"], "Where does this quarter's effort go?", "",
                             ["Depth on what exists", "One new bet"],
                             work={"0": ["Pick the three things", "Cut everything else",
                                         "Report at six weeks"],
                                   "1": ["Scope the bet", "Staff it", "Set a kill date"]})
        step(lead, d["id"], "open")
        step(lead, d["id"], "put_to_cell")
        options = dm.options_of(d["id"])
        for i, m in enumerate(member.members(sub["id"])[:20]):
            decision.vote(m["id"], d["id"], options[0 if i % 3 else 1]["id"])
        evidence.attach(lead["id"], "decision", d["id"], "report",
                        "Last quarter's numbers for this group")
        step(lead, d["id"], "send_to_leader")
        step(lead, d["id"], "resolve", option_id=options[size % 2]["id"],
             note="Going with the count." if size % 2 == 0 else
                  "Against the vote: we have no room for a new bet this quarter.")

        for j, t in enumerate(doable(sub["id"])):
            owner = crew[(j * 7) % len(crew)]
            task.assign(lead["id"], t["id"], owner["id"])
            task.report_progress(owner["id"], t["id"], (size * (j + 3)) % 101)
    return c


def seed():
    if db.value("SELECT count(*) FROM cells", default=0):
        print("There is already something here. `python3 run.py reset` first if you meant to.")
        return

    for build in (wedding, beta_launch, product_org, company):
        c = build()
        n = hierarchy.scale(c["id"])
        caps = sorted(governance.capabilities(n) - set(governance.ALWAYS))
        print("%-52s %4d people   %s" % (c["goal"][:52], n, ", ".join(caps) or "nothing extra"))

    print("\n%d events, %d relationships"
          % (db.value("SELECT count(*) FROM events", default=0),
             db.value("SELECT count(*) FROM relationships", default=0)))
    print("sign in as any of these, no password:")
    print("  sara@example.org        the wedding")
    print("  priya@example.org       the beta launch")
    print("  mariam@example.org      the product org")
    print("  bahaeddin889@gmail.com  the company")


if __name__ == "__main__":
    cellos.boot()
    seed()
