#!/usr/bin/env python3
"""
A wedding at a hotel: five people answer for it, twenty-two end up in it.

Amel and Yanis, the Hôtel Panorama in Constantine, 12 June, four hundred
guests, one evening. A cortège, a traiteur, a DJ, a negafa, a photographer, a
videographer with a drone, a pâtissière, a florist, and a banquet manager who
works for the hotel and not for them.

Five answer for the whole of it -- four family and one hired, because a modern
wedding has a professional in the middle of it. Lamia is not staff here. She
leads the venue and the run of the evening, and she has a vote:

    ◎  Marry Amel and Yanis at the Hôtel Panorama on 12 June, four hundred
       guests, one evening, and nothing owed afterwards
       Amel, Yanis, Ryma, Nabil, Lamia -- all five lead
       6,000,000 DZD · 12 June 2027
       │
       ├─ ◎ The room, the tables and the running order
       │     Lamia* + Karim of the hotel, Sabrina on flowers, Ryma · 2,600,000
       │
       ├─ ◎ Four hundred dinners that come out hot and at the same time
       │     Ryma* + Hakim the traiteur, Nawel · 1,900,000
       │     └─ ◎ A cake that survives the room, a sweets table that lasts
       │           Nawel* + Sofia · 180,000
       │
       ├─ ◎ The dresses, the negafa, and the morning of it
       │     Amel* + Djazia the negafa, Meriem on hair · 650,000
       │     └─ ◎ Five dress changes without the evening stopping each time
       │           Djazia* + Sarah · 250,000
       │
       ├─ ◎ The cortège, from the house to the hotel, still together
       │     Nabil* + Sofiane with the cars, Redha driving · 320,000
       │
       ├─ ◎ The DJ, the entrance, and a dance floor that never goes flat
       │     Yanis* + Sami the DJ, Nassim · 480,000
       │     └─ ◎ Getting the couple into the room, in under the time
       │           Nassim* + Bilal on bendir · 150,000
       │
       ├─ ◎ Somebody covering the day who agreed in advance what they cover
       │     Lamia* + Ines on photos, Walid on film and the drone · 420,000
       │
       ├─ ◎ Knowing who is coming before the traiteur needs a number
       │     Ryma* + Lina who prints them · 90,000
       │
       ├─ ◎ The sixty who came from Algiers and Annaba, fed and slept
       │     Nabil* + Farida on reservations · 380,000
       │
       └─ ◎ Knowing what it costs before it is signed
             Yanis* + Nabil, Lamia

Thirteen cells, twenty-two people, sixty-two things to do, six questions.

**Seventeen of the twenty-two never appear on the wedding's own list of
people.** Hakim cooks and is in the dinner cell only. Sami is the DJ. Djazia
is the negafa. Karim works for the hotel, not for the couple, and is in one
cell of theirs. None of them is anywhere near the top and none of them needs
to be -- a cell is not a subset of the cell above it.

Three things are worth watching once it is running:

  · **The parts come to 6,840,000 against a 6,000,000 budget.** Every piece
    has quoted and nothing is signed but the hotel. Nobody added it up; the
    wedding says so on its own page. The question open at the top is *what
    goes* -- cut a hundred guests, drop the video, or put the difference on
    the two families -- and the planner has already said which one every
    wedding she does ends on.

  · **Work cannot be handed to somebody who is not in the cell.** The seating
    plan is Ryma's, and she leads the wedding, and it still would not attach
    to her until she was named in the venue cell. Leading a cell above lets
    you act below; it does not put work in your hands. The money cell brings
    in nobody new and had to name its three anyway.

  · **Nothing here was created.** The first cell grew when this was five
    people, and five can create nothing -- that unlocks at twenty, which the
    wedding only passed once every cell had brought in who it needed. It is
    twenty-two now, which is why a vote at the top no longer settles a
    question on its own and a leader signs it instead. Nobody configured
    that. It grew into it.

For the same wedding done the other way -- three days in a village in the
Aurès, six hundred people, twenty-five sheep, no hotel and no DJ -- see
`aures.py`.

    python3 wedding.py         seed it and serve on 8426
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("CELLOS_DB", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "wedding.db"))
os.environ.setdefault("CELLOS_PORT", "8426")

import cellos  # noqa: E402
from cellos.app import server  # noqa: E402
from cellos.domains.cell import service as cell_service  # noqa: E402
from cellos.domains.decision import model as dm, service as decision  # noqa: E402
from cellos.domains.evidence import service as evidence  # noqa: E402
from cellos.domains.member import service as member  # noqa: E402
from cellos.domains.task import service as task  # noqa: E402
from cellos.kernel import db  # noqa: E402

DZD = "DZD"
DAY = "2027-06-12"


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
    # Four family and one hired. A modern wedding has a professional in the
    # middle of it, and she is not staff here -- she leads the venue and the
    # run of the evening, and the family leads the rest.
    amel = member.register("Amel Ferhat", "amel@mariage.dz")
    w = cell_service.create(
        amel["id"],
        "Marry Amel and Yanis at the Hôtel Panorama in Constantine on 12 June, "
        "four hundred guests, one evening, and nothing owed afterwards")

    five = {}
    for name, email in [
        ("Yanis Meddour", "yanis@mariage.dz"),        # the groom
        ("Ryma Ferhat", "ryma@mariage.dz"),           # the bride's sister, témoin
        ("Nabil Meddour", "nabil@mariage.dz"),        # the groom's brother
        ("Lamia Zerrouki", "lamia@mariage.dz"),       # the wedding planner
    ]:
        five[name.split()[0].lower()] = member.admit(
            amel["id"], w["id"], name, email, member.LEADER)
    yanis, ryma = five["yanis"], five["ryma"]
    nabil, lamia = five["nabil"], five["lamia"]

    cell_service.set_budget(yanis["id"], w["id"], 6_000_000, DZD)
    cell_service.set_deadline(yanis["id"], w["id"], DAY)

    # --- helpers ---------------------------------------------------------

    def ident(cell):
        return cell["id"] if isinstance(cell, dict) else cell

    def add(cell, title, owner, progress=0, due=None, cost=None):
        t = task.create(amel["id"], ident(cell), title)
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
        A piece of work that stopped fitting one person. `joining` is the
        people it brings in who are not upstairs -- the traiteur, the DJ, the
        negafa, the banquet manager. None of them is on the wedding's own
        list of people and none of them needs to be.
        """
        seed_task = add(parent, title, owner)
        task.expand(amel["id"], seed_task["id"], goal)
        cell = task.expanded_into(seed_task["id"])
        brought = {}
        for name, email in joining:
            p = member.admit(amel["id"], cell, name, email)
            brought[name.split()[0].lower()] = p
        if budget:
            cell_service.set_budget(yanis["id"], cell, budget, DZD)
        if due:
            cell_service.set_deadline(yanis["id"], cell, due)
        return cell, brought

    # --- settled: hotel, or a salle des fêtes -----------------------------
    venue_q = decision.propose(
        lamia["id"], w["id"],
        "The hotel, or a salle des fêtes?",
        "A salle is half the price and you bring your own traiteur, your own "
        "decorator and your own problems. The hotel is one contract, one "
        "person to shout at, and rooms for the people who came from Algiers.",
        [
            "The Hôtel Panorama — one contract, rooms included",
            "A salle des fêtes at Ali Mendjeli, and we assemble the rest",
            "The hotel for the dinner, a salle for the afternoon",
        ],
        work={
            "0": ["Sign the hotel contract and read the cancellation clause",
                  "Block thirty rooms for the guests coming from far",
                  "Get the hotel's own list of what is and is not included"],
            "1": ["Find a salle for 12 June", "Find a traiteur", "Find a decorator"],
            "2": ["Price both", "Work out how four hundred people move between them"],
        },
    )
    step(lamia, venue_q["id"], "open")
    vq = dm.options_of(venue_q["id"])
    decision.remark(lamia["id"], venue_q["id"],
                    "A salle in June is booked by January and the good traiteurs go "
                    "with it. If we want a salle we are deciding this week.", vq[1]["id"])
    decision.remark(nabil["id"], venue_q["id"],
                    "Sixty people are coming from Algiers and Annaba. If there are no "
                    "rooms they drive back at two in the morning or they do not come.",
                    vq[0]["id"])
    decision.remark(yanis["id"], venue_q["id"],
                    "The salle is 1,400,000 against 2,600,000. That is a car.",
                    vq[1]["id"])
    evidence.attach(lamia["id"], "option", vq[0]["id"], "note",
                    "Panorama quote: hall, dinner, thirty rooms, 12 June")
    step(lamia, venue_q["id"], "put_to_cell")
    for who, pick in ((amel, 0), (nabil, 0), (ryma, 0), (lamia, 0), (yanis, 1)):
        decision.vote(who["id"], venue_q["id"], vq[pick]["id"])
    step(amel, venue_q["id"], "accept_by_vote", "send_to_leader", "resolve",
         option_id=vq[0]["id"],
         note="Four to one. Yanis is right about the money and outvoted on the rooms.")

    # --- settled and recorded: how long it runs ---------------------------
    length = decision.propose(
        amel["id"], w["id"],
        "One evening, or the henna the night before as well?",
        "The henna is family and close friends, about eighty people, and it is "
        "the night everybody actually enjoys.",
        ["One evening only", "Henna at home on the Friday, the wedding on the Saturday"],
        work={"1": ["Find eighty chairs and somewhere to put them",
                    "Ask Djazia whether she does the henna night too"]},
    )
    step(amel, length["id"], "open")
    step(amel, length["id"], "put_to_cell")
    lo = dm.options_of(length["id"])
    for who in (amel, ryma, lamia, nabil, yanis):
        decision.vote(who["id"], length["id"], lo[1]["id"])
    step(amel, length["id"], "accept_by_vote", "send_to_leader", "resolve",
         option_id=lo[1]["id"],
         note="Unanimous, and it was never really in doubt. It is in here so the "
              "Friday gets a budget instead of being paid for out of surprise.")
    step(amel, length["id"], "record",
         outcome="Henna at home on the Friday, the hotel on the Saturday.",
         lesson="The evening nobody planned is the one that gets paid for twice. "
                "Deciding to have it is what makes it cheap.")

    # --- open, and the one that actually matters --------------------------
    #
    # Every part has now quoted, and together they quote more than the whole.
    cut = decision.propose(
        yanis["id"], w["id"],
        "We are over. What goes?",
        "Everything that has quoted comes to more than the budget, and nothing "
        "has been signed yet except the hotel. Three ways out, and one of them "
        "is not really a way out.",
        [
            "Four hundred becomes three hundred",
            "Drop the video — keep the photographer, lose the film and the drone",
            "Keep everything and put the difference on the two families",
        ],
        work={
            "0": ["Cut the guest list, and tell people before the invitations go out"],
            "1": ["Tell Walid before he blocks the date"],
            "2": ["Agree in writing who covers what, now and not in July"],
        },
    )
    step(yanis, cut["id"], "open")
    co = dm.options_of(cut["id"])
    decision.remark(yanis["id"], cut["id"],
                    "A hundred guests is 190,000 of dinner alone. It is the only "
                    "option that closes the gap on its own.", co[0]["id"])
    decision.remark(amel["id"], cut["id"],
                    "You cannot uninvite a hundred people in Constantine. Whatever we "
                    "save we pay for in twenty years of who was left out.", co[0]["id"])
    decision.remark(ryma["id"], cut["id"],
                    "The film is the only thing you still have in ten years. The "
                    "drone I would drop tomorrow.", co[1]["id"])
    evidence.attach(yanis["id"], "option", co[0]["id"], "measurement",
                    "Cost per couvert × 100, against the 840,000 gap")
    decision.remark(lamia["id"], cut["id"],
                    "Every wedding I do ends on the third option. I would rather you "
                    "chose it in April than discovered it in June.", co[2]["id"])
    step(yanis, cut["id"], "put_to_cell")
    for who, pick in ((ryma, 1), (lamia, 2), (yanis, 0), (amel, 1)):
        decision.vote(who["id"], cut["id"], co[pick]["id"])

    # Work the two settled questions made, picked up by whoever it belongs to.
    made = {t["title"]: t for t in task.in_cells([w["id"]])}
    for title, owner, progress in [
        ("Sign the hotel contract and read the cancellation clause", lamia, 100),
        ("Block thirty rooms for the guests coming from far", nabil, 45),
        ("Get the hotel's own list of what is and is not included", lamia, 70),
        ("Find eighty chairs and somewhere to put them", ryma, 20),
    ]:
        t = made.get(title)
        if t:
            task.assign(owner["id"], t["id"], owner["id"])
            if progress:
                task.report_progress(owner["id"], t["id"], progress)

    # ------------------------------------------------------------------
    # The cells. Not one of them was created. The first was grown when this
    # was a cell of five, and five cannot create anything -- that unlocks at
    # twenty, which the wedding only passed once every cell had brought in
    # the people it needed. Expansion works at any size, which is the only
    # reason this shape exists at all.
    # ------------------------------------------------------------------

    # 1. The venue and the run of the evening.
    venue, p = grew(
        w, "Run the hotel side of it", lamia,
        "Have the room, the tables and the running order settled so nobody is "
        "improvising on the night",
        [("Karim Lounis", "karim@mariage.dz"),        # the hotel's banquet manager
         ("Sabrina Adjali", "sabrina@mariage.dz"),    # decor and flowers
         # Upstairs already, and named here anyway: the seating plan is hers,
         # and work cannot be put in the hands of somebody who is not in the
         # cell, however senior they are above it.
         ("Ryma Ferhat", "ryma@mariage.dz")],
        budget=2_600_000, due="2027-06-05")
    karim, sabrina = p["karim"], p["sabrina"]
    plan = add(venue, "Do the seating plan for four hundred", ryma, 25, "2027-05-25")
    add(venue, "Agree the running order with the hotel, hour by hour", lamia, 60,
        "2027-05-30")
    add(venue, "The centrepieces and what happens to them after", sabrina, 40,
        "2027-06-01", 340_000)
    add(venue, "Walk the room and count the plugs the DJ will need", karim, 80)
    add(venue, "Agree what time the hotel wants everybody out", karim, 100, "2027-04-20")
    task.note(ryma["id"], plan["id"],
              "Four hundred people is forty tables of ten. The problem is not the "
              "tables, it is that six families cannot be seated near each other and "
              "two of them do not know that yet.")

    # 2. Dinner.
    dinner, p = grew(
        w, "Sort out the dinner", ryma,
        "Feed four hundred people a dinner that comes out hot and at the same time",
        [("Hakim Tounsi", "hakim@mariage.dz"),        # the traiteur
         ("Nawel Saadi", "nawel@mariage.dz")],        # pâtissière
        budget=1_900_000, due="2027-06-10")
    hakim, nawel = p["hakim"], p["nawel"]
    add(dinner, "Taste the menu and agree it in writing", ryma, 75, "2027-04-15")
    add(dinner, "Count the vegetarians and the allergies from the RSVPs", ryma, 30)
    add(dinner, "Agree how many servers for four hundred", hakim, 50)
    add(dinner, "Decide the soft bar and who tops it up during the evening", hakim, 20)

    # 2a. The cake and the sweets table became their own thing.
    sweets, p = grew(
        dinner, "The pièce montée and the sweets table", nawel,
        "Have a cake that survives the room and a sweets table that does not run out "
        "at eleven",
        [("Sofia Bendaoud", "sofia@mariage.dz")],     # does the traditional sweets
        budget=180_000, due="2027-06-11")
    sofia = p["sofia"]
    add(sweets, "Agree the cake, and how many tiers are real", nawel, 60, "2027-05-10",
        95_000)
    add(sweets, "Work out how it gets to the room without collapsing", nawel, 10)
    add(sweets, "The traditional sweets — how many trays, made when", sofia, 45)

    # 3. The bride.
    look, p = grew(
        w, "Get the bride's side ready", amel,
        "Have the dresses, the negafa and the morning of it planned so Amel is not "
        "organising her own wedding on the day",
        [("Djazia Belkhir", "djazia@mariage.dz"),     # the negafa
         ("Meriem Ait Said", "meriem@mariage.dz")],   # hair and makeup
        budget=650_000, due="2027-06-11")
    djazia, meriem = p["djazia"], p["meriem"]
    robe = add(look, "The white dress — find it, and have it fitted twice", amel, 70,
               "2027-05-01", 220_000)
    add(look, "The karakou and the chedda, and whose they are", djazia, 55)
    add(look, "Trial the hair and makeup, properly, in daylight", meriem, 40, "2027-05-15")
    add(look, "Work out the morning — what time everything starts", amel, 15)
    task.note(amel["id"], robe["id"],
              "Second fitting is three weeks before. The shop wants the balance at "
              "the second fitting, not on collection.")

    # 3a. The dress changes on the night are their own operation.
    changes, p = grew(
        look, "Plan the dress changes on the night", djazia,
        "Get the bride through five changes without the evening stopping each time",
        [("Sarah Meddour", "sarah@mariage.dz")],      # the groom's cousin, helps
        budget=250_000, due="2027-06-11")
    sarah = p["sarah"]
    add(changes, "Agree the order of the outfits with the DJ's running order", djazia, 30)
    add(changes, "Get a room near the hall, not upstairs", sarah, 0, "2027-05-20")
    add(changes, "Work out who carries what, and who holds the jewellery", sarah, 20)

    # 4. The cortège.
    cortege, p = grew(
        w, "Sort out the cortège", nabil,
        "Get the cortège from the house to the hotel without losing half of it at "
        "the lights",
        [("Sofiane Kaci", "sofiane@mariage.dz"),      # supplies the cars
         ("Redha Belhadj", "redha@mariage.dz")],      # drives the lead car
        budget=320_000, due="2027-06-11")
    sofiane, redha = p["sofiane"], p["redha"]
    add(cortege, "Book the cars and see them first, not in photographs", sofiane, 65,
        "2027-05-05", 260_000)
    route = add(cortege, "Decide the route and drive it at the same hour", redha, 100,
                "2027-05-18")
    add(cortege, "Work out who is in which car and tell them", nabil, 20)
    add(cortege, "Agree what the cortège does if it rains", redha, 0)

    # Settled inside the cell that owns it, and recorded.
    road = decision.propose(
        nabil["id"], cortege,
        "Through the centre, or round by the viaduct?",
        "The centre is shorter and it is Constantine at six in the evening. The "
        "viaduct is twenty minutes longer and the cortège stays together.",
        ["Through the centre", "Round by the viaduct"],
        work={"0": ["Warn every driver about the two lights that split convoys"],
              "1": ["Drive it once at the same hour on a Saturday"]},
    )
    step(nabil, road["id"], "open")
    ro = dm.options_of(road["id"])
    decision.remark(redha["id"], road["id"],
                    "Twelve cars through the centre at six is not a cortège, it is "
                    "twelve cars that all arrive separately.", ro[1]["id"])
    evidence.attach(redha["id"], "option", ro[1]["id"], "note",
                    "Drove both on a Saturday in April: 18 min against 34, but "
                    "nothing split on the viaduct")
    step(nabil, road["id"], "put_to_cell")
    for who in (sofiane, redha, nabil):
        decision.vote(who["id"], road["id"], ro[1]["id"])
    step(nabil, road["id"], "accept_by_vote", "send_to_leader", "resolve",
         option_id=ro[1]["id"],
         note="Longer, and everybody arrives together, which is the entire point.")
    step(nabil, road["id"], "record",
         outcome="The viaduct. Held together both times it was driven.",
         lesson="A cortège is not measured by when the first car arrives.")

    # 5. Music, the DJ and the dance floor.
    music, p = grew(
        w, "Sort out the music", yanis,
        "Have the DJ, the entrance and the dance floor run so the evening never "
        "goes flat",
        [("Sami Aloui", "sami@mariage.dz"),           # the DJ
         ("Nassim Berrah", "nassim@mariage.dz")],     # leads the zaffa
        budget=480_000, due="2027-06-11")
    sami, nassim = p["sami"], p["nassim"]
    dj = add(music, "Book the DJ and hear him somewhere else first", yanis, 100,
             "2027-03-20", 300_000)
    add(music, "Give the DJ the running order and the five things not to play", yanis, 35)
    add(music, "Agree the sound with the hotel — their limiter, his desk", sami, 50)
    add(music, "Work out the first dance, and whether there is one", yanis, 0)

    # 5a. The entrance became its own thing, as it always does.
    zaffa, p = grew(
        music, "Plan the entrance", nassim,
        "Get the couple into the room in a way people remember, without it running "
        "twenty minutes long",
        [("Bilal Rahmani", "bilal@mariage.dz")],      # bendir and the troupe
        budget=150_000, due="2027-06-11")
    bilal = p["bilal"]
    add(zaffa, "Agree the troupe and how many of them", nassim, 70, "2027-05-12")
    add(zaffa, "Time it — it cannot be longer than the doors are open", bilal, 25)
    add(zaffa, "Agree the handover from the zaffa to the DJ", bilal, 0)

    # 6. Photo and video.
    photo, p = grew(
        w, "Sort out the photos and the film", lamia,
        "Have somebody covering the day who has agreed in advance what they are "
        "covering",
        [("Ines Merabet", "ines@mariage.dz"),         # photographer
         ("Walid Cherif", "walid@mariage.dz")],       # video and the drone
        budget=420_000, due="2027-06-11")
    ines, walid = p["ines"], p["walid"]
    add(photo, "Book the photographer and see a whole wedding, not a portfolio",
        lamia, 100, "2027-03-10", 240_000)
    drone = add(photo, "Book the video, the film and the drone", walid, 30, "2027-05-01",
                180_000)
    add(photo, "Agree the shot list, including the family groups", ines, 45)
    add(photo, "Find out whether the hotel allows a drone at all", walid, 0, "2027-05-05")

    # 7. Invitations and the guest list.
    invites, p = grew(
        w, "Do the invitations and the list", ryma,
        "Know who is actually coming before the traiteur needs a number",
        [("Lina Haddad", "lina@mariage.dz")],         # designs and prints them
        budget=90_000, due="2027-04-30")
    lina = p["lina"]
    add(invites, "Agree the list between the two families", ryma, 60, "2027-04-01")
    add(invites, "Design and print them", lina, 80, "2027-04-10", 62_000)
    add(invites, "Deliver them by hand where it matters", ryma, 30)
    add(invites, "Chase the RSVPs, twice, and then a third time", lina, 15, "2027-05-20")

    # 8. Where people sleep, and the day after.
    guests, p = grew(
        w, "Look after the people who came from far", nabil,
        "Have the sixty who came from Algiers and Annaba fed, slept and not "
        "wondering where to go",
        [("Farida Ould Kaci", "farida@mariage.dz")],  # does the hotel reservations
        budget=380_000, due="2027-06-11")
    farida = p["farida"]
    add(guests, "Match the thirty rooms to the sixty people", farida, 40, "2027-05-25")
    add(guests, "Organise the brunch on the Sunday", nabil, 10)
    add(guests, "Tell people how to get from the airport", farida, 0)

    # 9. The money. Brings nobody new -- and its three still had to be named,
    #    because leading a cell above lets you act below but does not put work
    #    in your hands.
    money, _ = grew(
        w, "Keep track of what this costs", yanis,
        "Know what this costs before it is signed, and who is covering what",
        [("Nabil Meddour", "nabil@mariage.dz"),
         ("Lamia Zerrouki", "lamia@mariage.dz")],
        due=DAY)
    add(money, "Put every quote in one place with a date on it", yanis, 70, "2027-04-25")
    add(money, "Work out what is already non-refundable", yanis, 40)
    add(money, "Agree in writing who covers what", nabil, 0)

    # --- a question about work that already exists -------------------------
    #
    # The video is booked. Somebody has doubts about the drone specifically.
    # The answer belongs in that task's record, not in a task of its own.
    drone_q = decision.propose(
        yanis["id"], photo,
        "Do we keep the drone?",
        "It is 60,000 of the 180,000, the hotel has not said yes to it, and it is "
        "the first thing on the list when we need to find money.",
        ["Keep it", "Drop the drone, keep the film"],
        about=drone["id"])
    step(yanis, drone_q["id"], "open")
    dq = dm.options_of(drone_q["id"])
    decision.remark(walid["id"], drone_q["id"],
                    "The drone is the opening thirty seconds and it is the shot "
                    "everybody sends to everybody. Without it the film opens on a "
                    "car park.", dq[0]["id"])
    decision.remark(yanis["id"], drone_q["id"],
                    "The hotel has not confirmed it is allowed. We may be arguing "
                    "about something that cannot happen.", dq[1]["id"])
    step(yanis, drone_q["id"], "put_to_cell")
    for who, pick in ((walid, 0), (ines, 1), (lamia, 1)):
        decision.vote(who["id"], drone_q["id"], dq[pick]["id"])

    # --- an open question inside the cell that owns it ---------------------
    service = decision.propose(
        ryma["id"], dinner,
        "Served at the table, or a buffet?",
        "Four hundred people served at the table needs forty servers and takes an "
        "hour and a half. A buffet takes twenty minutes and a queue.",
        ["Served at the table", "Buffet", "Starter and dessert served, main as a buffet"],
    )
    step(ryma, service["id"], "open")
    so = dm.options_of(service["id"])
    decision.remark(hakim["id"], service["id"],
                    "Forty servers for four hundred is what it takes and it is why "
                    "it costs what it costs. Thirty and the last table eats cold.",
                    so[0]["id"])
    decision.remark(lamia["id"], service["id"],
                    "An hour and a half of service in the middle of the evening is "
                    "an hour and a half the dance floor is empty.", so[1]["id"])
    decision.remark(amel["id"], service["id"],
                    "A queue at my wedding. No.", so[0]["id"])
    step(ryma, service["id"], "put_to_cell")
    for who, pick in ((hakim, 0), (amel, 0), (lamia, 2), (ryma, 2)):
        decision.vote(who["id"], service["id"], so[pick]["id"])

    return w


def main():
    cellos.boot()
    if db.value("SELECT count(*) FROM events", default=0):
        print("data/wedding.db already has something in it. Delete it to reseed.")
    else:
        build()
        print("The wedding at the Hôtel Panorama seeded.")

    host, port = "127.0.0.1", int(os.environ["CELLOS_PORT"])
    print("\n  http://%s:%d\n" % (host, port))
    print("  the five who answer for it:\n")
    for who, does in [
        ("amel@mariage.dz", "the bride"),
        ("yanis@mariage.dz", "the groom — and the money"),
        ("ryma@mariage.dz", "the bride's sister — dinner, the list, the seating"),
        ("nabil@mariage.dz", "the groom's brother — the cortège and the guests"),
        ("lamia@mariage.dz", "the wedding planner — the venue and the evening"),
    ]:
        print("    %-24s %s" % (who, does))
    print("\n  and some of the fourteen who are in one cell only:\n")
    for who, does in [
        ("hakim@mariage.dz", "the traiteur"),
        ("sami@mariage.dz", "the DJ"),
        ("djazia@mariage.dz", "the negafa"),
        ("walid@mariage.dz", "video and the drone"),
        ("karim@mariage.dz", "the hotel's banquet manager"),
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
