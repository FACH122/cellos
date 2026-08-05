#!/usr/bin/env python3
"""
Eight students and one assignment.

The small end of CellOS, and the tier most groups actually live in. Eight
people is past five, so the cell votes and its own count settles things --
there is no leader confirmation step, because at this size handing the answer
to one person would be ceremony. It is under twenty, so nobody is offered
"start a group": there is no structure to build yet.

But a piece of work can still turn out to be bigger than one person, and when
it does it expands into a cell exactly as it would in a company of two
hundred. That is the whole claim of the system, tested at eight people.

    python3 run.py students
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cellos.domains.cell import service as cell_service  # noqa: E402
from cellos.domains.decision import model as dm, service as decision  # noqa: E402
from cellos.domains.evidence import service as evidence  # noqa: E402
from cellos.domains.governance import rules as governance  # noqa: E402
from cellos.domains.hierarchy import service as hierarchy  # noqa: E402
from cellos.domains.member import service as member  # noqa: E402
from cellos.domains.progress import service as progress  # noqa: E402
from cellos.domains.task import service as task  # noqa: E402

STUDENTS = [
    ("Yasmine Toubal", "yasmine@uni.edu"),
    ("Deniz Aydin", "deniz@uni.edu"),
    ("Oscar Lindgren", "oscar@uni.edu"),
    ("Priya Nair", "priya@uni.edu"),
    ("Tom Whelan", "tom@uni.edu"),
    ("Aicha Diop", "aicha@uni.edu"),
    ("Kenji Mori", "kenji@uni.edu"),
    ("Lena Fischer", "lena@uni.edu"),
]


def step(actor, decision_id, *preferred, **args):
    d = decision.get(decision_id)
    offered = {a["name"] for a in decision.actions(actor["id"], d)}
    for name in preferred:
        if name in offered:
            return decision.act(actor["id"], decision_id, name, **args)
    raise RuntimeError("none of %s on a %s decision (offered %s)"
                       % (list(preferred), d["state"], sorted(offered)))


def doable(cell_id):
    return [t for t in task.in_cells([cell_id]) if t["state"] != "expanded"]


def build():
    # Yasmine starts it, so she leads. Nobody appointed her; she opened the tab.
    yasmine = member.register(*STUDENTS[0])
    group = cell_service.create(
        yasmine["id"], "Hand in the distributed systems assignment by 5 December")
    others = [member.admit(yasmine["id"], group["id"], name, email)
              for name, email in STUDENTS[1:]]
    deniz, oscar, priya, tom, aicha, kenji, lena = others
    everyone = [yasmine] + others

    evidence.attach(yasmine["id"], "cell", group["id"], "document",
                    "The assignment brief", "https://uni.edu/ds/assignment-3.pdf")

    # ---------------------------------------------------------------- one
    # Settled some weeks ago, and it has an outcome recorded. This is the
    # group's memory: what they tried, and what they would tell themselves.
    tooling = decision.propose(
        deniz["id"], group["id"],
        "Where do we keep the write-up?",
        "Last term half of us edited the wrong copy the night before.",
        ["One shared doc", "Everyone writes their own section, merge at the end"],
        {"0": ["Set the doc up and share it with everyone"]},
    )
    step(deniz, tooling["id"], "open")
    decision.remark(tom["id"], tooling["id"], "Merging at the end is how we lost a section last time.")
    step(deniz, tooling["id"], "put_to_cell")
    opts = dm.options_of(tooling["id"])
    for who in (yasmine, deniz, oscar, priya, tom, aicha):
        decision.vote(who["id"], tooling["id"], opts[0]["id"])
    decision.vote(kenji["id"], tooling["id"], opts[1]["id"])
    step(deniz, tooling["id"], "accept_by_vote")
    for t in doable(group["id"]):
        if decision.decision_of_task(t["id"]) == tooling["id"]:
            task.assign(deniz["id"], t["id"], deniz["id"])
            task.report_progress(deniz["id"], t["id"], 100)
    step(deniz, tooling["id"], "record",
         outcome="One doc, nobody lost anything. Two people edited the same paragraph "
                 "once and it took a minute to sort out.",
         lesson="Agreeing where the work lives before anyone starts writing is worth the "
                "ten minutes. Do it in the first meeting, not the week before.")

    # ---------------------------------------------------------------- two
    # The real question, settled by the count. Eight people is small enough
    # that the vote decides and nobody signs it off.
    what = decision.propose(
        yasmine["id"], group["id"],
        "What do we actually build?",
        "The brief says 'a distributed system demonstrating consensus'. That is "
        "anything from a toy to a term's work.",
        ["A small Raft implementation with a visualiser",
         "A key-value store on top of an existing Raft library",
         "A simulation with no real networking"],
        {"0": ["Write the literature review",
               "Implement leader election",
               "Implement log replication",
               "Build the visualiser",
               "Write the evaluation section",
               "Put the slides together"]},
    )
    step(yasmine, what["id"], "open")
    decision.remark(oscar["id"], what["id"],
                    "Raft from scratch is four weekends. I have two.")
    decision.remark(aicha["id"], what["id"],
                    "The visualiser is what gets us the marks though. The brief weights "
                    "the demo at 40%.")
    decision.remark(kenji["id"], what["id"], "I can do election if someone else does replication.")
    evidence.attach(aicha["id"], "decision", what["id"], "document",
                    "Marking rubric — demo is 40%", "https://uni.edu/ds/rubric.pdf")
    evidence.attach(oscar["id"], "decision", what["id"], "measurement",
                    "Last year's group spent 60 hours on a from-scratch Raft")

    step(yasmine, what["id"], "put_to_cell")
    opts = dm.options_of(what["id"])
    for who in (yasmine, aicha, kenji, priya, lena):
        decision.vote(who["id"], what["id"], opts[0]["id"])
    for who in (oscar, deniz):
        decision.vote(who["id"], what["id"], opts[1]["id"])
    decision.vote(tom["id"], what["id"], opts[2]["id"])
    # 5–2–1. Yasmine could overrule it — she leads — but at eight people the
    # count is the answer, so she closes it and takes what the group said.
    step(yasmine, what["id"], "accept_by_vote")

    # ------------------------------------------------------------- the work
    jobs = {t["title"]: t for t in doable(group["id"])}
    plan = [
        ("Implement leader election", kenji, 70),
        ("Implement log replication", priya, 45),
        ("Build the visualiser", aicha, 30),
        ("Write the evaluation section", lena, 0),   # taken, not started
        ("Put the slides together", None, None),     # nobody has taken it
    ]
    for title, who, pct in plan:
        t = jobs.get(title)
        if t is None or who is None:
            continue
        task.assign(who["id"], t["id"], who["id"])
        if pct:
            task.report_progress(who["id"], t["id"], pct)

    # --------------------------------------------------- work that outgrew one
    # The literature review turns out to be three people's job. It expands,
    # and everything already attached to it comes with it.
    review = jobs["Write the literature review"]
    task.assign(yasmine["id"], review["id"], oscar["id"])
    evidence.attach(oscar["id"], "task", review["id"], "note",
                    "Supervisor wants at least 15 sources, 5 of them post-2020")
    lit = task.expand(yasmine["id"], review["id"])

    for who in (deniz, tom):
        member.admit(oscar["id"], lit["id"], who["name"], who["email"])

    split = decision.propose(
        oscar["id"], lit["id"], "How do we split the reading?", "",
        ["By era — classical, then modern", "By theme — consensus, ordering, failure"],
        {"1": ["Consensus papers", "Ordering papers", "Failure-model papers",
               "Write it up as one voice"]},
    )
    step(oscar, split["id"], "open")
    decision.remark(deniz["id"], split["id"], "By theme, or the write-up reads like three essays.")
    step(oscar, split["id"], "put_to_cell", "resolve",
         option_id=dm.options_of(split["id"])[1]["id"], note="Reads better as one piece.")
    if decision.get(split["id"])["state"] == "voting":
        sopts = dm.options_of(split["id"])
        for who in (oscar, deniz, tom):
            decision.vote(who["id"], split["id"], sopts[1]["id"])
        step(oscar, split["id"], "accept_by_vote")

    inner = {t["title"]: t for t in doable(lit["id"])}
    for title, who, pct in [("Consensus papers", oscar, 100),
                            ("Ordering papers", deniz, 60),
                            ("Failure-model papers", tom, 20)]:
        t = inner.get(title)
        if t:
            task.assign(oscar["id"], t["id"], who["id"])
            task.report_progress(who["id"], t["id"], pct)

    # ------------------------------------------------- still to be answered
    # Left open on purpose: it is waiting on the group, and every one of them
    # will see it as "your answer" until they vote.
    presenting = decision.propose(
        lena["id"], group["id"],
        "Who presents on the 8th?",
        "Twenty minutes, two presenters, everyone has to answer questions.",
        ["Yasmine and Aicha", "Kenji and Priya", "Whoever has done the most by then"],
        {"0": ["Write the speaker notes", "Book a practice room"]},
    )
    step(lena, presenting["id"], "open")
    step(lena, presenting["id"], "put_to_cell")
    decision.vote(lena["id"], presenting["id"], dm.options_of(presenting["id"])[0]["id"])
    decision.vote(tom["id"], presenting["id"], dm.options_of(presenting["id"])[2]["id"])

    return group, yasmine, lit


def report(group, owner, lit):
    n = hierarchy.scale(group["id"])
    caps = sorted(governance.capabilities(n) - set(governance.ALWAYS))
    p = progress.of_cell(group["id"])

    print()
    print("%s" % group["goal"])
    print("  %d students · %d%% · governance: %s" % (n, p["percent"], governance.model(n)))
    print("  what appears at this size: %s" % ", ".join(caps))
    print("  what does not: child cells, a dashboard, analytics, leader confirmation")
    print()
    print("  inside it, because one job was too big for one person:")
    lp = progress.of_cell(lit["id"])
    print("    %s — %d people, %d%%" % (lit["goal"], hierarchy.scale(lit["id"]), lp["percent"]))
    print()
    print("  sign in as any of these — no password:")
    for name, email in STUDENTS:
        print("    %-22s %s" % (email, name))
    print()
    print("  kenji@uni.edu has not voted on who presents, so that question reads")
    print("  'your answer' for him. lena@uni.edu already voted, so for her it reads")
    print("  'everyone is answering'. Same question, same card, different person.")
    print()
