#!/usr/bin/env python3
"""
Relax Confort, run by seven people.

A real business: bedding and comfort products -- orthopedic mattresses,
toppers, pillows, quilts, poufs -- sold online across Algeria from Boumerdès,
in French and Arabic, at 2,500 to 38,500 DZD, with orders taken over two phone
numbers.

Seven people is a size worth showing, because it is the size most companies
actually are, and the one where a system like this either helps or gets in the
way. At seven they get no dashboard and no analytics -- those arrive at fifty
and two hundred, and this shop is neither. Nothing here turns them off. They
simply have not arrived.

What they do get is the shape of the company:

    ◎  Sell 400 mattresses a month without money stuck in stock or transit
       7 people · 4,000,000 DZD · by 31 Dec
       │
       ├─ ◎ Take every order that comes in, on the phone or the page
       │     Amina, Rachid ─ "Do we take orders on WhatsApp as well?"
       │
       ├─ ◎ Get every parcel delivered and every dinar back within the month
       │     Nadia, Lila · 600,000 DZD
       │
       ├─ ◎ Know what is in the depot without walking into it
       │     Lila, Karim · 2,000,000 DZD
       │
       ├─ ◎ Sell six models we can always get, from people who answer the phone
       │     Karim, Yacine, Sofiane ─ "Five years on the orthopedic range?"
       │
       ├─ ◎ Be the first shop somebody in Algeria finds
       │     Sofiane, Amina · 400,000 DZD
       │
       ├─ ◎ Make a complaint cheaper to answer than to ignore
       │     Rachid, Nadia
       │
       └─ ◎ Open a showroom in Boumerdès people can walk into
             Yacine, Lila, Rachid · 1,200,000 DZD · by 31 Mar

Seven cells and seven people, which means everybody is in two or three of
them. That is the point: a cell is an area of responsibility, not a
department, and nobody here has a department.

None of these children were "created". A cell of seven cannot create children
-- that unlocks at twenty. Every one of them started as a task in the shop
that outgrew one person, and expansion works at any size. Amina taking phone
orders became "take every order that comes in" the day Rachid had to help.

Three things are worth watching once it is running:

  · Four of the children have put a number on what they need, and those four
    come to 4,200,000 DZD of a 4,000,000 DZD budget. Nothing stops them. The
    shop says so, on its own page, in a sentence with the number in it.

  · Two children are due after the shop is. Said the same way, blocked the
    same amount, which is not at all.

  · The carrier question was answered by six of the seven -- Yacine settled
    it without voting in it, which is what running a shop looks like -- and
    made work at the top, where it was asked. That work is not repeated
    inside the delivery cell that grew later. A company-wide answer makes
    company-wide work, and whoever's area it is picks it up where it lies.

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

    def ident(cell):
        """A cell is a dict when you just made it and an id when you looked it
        up. Take either rather than making every caller remember which."""
        return cell["id"] if isinstance(cell, dict) else cell

    def add(cell, title, owner, progress=0, due=None, cost=None):
        t = task.create(yacine["id"], ident(cell), title)
        if owner:
            task.assign(owner["id"], t["id"], owner["id"])
            if progress:
                task.report_progress(owner["id"], t["id"], progress)
            if due:
                task.set_deadline(owner["id"], t["id"], due)
            if cost is not None:
                task.record_cost(owner["id"], t["id"], cost)
        return t

    def claim(title, owner, progress=0):
        """Pick up work one of the settled questions produced."""
        for t in task.in_cells([shop["id"]]):
            if t["title"] == title:
                task.assign(owner["id"], t["id"], owner["id"])
                if progress:
                    task.report_progress(owner["id"], t["id"], progress)
                return t
        return None

    # A question the whole shop answered makes work for the whole shop. It
    # stays where it was made and whoever's area it is picks it up -- rather
    # than being retyped inside the cell that later grew around it.
    claim("Buy or lease the van", nadia, 30)
    claim("Hire a driver", nadia)
    claim("Work out the cost per parcel on our own route", nadia, 20)
    claim("Agree the six with Sofiane", karim, 80)
    claim("Set the reorder point", karim, 80)

    # --- the parts of the business ----------------------------------------
    #
    # None of these was "created". Each began as one thing on somebody's list
    # that stopped fitting on a list, and became a cell with its own goal,
    # its own people and its own questions. A seven-person shop cannot start
    # a child cell -- that is offered at twenty -- but work outgrowing one
    # person is not gated on headcount, and this is what an organisation
    # actually is.
    def grew(title, owner, goal, crew, budget=None, due=None):
        """A piece of work that stopped fitting on one person's list."""
        seed_task = add(shop, title, owner)
        task.expand(yacine["id"], seed_task["id"], goal)
        cell = task.expanded_into(seed_task["id"])
        for who in crew:
            member.admit(yacine["id"], cell, who["name"], who["email"])
        if budget:
            cell_service.set_budget(yacine["id"], cell, budget, DZD)
        if due:
            cell_service.set_deadline(yacine["id"], cell, due)
        return cell

    # Orders, and the two phone numbers on the site.
    orders = grew("Take the orders without losing any", amina,
                  "Take every order that comes in, on the phone or the page",
                  [rachid])
    add(orders, "Rewrite the order sheet so two people can use it", amina, 60, "2026-11-18")
    add(orders, "Answer Instagram messages inside the hour", rachid, 30)
    add(orders, "Call back the 40 orders that never confirmed", amina, 0, "2026-11-12")
    whatsapp = decision.propose(
        amina["id"], orders,
        "Do we take orders on WhatsApp as well as the phone?",
        "Half the messages already arrive there. Right now we answer and then "
        "ask them to call, and some of them do not.",
        ["Yes, one number for both", "No, the phone is already full"],
        work={"0": ["Put the number on the site", "Agree who watches it and when"]})
    step(amina, whatsapp["id"], "open")
    step(amina, whatsapp["id"], "put_to_cell")
    decision.vote(rachid["id"], whatsapp["id"], dm.options_of(whatsapp["id"])[0]["id"])

    # Delivery, and the money that has to come back with the driver.
    delivery = grew("Get the parcels there and the money back", nadia,
                    "Get every parcel delivered and every dinar back within the week",
                    [lila], budget=600_000, due="2026-12-31")
    add(delivery, "Reconcile October against the carrier's statement", nadia, 100, "2026-11-05")
    add(delivery, "Rank the wilayas by refusal rate", lila, 45)
    add(delivery, "Agree what we do with a parcel refused twice", None)

    # The depot.
    depot = grew("Know what is actually in the depot", lila,
                 "Know what is in the depot without walking into it",
                 [karim], budget=2_000_000, due="2026-12-31")
    add(depot, "Count everything and write it down", lila, 60, "2026-11-20")
    add(depot, "Find somewhere dry for the toppers", lila, 0)

    # What we sell, and who makes it.
    # Sofiane is in here because what we sell and what the site says we sell
    # have to be the same six. That is the whole reason "agree the six with
    # Sofiane" is on Karim's list at the top.
    sourcing = grew("Choose what we sell and who makes it", karim,
                    "Sell six models we can always get, from people who answer the phone",
                    [yacine, sofiane], due="2027-01-31")
    add(sourcing, "Agree return terms with the workshop for pressure marks",
        karim, 25, "2026-12-10")
    add(sourcing, "Visit the two workshops in Sétif", karim, 0, "2026-11-28", 45_000)
    add(sourcing, "Drop the three models nobody buys", yacine, 40)
    warranty_q = decision.propose(
        karim["id"], sourcing,
        "Do we put five years on the orthopedic range?",
        "Everyone selling against us says two. The workshop will not sign for five.",
        ["Five years, and we carry it ourselves", "Two years, like everyone else"],
        work={"0": ["Work out what a claim costs us", "Say it plainly on the page"]})
    step(karim, warranty_q["id"], "open")
    step(karim, warranty_q["id"], "put_to_cell")
    w = dm.options_of(warranty_q["id"])
    decision.vote(yacine["id"], warranty_q["id"], w[0]["id"])
    decision.vote(karim["id"], warranty_q["id"], w[0]["id"])
    step(karim, warranty_q["id"], "accept_by_vote", "send_to_leader", "resolve",
         option_id=w[0]["id"],
         note="Five years is the only thing we can say that they cannot.")

    # Getting found.
    reach = grew("Make people find us", sofiane,
                 "Be the first shop somebody in Algeria finds when they want a mattress",
                 [amina], budget=400_000, due="2026-12-31")
    arabic = add(reach, "Rewrite the product pages in Arabic first, French second",
                 sofiane, 40, "2026-11-30")
    add(reach, "Photograph the six models on a real bed, not on the floor",
        sofiane, 70, "2026-11-15", 28_000)
    add(reach, "Stop the ads for models we do not stock", amina, 0, "2026-11-10")

    task.note(sofiane["id"], arabic["id"],
              "Half the messages on Instagram are in Arabic and the site answers in "
              "French. Doing the six that sell first.")
    evidence.attach(sofiane["id"], "task", arabic["id"], "measurement",
                    "62% of October's messages were written in Arabic")

    # A question about work that already exists. Its answer goes back to that
    # work; it does not become more work.
    doubt = decision.propose(
        sofiane["id"], reach,
        "Is the Arabic rewrite worth it before the winter season?",
        "It is six weeks of Sofiane, and winter is when mattresses sell.",
        ["Finish it before winter", "Six models now, the rest in January",
         "Stop, and spend the six weeks on ads"],
        about=arabic["id"])
    step(sofiane, doubt["id"], "open")
    decision.remark(amina["id"], doubt["id"],
                    "People ask the price in Arabic and leave when the page answers "
                    "in French. That is the whole conversation.",
                    dm.options_of(doubt["id"])[1]["id"])

    # After the sale.
    care = grew("Look after people once they have paid", rachid,
                "Make a complaint cheaper to answer than to ignore", [nadia])
    claims = add(care, "Answer the twelve warranty claims from September", rachid, 50, "2026-11-25")
    add(care, "Write down what we do when a topper flattens", rachid, 0)
    add(care, "Find out whether the returns come from one wilaya", nadia, 15)
    task.note(rachid["id"], claims["id"],
              "Nine of the twelve are the same complaint: the topper flattens on one "
              "side. That is a supplier question, not a warranty question.")
    evidence.attach(rachid["id"], "task", claims["id"], "note",
                    "Nine of twelve claims name the same model")

    # The one that is not running the shop, but building it.
    room = grew("Open a showroom in Boumerdès so people can lie on one", yacine,
                "Open a showroom in Boumerdès people can walk into",
                [lila, rachid], budget=1_200_000, due="2027-03-31")
    add(room, "Find 60m² on the main road", lila, 0, "2026-12-15")
    add(room, "Price the fit-out", lila, 0)
    add(room, "Work out who staffs it on Fridays", rachid, 0)

    # Still one person's, still at the top.
    add(shop, "Set the winter price list", yacine, 20, "2026-11-30")

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
