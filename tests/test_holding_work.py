"""
Who holds a piece of work, and who may change that.

Every one of these came out of ten people using the system at once on a real
question. The event log afterwards showed three of them had "taken" the same
task in turn, each silently displacing the last: two people believed they were
writing the test protocol and only one of them was. Nothing in the system had
objected, and nothing in this suite had noticed.

Unheld work is meant to be picked up freely -- that is what leaving it unowned
is for. What must not happen is work quietly leaving the hands it is in.
"""

import unittest

from cellos.domains.cell import service as cell_service
from cellos.domains.member import service as member
from cellos.domains.task import model, rules, service as task
from cellos.kernel.errors import NotAllowed

_n = [0]


def a_cell(people=4):
    _n[0] += 1
    tag = _n[0]
    boss = member.register("Lead %d" % tag, "hlead%d@test.invalid" % tag)
    c = cell_service.create(boss["id"], "Ship the thing %d" % tag)
    crew = [
        member.admit(boss["id"], c["id"], "H%d-%d" % (tag, i), "h%d-%d@test.invalid" % (tag, i))
        for i in range(people - 1)
    ]
    return boss, c, crew


class TheRule(unittest.TestCase):
    """The pure rule, with no database in the way."""

    def test_picking_up_unheld_work_needs_nobody_s_permission(self):
        self.assertIsNone(rules.check_assignment(None, None, "me", "me", False))

    def test_taking_work_out_of_someone_else_s_hands_is_refused(self):
        refusal = rules.check_assignment("Kenji", "kenji", "nadia", "nadia", False)
        self.assertIn("Kenji has that", refusal)

    def test_the_refusal_names_who_to_ask(self):
        refusal = rules.check_assignment("Kenji", "kenji", "nadia", "nadia", False)
        self.assertIn("Ask them", refusal)

    def test_putting_down_work_you_are_holding_is_yours_to_do(self):
        self.assertIsNone(rules.check_assignment("Me", "me", "me", None, False))

    def test_putting_down_work_you_are_not_holding_is_refused(self):
        self.assertIsNotNone(rules.check_assignment("Kenji", "kenji", "nadia", None, False))

    def test_a_leader_may_move_work_between_any_hands(self):
        self.assertIsNone(rules.check_assignment("Kenji", "kenji", "boss", "nadia", True))

    def test_a_member_may_not_hand_work_to_a_third_person(self):
        refusal = rules.check_assignment(None, None, "me", "someone_else", False)
        self.assertIn("Only a leader", refusal)


class ThroughTheSystem(unittest.TestCase):

    def test_the_three_way_theft_that_started_this(self):
        """
        The exact sequence out of the battery cell's event log: Kenji takes
        it, then Nadia takes it, then Wei takes it, and nobody is told.
        """
        boss, cell, crew = a_cell()
        kenji, nadia, wei = crew[0], crew[1], crew[2] if len(crew) > 2 else crew[0]
        t = task.create(boss["id"], cell["id"], "Write the test protocol")

        task.assign(kenji["id"], t["id"], kenji["id"])
        self.assertEqual(task.get(t["id"])["owner_id"], kenji["id"])

        with self.assertRaises(NotAllowed) as caught:
            task.assign(nadia["id"], t["id"], nadia["id"])
        self.assertIn("has that", str(caught.exception))

        # And it really did not move.
        self.assertEqual(task.get(t["id"])["owner_id"], kenji["id"])

    def test_unheld_work_is_still_free_to_pick_up(self):
        boss, cell, crew = a_cell()
        t = task.create(boss["id"], cell["id"], "Spec the enclosure")
        task.assign(crew[0]["id"], t["id"], crew[0]["id"])
        self.assertEqual(task.get(t["id"])["owner_id"], crew[0]["id"])

    def test_work_put_down_can_be_picked_up_by_the_next_person(self):
        boss, cell, crew = a_cell()
        t = task.create(boss["id"], cell["id"], "Chase the supplier")
        task.assign(crew[0]["id"], t["id"], crew[0]["id"])
        task.assign(crew[0]["id"], t["id"], None)          # hands it back
        task.assign(crew[1]["id"], t["id"], crew[1]["id"])  # somebody else takes it
        self.assertEqual(task.get(t["id"])["owner_id"], crew[1]["id"])

    def test_a_leader_can_move_work_that_is_stuck_in_someone_s_hands(self):
        boss, cell, crew = a_cell()
        t = task.create(boss["id"], cell["id"], "Run the aging campaign")
        task.assign(crew[0]["id"], t["id"], crew[0]["id"])
        task.assign(boss["id"], t["id"], crew[1]["id"])
        self.assertEqual(task.get(t["id"])["owner_id"], crew[1]["id"])


