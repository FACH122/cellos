#!/usr/bin/env python3
"""
A wedding in the Aurès: five people answer for it, twenty end up in it.

Dounia is from Arris, Massinissa from T'kout. Three days in September, six
hundred people if nobody is left out, twenty-five sheep, and a village of
ninety houses lending its floors. This is the largest thing most families
ever run, and they run it with no tooling at all.

Five people answer for the whole of it -- and all five lead, because in the
Aurès the couple are not the organisers. The two fathers, the bride's mother
and the eldest brother are, and none of them outranks the others:

    ◎  Marry Dounia and Massinissa in T'kout over three days in September
       Massinissa, Dounia, Salah, Djamila, Hocine -- all five lead
       3,500,000 DZD · the day is 18 September 2027
       │
       ├─ ◎ Run three days so nobody stands about wondering what is next
       │     Salah* + Amar the elder · 120,000
       │
       ├─ ◎ Feed six hundred people for three days
       │     Djamila* + Yamina, Zohra, Brahim · 1,850,000
       │     └─ ◎ Roast twenty-five sheep over three days
       │           Brahim* + Tayeb · 200,000
       │
       ├─ ◎ Have the trousseau, the dresses and the henna night ready
       │     Dounia* + Kenza, Nadjet · 700,000
       │     └─ ◎ Give the henna night its own evening
       │           Nadjet* + Souad who sings · 180,000
       │
       ├─ ◎ Bring the bride from Arris on a road not built for it
       │     Hocine* + Rabah, Youcef · 240,000
       │
       ├─ ◎ Have the rahaba, the zerna and the baroud at the right hour
       │     Massinissa* + Lakhdar, Farid · 350,000
       │
       ├─ ◎ Put six hundred people to bed in a village of ninety houses
       │     Hocine* + Ourida, Slimane · 180,000
       │
       ├─ ◎ Have the mairie and the mosque satisfied before anybody travels
       │     Massinissa* + Ali · 15,000
       │
       └─ ◎ Know what this costs before it is spent
             Hocine* + Salah, Massinissa

Eleven cells, twenty people, fifty-four things to do, six questions.

**Fifteen of the twenty never appear on the wedding's own list of people.**
Yamina has rolled chakhchoukha for thirty years and is in the food cell only.
Ali does the Batna runs. Souad sings at henna nights. Thirteen of the fifteen
are in exactly one cell; only Brahim and Nadjet are in two, because the piece
each was brought in for -- the méchoui, the henna night -- grew a cell of its
own underneath them. Nobody needs to be listed at the top to be trusted with
something: a cell is not a subset of the cell above it. That is the shape of a
wedding like this. Five answer for it, and it is carried by people who each
own one piece of it.

The money cell is the exception that proves it, and the only one bringing
nobody new: its three are all upstairs already, and they still had to be
admitted to it by name. Leading a cell above lets you *act* below, but it does
not put work in your hands. Being answerable for something is a membership,
not an inheritance.

Three things are worth watching once it is running:

  · **It crossed twenty without anybody deciding to.** It began as five. Each
    cell brought in the people it needed, and the total reached exactly
    twenty -- where CellOS stops letting a vote settle a question on its own
    and starts asking a leader to sign it. Nobody configured that. Nobody was
    told. The wedding got big and the way it decides things changed.

  · **The parts come to 3,455,000 of 3,500,000.** It balances, with 45,000
    spare, which is not a comfortable number against three days and six
    hundred people. And the question still open at the top is *how many do we
    actually invite* -- where six hundred is winning, and six hundred is the
    option that breaks the 45,000.

  · **Nothing here was created.** A cell of five cannot create children; that
    unlocks at twenty, which this only reached afterwards. Every one of the
    ten grew out of a task that stopped fitting one person -- which works at
    any size, and is the only reason this shape exists at all.

    python3 aures.py           seed it and serve on 8425
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("CELLOS_DB", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "aures.db"))
os.environ.setdefault("CELLOS_PORT", "8425")

import cellos  # noqa: E402
from cellos.app import server  # noqa: E402
from cellos.domains.cell import service as cell_service  # noqa: E402
from cellos.domains.decision import model as dm, service as decision  # noqa: E402
from cellos.domains.evidence import service as evidence  # noqa: E402
from cellos.domains.member import service as member  # noqa: E402
from cellos.domains.task import service as task  # noqa: E402
from cellos.kernel import db  # noqa: E402

DZD = "DZD"
DAY = "2027-09-18"          # the third day, the one people mean by "the wedding"


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
    # --- the five who answer for it --------------------------------------
    #
    # Two families and the wedding between them. In the Aurès the couple are
    # not the organisers -- the fathers, the mothers and the eldest brother
    # are -- so all five lead, and none of them outranks the others here.
    massi = member.register("Massinissa Aït Amrane", "massinissa@aures.dz")
    wedding = cell_service.create(
        massi["id"],
        "Marry Dounia and Massinissa in T'kout over three days in September, "
        "feed everyone who comes, and owe nothing afterwards")

    five = {}
    for name, email in [
        ("Dounia Boulahbal", "dounia@aures.dz"),        # the bride
        ("Salah Aït Amrane", "salah@aures.dz"),         # the groom's father
        ("Djamila Boulahbal", "djamila@aures.dz"),      # the bride's mother
        ("Hocine Aït Amrane", "hocine@aures.dz"),       # the eldest brother
    ]:
        five[name.split()[0].lower()] = member.admit(
            massi["id"], wedding["id"], name, email, member.LEADER)
    dounia, salah = five["dounia"], five["salah"]
    djamila, hocine = five["djamila"], five["hocine"]

    cell_service.set_budget(salah["id"], wedding["id"], 3_500_000, DZD)
    cell_service.set_deadline(salah["id"], wedding["id"], DAY)

    # --- helpers ---------------------------------------------------------

    def ident(cell):
        return cell["id"] if isinstance(cell, dict) else cell

    def add(cell, title, owner, progress=0, due=None, cost=None):
        t = task.create(massi["id"], ident(cell), title)
        if owner:
            task.assign(owner["id"], t["id"], owner["id"])
            if progress:
                task.report_progress(owner["id"], t["id"], progress)
            if due:
                task.set_deadline(owner["id"], t["id"], due)
            if cost is not None:
                task.record_cost(owner["id"], t["id"], cost)
        return t

    def grew(parent, title, owner, goal, joining=(), budget=None, due=None):
        """
        A piece of work that stopped fitting one person.

        `joining` is the people it brings in who are not upstairs. That is the
        whole shape of a wedding like this: the five answer for it, and the
        aunt who has cooked chakhchoukha for thirty years is in exactly one
        cell and belongs nowhere else on the tree.
        """
        seed_task = add(parent, title, owner)
        task.expand(massi["id"], seed_task["id"], goal)
        cell = task.expanded_into(seed_task["id"])
        brought = {}
        for name, email in joining:
            p = member.admit(massi["id"], cell, name, email)
            brought[name.split()[0].lower()] = p
        if budget:
            cell_service.set_budget(salah["id"], cell, budget, DZD)
        if due:
            cell_service.set_deadline(salah["id"], cell, due)
        return cell, brought

    # --- settled: the village or a hall in Batna --------------------------
    #
    # The question every Aurès family argues about. A hall in Batna is one
    # afternoon, paid for and finished. T'kout is three days, four hundred
    # relatives, and every house in the village lending its floor.
    where = decision.propose(
        salah["id"], wedding["id"],
        "T'kout, or a hall in Batna?",
        "Half the family is in Batna and Constantine and would have to drive "
        "the mountain road twice. The other half has never held a wedding "
        "anywhere but the village.",
        [
            "Three days in T'kout, the way both families were married",
            "One afternoon in a hall in Batna, catered, everyone home by night",
            "Henna night in T'kout, the wedding itself in a hall in Batna",
        ],
        work={
            "0": ["Ask every house in the village how many it can sleep",
                  "Work out the water for three days",
                  "Get the road to the upper houses graded before September"],
            "1": ["Price three halls in Batna", "Count who would actually come that far"],
            "2": ["Price the halls", "Work out two sets of transport"],
        },
    )
    step(salah, where["id"], "open")
    opts = dm.options_of(where["id"])
    decision.remark(djamila["id"], where["id"],
                    "My mother was married in that village and so was I. If we do it "
                    "in a hall the old women will not come, and they are the wedding.",
                    opts[0]["id"])
    decision.remark(hocine["id"], where["id"],
                    "Three days in T'kout means water for six hundred people in "
                    "September. The spring is at its lowest then. That is the part "
                    "nobody costs.", opts[0]["id"])
    decision.remark(massi["id"], where["id"],
                    "A hall is 400,000 and it is finished. Three days is everything "
                    "we have and the whole village's time as well.", opts[1]["id"])
    evidence.attach(hocine["id"], "option", opts[0]["id"], "measurement",
                    "The village spring in September: 40% of its spring flow")
    step(salah, where["id"], "put_to_cell")
    for who, pick in ((djamila, 0), (dounia, 0), (salah, 0), (hocine, 0), (massi, 1)):
        decision.vote(who["id"], where["id"], opts[pick]["id"])
    step(salah, where["id"], "accept_by_vote", "send_to_leader", "resolve",
         option_id=opts[0]["id"],
         note="Four to one for the village. Hocine is right about the water, so that "
              "becomes work rather than an objection.")

    # --- settled and recorded: how many days ------------------------------
    days = decision.propose(
        djamila["id"], wedding["id"],
        "Three days, or two?",
        "Henna night, the day itself, and the day after for whoever is still "
        "there. The middle day is the one everybody means. The third is the "
        "one that costs.",
        ["Three days", "Two days, and people go home on the Saturday night"],
        work={"0": ["Feed people on the Sunday too",
                    "Find beds for whoever is still there on the Sunday"]},
    )
    step(djamila, days["id"], "open")
    step(djamila, days["id"], "put_to_cell")
    o = dm.options_of(days["id"])
    for who in (salah, dounia, hocine, massi, djamila):
        decision.vote(who["id"], days["id"], o[0]["id"])
    step(salah, days["id"], "accept_by_vote", "send_to_leader", "resolve",
         option_id=o[0]["id"],
         note="Nobody who drove from Constantine is leaving on the Saturday night. "
              "The third day happens whether we plan it or not, so we plan it.")
    step(salah, days["id"], "record",
         outcome="Three days, and the Sunday budgeted rather than improvised.",
         lesson="The day that costs the most is the one nobody decided to have. "
                "Deciding to have it is cheaper than being surprised by it.")

    # --- open, and genuinely undecided ------------------------------------
    how_many = decision.propose(
        hocine["id"], wedding["id"],
        "How many do we actually invite?",
        "Six hundred is what the two families come to if nobody is left out. "
        "Every hundred is roughly four more sheep and eighty more beds.",
        [
            "Six hundred — nobody in either family is left out",
            "Three hundred and fifty — the close families and the village",
            "Six hundred on the middle day, the village only on the other two",
        ],
        work={
            "0": ["Count the beds in the village against six hundred"],
            "1": ["Draw the line and tell people before they hear it from others"],
            "2": ["Work out three different numbers for three days"],
        },
    )
    step(hocine, how_many["id"], "open")
    hm = dm.options_of(how_many["id"])
    decision.remark(salah["id"], how_many["id"],
                    "You cannot invite a man's brother and not the man. Six hundred "
                    "is not a choice we are making, it is a count of who exists.",
                    hm[0]["id"])
    decision.remark(hocine["id"], how_many["id"],
                    "Six hundred over three days is 1,800 meals. At 900 DZD a plate "
                    "that is more than the whole food budget on its own.", hm[1]["id"])
    evidence.attach(hocine["id"], "option", hm[1]["id"], "measurement",
                    "Meals × days × plate cost against the food budget")
    decision.remark(dounia["id"], how_many["id"],
                    "The third option is what my aunt did in Arris and nobody was "
                    "offended. The village is there every day anyway.", hm[2]["id"])
    step(hocine, how_many["id"], "put_to_cell")
    for who, pick in ((dounia, 2), (djamila, 0), (massi, 2), (salah, 0)):
        decision.vote(who["id"], how_many["id"], hm[pick]["id"])

    # Work the two settled questions made. Nobody typed it in; it appeared
    # when the family chose, and it stays here because it was decided here.
    made = {t["title"]: t for t in task.in_cells([wedding["id"]])}
    for title, owner, progress in [
        ("Ask every house in the village how many it can sleep", djamila, 55),
        ("Work out the water for three days", hocine, 30),
        ("Get the road to the upper houses graded before September", salah, 0),
        ("Feed people on the Sunday too", djamila, 20),
    ]:
        t = made.get(title)
        if t:
            task.assign(owner["id"], t["id"], owner["id"])
            if progress:
                task.report_progress(owner["id"], t["id"], progress)

    # ------------------------------------------------------------------
    # The cells. None of these were created -- a cell of five cannot create
    # children, that unlocks at twenty. Every one grew out of a task that
    # stopped fitting one person, which works at any size.
    # ------------------------------------------------------------------

    # 1. The three days themselves, and the order of them.
    days_cell, p = grew(
        wedding, "Work out what happens on each of the three days", salah,
        "Run three days in T'kout so nobody is standing about wondering what is next",
        [("Amar Ould Salah", "amar@aures.dz")],       # the village elder
        budget=120_000, due="2027-09-01")
    amar = p["amar"]
    add(days_cell, "Write the order of the middle day, hour by hour", salah, 40, "2027-08-20")
    add(days_cell, "Agree with the mosque what time the fatiha is", amar, 70, "2027-07-15")
    add(days_cell, "Decide who greets people at the road", amar, 0)
    add(days_cell, "Work out where six hundred people stand during the fatiha", salah, 15)

    # 2. Feeding them. The largest thing in the wedding by every measure.
    food, p = grew(
        wedding, "Feed everyone for three days", djamila,
        "Feed six hundred people for three days without anyone waiting or anyone "
        "running out",
        [("Yamina Aït Amrane", "yamina@aures.dz"),    # chakhchoukha, thirty years of it
         ("Zohra Boulahbal", "zohra@aures.dz"),       # the bride's aunt
         ("Brahim Meziani", "brahim@aures.dz")],      # does the méchoui
        budget=1_850_000, due="2027-09-16")
    yamina, zohra, brahim = p["yamina"], p["zohra"], p["brahim"]
    chak = add(food, "Roll the chakhchoukha — how many hands, how many days ahead",
               yamina, 35, "2027-09-12")
    add(food, "Count the sheep and agree the price now, not in September", brahim, 60,
        "2027-06-30", 1_125_000)
    add(food, "Find the twelve gas rings and the big pots", zohra, 25)
    add(food, "Work out who serves, and who serves the servers", djamila, 10)
    add(food, "The sweets — how many trays and who makes them", zohra, 45, "2027-09-10")
    task.note(yamina["id"], chak["id"],
              "Chakhchoukha for six hundred cannot be rolled the day before. Eight "
              "women, three days, and it has to be somewhere dry. The old school is "
              "empty and it has a floor.")
    evidence.attach(yamina["id"], "task", chak["id"], "note",
                    "Eight women × three days, and the old school as the room")

    # 2a. The méchoui got big enough to be its own thing.
    mechoui, p = grew(
        food, "Do the méchoui properly", brahim,
        "Roast twenty-five sheep over three days without anybody waiting for meat",
        [("Tayeb Meziani", "tayeb@aures.dz")],        # Brahim's brother, the pits
        budget=200_000, due="2027-09-15")
    tayeb = p["tayeb"]
    add(mechoui, "Dig and line the four pits", tayeb, 0, "2027-09-14")
    add(mechoui, "Order the charcoal in June before the price moves", brahim, 100,
        "2027-06-20", 95_000)
    add(mechoui, "Agree with the butcher in Arris who slaughters and when", brahim, 50)

    # 3. The bride's side: the trousseau, and the henna night.
    bride, p = grew(
        wedding, "Get the bride's side ready", dounia,
        "Have the trousseau, the dresses and the henna night ready without Dounia "
        "doing all of it herself",
        [("Kenza Boulahbal", "kenza@aures.dz"),       # the bride's sister
         ("Nadjet Boulahbal", "nadjet@aures.dz")],    # cousin, does the henna
        budget=700_000, due="2027-09-16")
    kenza, nadjet = p["kenza"], p["nadjet"]
    melhfa = add(bride, "Find the melhfa and have it fitted", dounia, 65, "2027-08-10",
                 180_000)
    add(bride, "Get grandmother's tabzimt and the silver cleaned and checked", kenza, 80,
        "2027-08-01")
    add(bride, "Buy the trousseau, and write down what came from whom", kenza, 30)
    add(bride, "Decide what the bride wears on each of the three days", dounia, 20)
    task.note(dounia["id"], melhfa["id"],
              "The woman in Arris who does the traditional melhfa properly has two "
              "other weddings in September. She wants to know now.")

    # 3a. The henna night became its own evening with its own people.
    henna, p = grew(
        bride, "Run the henna night", nadjet,
        "Give the henna night its own evening rather than squeezing it into the day "
        "before",
        [("Souad Hamlaoui", "souad@aures.dz")],       # sings at henna nights
        budget=180_000, due="2027-09-16")
    souad = p["souad"]
    add(henna, "Ask Souad and the women who sing with her", nadjet, 90, "2027-07-01")
    add(henna, "Work out the room — the courtyard if it is dry, the school if not", souad, 20)
    add(henna, "The henna itself, and who applies it", nadjet, 50)

    # 4. Bringing the bride from Arris to T'kout: the rakb, over mountain road.
    rakb, p = grew(
        wedding, "Bring the bride from Arris", hocine,
        "Bring the bride from Arris to T'kout with everyone who is coming with her, "
        "on a road that is not built for it",
        [("Rabah Aït Amrane", "rabah@aures.dz"),      # cousin, drives
         ("Youcef Hamlaoui", "youcef@aures.dz")],     # has the 4x4s
        budget=240_000, due="2027-09-17")
    rabah, youcef = p["rabah"], p["youcef"]
    road = add(rakb, "Decide which road the rakb takes", hocine, 100, "2027-07-20")
    add(rakb, "Count the cars, and who drives which", rabah, 40)
    add(rakb, "Ask the gendarmerie about the convoy on that stretch", youcef, 0, "2027-08-25")
    add(rakb, "Work out where the convoy stops and for how long", rabah, 15)

    # A question settled inside the cell that owns it, and recorded.
    which_road = decision.propose(
        hocine["id"], rakb, "The old mountain road, or round by the N87?",
        "The mountain road is forty minutes. The N87 is an hour and fifty but it "
        "is tarmac the whole way and a convoy can hold together on it.",
        # Declared, because a question with no work attached falls back to
        # making one task named after the winning option -- which reads as
        # "Round by the N87" sitting in the list as though it were a job.
        ["The mountain road", "Round by the N87"],
        work={"0": ["Drive it once loaded, in September light"],
              "1": ["Tell every driver the route a week before, not on the day"]},
    )
    step(hocine, which_road["id"], "open")
    wr = dm.options_of(which_road["id"])
    decision.remark(youcef["id"], which_road["id"],
                    "Thirty cars on the mountain road means the last one arrives "
                    "twenty minutes after the first and one of them will be a Clio.",
                    wr[1]["id"])
    evidence.attach(youcef["id"], "option", wr[1]["id"], "note",
                    "Drove both in April with a loaded car: 42 min against 1h48")
    step(hocine, which_road["id"], "put_to_cell")
    for who in (rabah, youcef, hocine):
        decision.vote(who["id"], which_road["id"], wr[1]["id"])
    step(hocine, which_road["id"], "accept_by_vote", "send_to_leader", "resolve",
         option_id=wr[1]["id"],
         note="Longer, and everybody arrives together, which is the entire point of "
              "a rakb.")
    step(hocine, which_road["id"], "record",
         outcome="The N87. Convoy held together both times we tested it.",
         lesson="A procession is not measured by how fast the first car arrives.")

    # 5. The music, the rahaba, and the baroud.
    music, p = grew(
        wedding, "Sort out the music and the rahaba", massi,
        "Have the rahaba, the zerna and the baroud happen at the right hour and "
        "without anybody getting hurt",
        [("Lakhdar Sahraoui", "lakhdar@aures.dz"),    # leads the rahaba troupe
         ("Farid Bouzid", "farid@aures.dz")],         # the baroud, and the licence for it
        budget=350_000, due="2027-09-17")
    lakhdar, farid = p["lakhdar"], p["farid"]
    troupe = add(music, "Book Lakhdar's troupe for the middle day", massi, 75, "2027-06-15",
                 220_000)
    add(music, "Agree with the zerna players what they play and when", lakhdar, 30)
    add(music, "Get the licence for the baroud and tell the gendarmerie", farid, 20,
        "2027-08-30")
    add(music, "Decide where the baroud happens, away from the cars and the children",
        farid, 0)

    # 6. Where six hundred people sleep and wash. The thing the village
    #    actually provides, and the thing nobody budgets for.
    beds, p = grew(
        wedding, "Work out where everybody sleeps", hocine,
        "Put six hundred people to bed for three nights in a village of ninety houses",
        [("Ourida Aït Amrane", "ourida@aures.dz"),    # knows every house
         ("Slimane Ferhat", "slimane@aures.dz")],     # the big house at the top
        budget=180_000, due="2027-09-14")
    ourida, slimane = p["ourida"], p["slimane"]
    add(beds, "Write down every house and how many it sleeps", ourida, 55, "2027-08-15")
    add(beds, "Borrow mattresses and blankets, and write down whose", ourida, 25)
    water = add(beds, "The water — three days, six hundred people, September", slimane, 10,
                "2027-08-31")
    add(beds, "Work out the washing and where people can be clean", slimane, 0)
    task.note(slimane["id"], water["id"],
              "The spring is at its lowest in September. Two tankers from Arris is "
              "about 60,000 and it is the cheapest thing on this whole list.")

    # 7. The papers. Small, dull, and the only cell that can stop the wedding.
    papers, p = grew(
        wedding, "Do the paperwork", massi,
        "Have the mairie and the mosque both satisfied before anybody travels",
        [("Ali Benyahia", "ali@aures.dz")],           # does the Batna runs
        budget=15_000, due="2027-08-20")
    ali = p["ali"]
    add(papers, "Get both birth certificates from the mairie in Batna", ali, 100,
        "2027-05-30", 1_200)
    add(papers, "The medical certificates, both of us", massi, 50, "2027-08-01")
    add(papers, "Book the date at the mairie", ali, 100, "2027-06-10")
    add(papers, "Agree the fatiha with the imam", massi, 60)

    # 8. What it costs, and who puts in. The cell that watches the others.
    #
    # The only cell that brings nobody new in. Its three are already upstairs
    # -- and they have to be named here anyway, because leading a cell above
    # lets you act in the ones below but does not put work in your hands.
    # Being answerable for something is a membership, not an inheritance.
    money, _ = grew(
        wedding, "Keep track of what this costs", hocine,
        "Know what this costs before it is spent, and who has put in what",
        [("Salah Aït Amrane", "salah@aures.dz"),
         ("Massinissa Aït Amrane", "massinissa@aures.dz")],
        due="2027-09-18")
    add(money, "Write down what each family has put in so far", hocine, 60)
    add(money, "Price everything that has not been priced", hocine, 35, "2027-07-31")
    add(money, "Agree what we do if we go over", massi, 0)

    # --- a question about work that already exists -------------------------
    #
    # Not a proposal for new work. The rahaba booking exists, somebody has
    # doubts about the second night, and the answer belongs in that task's
    # record rather than in a task of its own.
    second_night = decision.propose(
        hocine["id"], music,
        "Do we need the rahaba on the second night as well?",
        "They are booked for the middle day. The second night is another 90,000 "
        "and the older guests will have gone.",
        ["Both nights, as booked", "The middle day only, and the zerna on the second"],
        about=troupe["id"])
    step(hocine, second_night["id"], "open")
    sn = dm.options_of(second_night["id"])
    decision.remark(lakhdar["id"], second_night["id"],
                    "The second night is when the young men dance. If you want a "
                    "rahaba at all, that is the night it is actually for.", sn[0]["id"])
    decision.remark(hocine["id"], second_night["id"],
                    "90,000 is the water for three days.", sn[1]["id"])
    step(hocine, second_night["id"], "put_to_cell")
    for who, pick in ((lakhdar, 0), (massi, 0), (farid, 1)):
        decision.vote(who["id"], second_night["id"], sn[pick]["id"])

    # --- an open question inside the cell that owns it ---------------------
    menu = decision.propose(
        djamila["id"], food,
        "Chakhchoukha on the middle day, or couscous?",
        "Chakhchoukha is what T'kout expects and it is three days of work by "
        "hand. Couscous for six hundred is one long night.",
        ["Chakhchoukha on the middle day, couscous on the other two",
         "Couscous all three days, and chakhchoukha only for the close family"],
    )
    step(djamila, menu["id"], "open")
    mo = dm.options_of(menu["id"])
    decision.remark(yamina["id"], menu["id"],
                    "If there is no chakhchoukha on the middle day people will say "
                    "so for twenty years. I have eight women. It is doable.",
                    mo[0]["id"])
    decision.remark(zohra["id"], menu["id"],
                    "Eight women for three days is eight women who are not doing "
                    "the other nine things on this list.", mo[1]["id"])
    step(djamila, menu["id"], "put_to_cell")
    for who, pick in ((yamina, 0), (zohra, 1), (djamila, 0), (brahim, 0)):
        decision.vote(who["id"], menu["id"], mo[pick]["id"])

    return wedding


def main():
    cellos.boot()
    if db.value("SELECT count(*) FROM events", default=0):
        print("data/wedding.db already has something in it. Delete it to reseed.")
    else:
        build()
        print("The wedding at T'kout seeded.")

    host, port = "127.0.0.1", int(os.environ["CELLOS_PORT"])
    print("\n  http://%s:%d\n" % (host, port))
    print("  the five who answer for it -- sign in with any name and one of these:\n")
    for who, does in [
        ("salah@aures.dz", "the groom's father"),
        ("djamila@aures.dz", "the bride's mother"),
        ("hocine@aures.dz", "the eldest brother — money, water, the rakb"),
        ("massinissa@aures.dz", "the groom"),
        ("dounia@aures.dz", "the bride"),
    ]:
        print("    %-24s %s" % (who, does))
    print("\n  and some of the fourteen who are in one cell only:\n")
    for who, does in [
        ("yamina@aures.dz", "rolls the chakhchoukha"),
        ("brahim@aures.dz", "the méchoui"),
        ("lakhdar@aures.dz", "leads the rahaba"),
        ("ourida@aures.dz", "knows which house sleeps how many"),
        ("ali@aures.dz", "does the Batna runs"),
    ]:
        print("    %-24s %s" % (who, does))
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
