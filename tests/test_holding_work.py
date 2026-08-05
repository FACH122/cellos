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
from cellos.domains.task import rules, service as task
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