class SayingWhatIsHappening(unittest.TestCase):
    """
    A task page is the one screen somebody sits at. Until now the only thing
    it could accept was a number: a person could move progress from 40 to 55
    and had nowhere to say why, or what they were stuck behind.
    """

    def test_a_note_needs_something_in_it(self):
        from cellos.kernel.errors import DomainError
        for empty in ("", "   ", None):
            with self.assertRaises(DomainError):
                rules.clean_note(empty)

    def test_a_note_stops_before_it_becomes_a_report(self):
        from cellos.kernel.errors import DomainError
        with self.assertRaises(DomainError) as caught:
            rules.clean_note("x" * (rules.MAX_NOTE + 1))
        self.assertIn("probably evidence", str(caught.exception))

    def test_anybody_in_the_cell_may_say_something(self):
        """
        Not only whoever holds it. Being blocked by somebody else's work is
        exactly when you most need to say so.
        """
        boss, cell, crew = a_cell()
        t = task.create(boss["id"], cell["id"], "Wait on the vendor")
        task.assign(crew[0]["id"], t["id"], crew[0]["id"])

        task.note(crew[1]["id"], t["id"], "Their quote assumes we host the runner.")
        said = task.note(crew[0]["id"], t["id"], "Revised quote in, 20% lower.")

        self.assertEqual(len(said), 2)
        self.assertEqual(said[0]["body"], "Their quote assumes we host the runner.")
        self.assertEqual(said[1]["author_id"], crew[0]["id"])

    def test_a_stranger_may_not(self):
        from cellos.kernel.errors import NotAllowed
        boss, cell, _ = a_cell()
        outsider = member.register("Outside", "outside@test.invalid")
        t = task.create(boss["id"], cell["id"], "Something")
        with self.assertRaises(NotAllowed):
            task.note(outsider["id"], t["id"], "hello")

    def test_notes_survive_a_replay(self):
        """
        They are a projection like everything else -- the log is the authority,
        and dropping every derived table has to bring them back.
        """
        from cellos.kernel import events as event_log

        boss, cell, _ = a_cell()
        t = task.create(boss["id"], cell["id"], "Chase the supplier")
        task.note(boss["id"], t["id"], "Left a voicemail.")

        event_log.replay()
        again = model.notes_of(t["id"])
        self.assertEqual([n["body"] for n in again], ["Left a voicemail."])


class AskingAboutWork(unittest.TestCase):
    """
    A question can be raised *about* work that already exists.

    The ordinary flow is unchanged: a question is settled and the work it
    commits to appears, linked by `produces`. This is the other direction --
    the work is already there and somebody wants to argue about it. Two
    different facts, so two different edges.
    """

    def test_a_question_can_concern_existing_work(self):
        from cellos.domains.decision import service as decision

        boss, cell, _ = a_cell()
        t = task.create(boss["id"], cell["id"], "Stand up the new service")
        d = decision.propose(boss["id"], cell["id"],
                             "Is this still worth finishing?", "",
                             ["Keep going", "Stop"], about=t["id"])

        asked = decision.questions_about(t["id"])
        self.assertEqual([q["id"] for q in asked], [d["id"]])

    def test_it_is_not_the_decision_the_work_came_from(self):
        """
        `because` answers "why does this exist". A question raised later is
        something that happened to it, and must not be mistaken for its origin.
        """
        from cellos.domains.decision import service as decision

        boss, cell, _ = a_cell()
        t = task.create(boss["id"], cell["id"], "Chase the vendor")
        decision.propose(boss["id"], cell["id"], "Still worth it?", "",
                         ["Yes", "No"], about=t["id"])

        self.assertIsNone(decision.decision_of_task(t["id"]))

    def test_work_can_be_argued_over_more_than_once(self):
        from cellos.domains.decision import service as decision

        boss, cell, _ = a_cell()
        t = task.create(boss["id"], cell["id"], "Run the campaign")
        decision.propose(boss["id"], cell["id"], "Pause it?", "", ["Yes", "No"], about=t["id"])
        decision.propose(boss["id"], cell["id"], "Resume it?", "", ["Yes", "No"], about=t["id"])

        self.assertEqual(len(decision.questions_about(t["id"])), 2)

    def test_a_question_about_nothing_is_still_an_ordinary_question(self):
        from cellos.domains.decision import service as decision

        boss, cell, _ = a_cell()
        d = decision.propose(boss["id"], cell["id"], "Where do we meet?", "",
                             ["Here", "There"])
        self.assertEqual(decision.questions_about(d["id"]), [])
