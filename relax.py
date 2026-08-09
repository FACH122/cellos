#!/usr/bin/env python3
"""
Relax Confort, run by seven people.

A real business: bedding and comfort products -- orthopedic mattresses,
toppers, pillows, quilts, poufs -- sold online across Algeria from Boumerdès,
in French and Arabic, at 2,500 to 38,500 DZD, with orders taken over two phone
numbers.

Seven people is a size worth showing, because it is the size most companies
actually are and the one where a system like this either helps or gets in the
way. At seven, CellOS gives them almost nothing: tasks, questions, votes,
evidence, and what the cell has learned. No child cells, no dashboard, no
analytics -- those appear at twenty, fifty and two hundred, and this shop is
none of those. Nothing here turns them off. They simply have not arrived.

The one exception is worth watching: a piece of work can outgrow one person at
any size. When "open a showroom" stops being something Yacine does on
Saturdays, it becomes a cell with people in it, and the seven-person cell has
a child without ever having been big enough to "create" one.

    python3 relax.py           seed it and serve on 8424
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("CELLOS_DB", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "relax.db"))
os.environ.setdefault("CELLOS_PORT", "8424")

import cellos  # noqa: E402
from cellos.app import server  # noqa: E402
from cellos.domains import permission  # noqa: E402
from cellos.domains.cell import service as cell_service  # noqa: E402
from cellos.domains.decision import model as dm, service as decision  # noqa: E402
from cellos.domains.evidence import service as evidence  # noqa: E402
from cellos.domains.member import service as member  # noqa: E402
from cellos.domains.task import service as task  # noqa: E402
from cellos.kernel import db  # noqa: E402

DZD = "DZD"


def step(actor, decision_id, *preferred, **args):
    """Fire the first offered transition, the way the interface does."""
    d = decision.get(decision_id)
    offered = {a["name"] for a in decision.actions(actor["id"], d)}
    for name in preferred:
        if name in offered:
            return decision.act(actor["id"], decision_id, name, **args)
    raise RuntimeError("none of %s on a %s decision (offered %s)"
                       % (list(preferred), d["state"], sorted(offered)))


def build():
    # --- the seven -------------------------------------------------------
    yacine = member.register("Yacine Belkacem", "yacine@relaxconfort.dz")
    shop = cell_service.create(
        yacine["id"],
        "Sell 400 mattresses a month across Algeria without money stuck "
        "in stock or in transit")

    people = {}
    for name, email in [
        ("Amina Haddad", "amina@relaxconfort.dz"),      # the two phone numbers
        ("Karim Bouzid", "karim@relaxconfort.dz"),      # suppliers
        ("Nadia Slimani", "nadia@relaxconfort.dz"),     # delivery and the cash
        ("Sofiane Meziane", "sofiane@relaxconfort.dz"),  # Facebook and Instagram
        ("Lila Cherif", "lila@relaxconfort.dz"),        # the depot
        ("Rachid Amrani", "rachid@relaxconfort.dz"),    # after the sale
    ]:
        people[name.split()[0].lower()] = member.admit(
            yacine["id"], shop["id"], name, email)
    amina, karim = people["amina"], people["karim"]
    nadia, sofiane = people["nadia"], people["sofiane"]
    lila, rachid = people["lila"], people["rachid"]

    cell_service.set_budget(yacine["id"], shop["id"], 4_000_000, DZD)
    cell_service.set_deadline(yacine["id"], shop["id"], "2026-12-31")

    # --- settled: who carries the parcels --------------------------------
    #
    # The question every Algerian online shop answers, and the one that
    # decides whether the money comes back.
    carrier = decision.propose(
        yacine["id"], shop["id"],
        "Qui livre pour nous ? — which delivery company do we put our weight behind?",
        "Cash on delivery means the parcel and the money are the same problem. "
        "A refused parcel is a mattress that travelled to Oran and came back, "
        "and we pay both ways.",
        [
            "Yalidine everywhere",
            "ZR Express everywhere",
            "Our own van for Alger, Boumerdès and Tizi Ouzou; a partner for the rest",
        ],
        work={
            "0": ["Sign the Yalidine contract", "Agree the return rate we will accept"],
            "1": ["Sign with ZR Express", "Test twenty parcels to the south"],
            "2": ["Buy or lease the van", "Hire a driver", "Pick a partner for the far wilayas",
                  "Work out the cost per parcel on our own route"],
        },
    )
    step(yacine, carrier["id"], "open")
    decision.remark(nadia["id"], carrier["id"],
                    "Two thirds of what we send goes to the three wilayas around us. "
                    "Paying a carrier's national price for a parcel that travels 40 km "
                    "is most of what we lose.", dm.options_of(carrier["id"])[2]["id"])
    decision.remark(karim["id"], carrier["id"],
                    "A van is a driver, fuel, insurance and a person to replace when "
                    "he is ill. We are seven.", dm.options_of(carrier["id"])[2]["id"])
    evidence.attach(nadia["id"], "option", dm.options_of(carrier["id"])[2]["id"],
                    "measurement", "October: 63% of parcels went to Alger, Boumerdès, Tizi Ouzou")
    step(yacine, carrier["id"], "put_to_cell")
    options = dm.options_of(carrier["id"])
    for who, pick in ((nadia, 2), (lila, 2), (rachid, 2), (amina, 0),
                      (karim, 0), (sofiane, 2)):
        decision.vote(who["id"], carrier["id"], options[pick]["id"])
    step(yacine, carrier["id"], "accept_by_vote", "send_to_leader", "resolve",
         option_id=options[2]["id"],
         note="Our own van near home, a partner far away. Nadia's number decides it: "
              "we are paying national prices to deliver down the road.")

    # --- settled and recorded: where the stock sits ------------------------
    stock = decision.propose(
        karim["id"], shop["id"],
        "Do we hold stock, or order from the workshop per batch?",
        "We have 4,000,000 DZD. Every mattress in the depot is money not "
        "buying the next one.",
        ["Hold two months of the six that sell", "Order per batch, nothing on the shelf"],
        work={"0": ["Agree the six with Sofiane", "Set the reorder point"]},
    )
    step(karim, stock["id"], "open")
    step(karim, stock["id"], "put_to_cell")
    o = dm.options_of(stock["id"])
    for who in (yacine, lila, amina, nadia, sofiane, rachid):
        decision.vote(who["id"], stock["id"], o[0]["id"])
    step(yacine, stock["id"], "accept_by_vote", "send_to_leader", "resolve",
         option_id=o[0]["id"],
         note="Per batch sounds disciplined and loses the sale. Two months on the six "
              "that move, nothing on the rest.")
    step(yacine, stock["id"], "record",
         outcome="Held two months on six models since September. Stockouts went from "
                 "eleven in August to one in October.",
         lesson="The models that sell are not the ones we like. Let the numbers pick "
                "the six, and re-pick them every season.")

    # --- open, and genuinely undecided ------------------------------------
    #
    # The real fight in Algerian e-commerce: a confirmation call cuts refusals
    # and costs a person's whole morning.
    calls = decision.propose(
        amina["id"], shop["id"],
        "Do we call every order before we send it?",
        "Refused parcels are 18% of what we ship. A call before dispatch cuts that, "
        "and Amina cannot make 400 calls a month on her own.",
        [
            "Call every order",
            "Call only above 15,000 DZD",
            "Send everything, and stop serving the wilayas that refuse most",
        ],
        work={
            "0": ["Write the script", "Find the hours, or find a second person"],
            "1": ["Set the threshold in the order sheet", "Measure refusals either side of it"],
            "2": ["Rank the wilayas by refusal rate", "Decide who we stop serving"],
        },
    )
    step(amina, calls["id"], "open")
    opts = dm.options_of(calls["id"])
    decision.remark(amina["id"], calls["id"],
                    "Every order is 400 calls a month. That is my whole morning, "
                    "every day, and nobody answers the phone at the price we sell at.",
                    opts[0]["id"])
    decision.remark(nadia["id"], calls["id"],
                    "The refusals are not spread evenly. Above 15,000 they are 31%, "
                    "below it they are 9%.", opts[1]["id"])
    evidence.attach(nadia["id"], "option", opts[1]["id"], "measurement",
                    "Refusal rate by order value, Sept–Oct")
    decision.remark(sofiane["id"], calls["id"],
                    "If we stop serving a wilaya the ads keep selling there and we "
                    "refund. I would rather call.", opts[2]["id"])
    step(amina, calls["id"], "put_to_cell")
    for who, pick in ((nadia, 1), (karim, 1), (amina, 1), (sofiane, 0), (lila, 0)):
        decision.vote(who["id"], calls["id"], opts[pick]["id"])

    # Work the two settled questions produced. Nobody transcribed it -- it
    # appeared when the cell chose. Some of it has been picked up and some has
    # not, which is the ordinary state of a Tuesday and the thing the health
    # reading is actually about.
    generated = {t["title"]: t for t in task.in_cells([shop["id"]])}
    for title, owner, progress in [
        ("Buy or lease the van", nadia, 30),
        ("Hire a driver", nadia, 0),
        ("Agree the six with Sofiane", karim, 80),
    ]:
        t = generated.get(title)
        if t:
            task.assign(owner["id"], t["id"], owner["id"])
            if progress:
                task.report_progress(owner["id"], t["id"], progress)

    # --- the work ---------------------------------------------------------
    def add(title, owner, progress=0, due=None, cost=None):
        t = task.create(yacine["id"], shop["id"], title)
        task.assign(owner["id"], t["id"], owner["id"])
        if progress:
            task.report_progress(owner["id"], t["id"], progress)
        if due:
            task.set_deadline(owner["id"], t["id"], due)
        if cost is not None:
            task.record_cost(owner["id"], t["id"], cost)
        return t

    arabic = add("Rewrite the product pages in Arabic first, French second",
                 sofiane, 40, "2026-11-30")
    add("Photograph the six models on a real bed, not on the floor", sofiane, 70, "2026-11-15")
    add("Reconcile October's cash on delivery against the carrier's statement",
        nadia, 100, "2026-11-05")
    add("Agree return terms with the workshop for pressure marks", karim, 25, "2026-12-10")
    add("Count the depot and write down what is actually there", lila, 60, "2026-11-20")
    warranty = add("Answer the twelve warranty claims from September", rachid, 50, "2026-11-25")
    showroom = add("Open a showroom in Boumerdès so people can lie on one", yacine, 15)

    task.note(sofiane["id"], arabic["id"],
              "Half the messages on Instagram are in Arabic and the site answers in French. "
              "Doing the six that sell first.")
    task.note(rachid["id"], warranty["id"],
              "Nine of the twelve are the same complaint: the topper flattens on one side. "
              "That is a supplier question, not a warranty question.")
    evidence.attach(rachid["id"], "task", warranty["id"], "note",
                    "Nine of twelve claims name the same model")

    # A question about work that already exists. Its answer comes back to the
    # task; it does not turn into more work.
    doubt = decision.propose(
        sofiane["id"], shop["id"],
        "Is the Arabic rewrite worth it before the winter season?",
        "It is six weeks of Sofiane, and winter is when mattresses sell.",
        ["Finish it before winter", "Six models now, the rest in January",
         "Stop, and spend the six weeks on ads"],
        about=arabic["id"],
    )
    step(sofiane, doubt["id"], "open")
    decision.remark(amina["id"], doubt["id"],
                    "People ask the price in Arabic and leave when the page answers "
                    "in French. That is the whole conversation.",
                    dm.options_of(doubt["id"])[1]["id"])

    # --- work that outgrew one person -------------------------------------
    task.expand(yacine["id"], showroom["id"],
                "Open a showroom in Boumerdès people can walk into")
    room = task.expanded_into(showroom["id"])
    for who in (lila, rachid):
        member.admit(yacine["id"], room, who["name"], who["email"])
    cell_service.set_budget(yacine["id"], room, 1_200_000, DZD)
    cell_service.set_deadline(yacine["id"], room, "2027-03-31")
    for title, owner in [("Find 60m² on the main road", lila),
                         ("Price the fit-out", lila),
                         ("Work out who staffs it on Fridays", rachid)]:
        t = task.create(yacine["id"], room, title)
        task.assign(owner["id"], t["id"], owner["id"])

    return shop, room


def main():
    cellos.boot()
    if db.value("SELECT count(*) FROM events", default=0):
        print("data/relax.db already has something in it. Delete it to reseed.")
    else:
        shop, room = build()
        print("Relax Confort seeded.")

    host, port = "127.0.0.1", int(os.environ["CELLOS_PORT"])
    print("\n  http://%s:%d\n" % (host, port))
    print("  sign in with any name and one of these:\n")
    for who, does in [
        ("yacine@relaxconfort.dz", "runs it — the only leader"),
        ("amina@relaxconfort.dz", "the two phone numbers"),
        ("nadia@relaxconfort.dz", "delivery, and the cash that comes back"),
        ("karim@relaxconfort.dz", "the workshops that make the mattresses"),
        ("sofiane@relaxconfort.dz", "Facebook, Instagram, the site"),
        ("lila@relaxconfort.dz", "the depot in Boumerdès"),
        ("rachid@relaxconfort.dz", "after the sale"),
    ]:
        print("    %-30s %s" % (who, does))
    print()
    httpd = server.serve(host, port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
