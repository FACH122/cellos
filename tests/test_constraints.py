"""
Constraints: an optional budget on a cell, an optional deadline on a task.

Optional is the load-bearing word. A cell that never set a budget is not a
cell at zero percent spent -- it is a cell the question does not apply to, and
it must never be asked about it.
"""

import datetime
import unittest

from cellos.domains.cell import rules as cell_rules, service as cell_service
from cellos.domains.constraints import rules, service as constraints
from cellos.domains.health import service as health
from cellos.domains.member import service as member
from cellos.domains.task import rules as task_rules, service as task
from cellos.kernel.errors import DomainError, NotAllowed

TODAY = datetime.date(2026, 6, 10)
_n = [0]


def a_cell(people=3):
    _n[0] += 1
    boss = member.register("Owner %d" % _n[0], "owner%d@test.invalid" % _n[0])
    c = cell_service.create(boss["id"], "Run an event %d" % _n[0])
    crew = [member.admit(boss["id"], c["id"], "C%d-%d" % (_n[0], i),
                         "c%d-%d@test.invalid" % (_n[0], i)) for i in range(people - 1)]
    return boss, c, crew


class Validation(unittest.TestCase):

    def test_no_budget_is_not_a_budget_of_zero(self):
        self.assertEqual(cell_rules.clean_budget(None, None), (None, None))
        self.assertEqual(cell_rules.clean_budget(0, "EUR"), (0.0, "EUR"))

    def test_a_budget_is_a_number(self):
        for bad in ("lots", "-1", -5):
            with self.assertRaises(DomainError):
                cell_rules.clean_budget(bad, "EUR")

    def test_a_deadline_is_a_date_or_nothing(self):
        self.assertEqual(task_rules.clean_deadline("2026-12-05"), "2026-12-05")
        self.assertIsNone(task_rules.clean_deadline(""))
        with self.assertRaises(DomainError):
            task_rules.clean_deadline("next tuesday")

    def test_a_cost_is_a_number_or_nothing(self):
        self.assertEqual(task_rules.clean_cost("12.5"), 12.5)
        self.assertIsNone(task_rules.clean_cost(None))
        with self.assertRaises(DomainError):
            task_rules.clean_cost("free")


class Optional(unittest.TestCase):

    def test_a_cell_with_no_commitments_is_asked_about_none(self):
        _boss, c, _crew = a_cell()
        self.assertIsNone(constraints.of_cell(c["id"]))
        self.assertIsNone(constraints.budget_of(c["id"]))

    def test_an_unconstrained_cell_carries_no_constraint_friction(self):
        boss, c, _crew = a_cell()
        t = task.create(boss["id"], c["id"], "Something")
        task.assign(boss["id"], t["id"], boss["id"])
        self.assertEqual(constraints.friction(c["id"]), [])

    def test_a_budget_can_be_dropped_again(self):
        boss, c, _crew = a_cell()
        cell_service.set_budget(boss["id"], c["id"], 500, "EUR")
        self.assertIsNotNone(constraints.budget_of(c["id"]))
        cell_service.set_budget(boss["id"], c["id"], None)
        self.assertIsNone(constraints.budget_of(c["id"]))

    def test_only_a_leader_commits_the_cell_to_spending(self):
        boss, c, crew = a_cell()
        with self.assertRaises(NotAllowed):
            cell_service.set_budget(crew[0]["id"], c["id"], 500, "EUR")


class Spending(unittest.TestCase):

    def test_spend_is_the_sum_of_what_the_work_cost(self):
        boss, c, _crew = a_cell()
        cell_service.set_budget(boss["id"], c["id"], 1000, "EUR")
        for title, cost in (("Venue", 600), ("Food", 250)):
            t = task.create(boss["id"], c["id"], title)
            task.assign(boss["id"], t["id"], boss["id"])
            task.record_cost(boss["id"], t["id"], cost)

        money = constraints.budget_of(c["id"])
        self.assertEqual(money["spent"], 850)
        self.assertEqual(money["remaining"], 150)
        self.assertEqual(money["share"], 85)
        self.assertFalse(money["over"])

    def test_spend_rolls_up_from_the_cells_inside(self):
        boss, c, crew = a_cell(people=25)
        cell_service.set_budget(boss["id"], c["id"], 1000, "EUR")
        big = task.create(boss["id"], c["id"], "A whole workstream")
        task.assign(boss["id"], big["id"], crew[0]["id"])
        inner_cell = task.expand(boss["id"], big["id"])

        inner = task.create(crew[0]["id"], inner_cell["id"], "Part of it")
        task.assign(crew[0]["id"], inner["id"], crew[0]["id"])
        task.record_cost(crew[0]["id"], inner["id"], 400)

        self.assertEqual(constraints.budget_of(c["id"])["spent"], 400)

    def test_going_over_is_noticed_and_said_plainly(self):
        boss, c, _crew = a_cell()
        cell_service.set_budget(boss["id"], c["id"], 100, "EUR")
        t = task.create(boss["id"], c["id"], "Venue")
        task.assign(boss["id"], t["id"], boss["id"])
        task.record_cost(boss["id"], t["id"], 130)

        money = constraints.budget_of(c["id"])
        self.assertTrue(money["over"])
        said = [r for _p, r in constraints.friction(c["id"])]
        self.assertTrue(any("over by" in r for r in said), said)

    def test_a_nearly_spent_budget_with_nothing_left_to_do_is_not_a_problem(self):
        """Tight only matters when there is still work to pay for."""
        self.assertEqual(rules.budget_friction(95, 100, "EUR", remaining_work=0), [])
        self.assertTrue(rules.budget_friction(95, 100, "EUR", remaining_work=3))


class Deadlines(unittest.TestCase):

    def test_a_passed_date_on_unfinished_work_is_late(self):
        said = rules.deadline_friction("Book the venue", "2026-06-07", TODAY, progress=0)
        self.assertEqual(len(said), 1)
        self.assertIn("3 days ago", said[0][1])

    def test_an_imminent_date_on_unstarted_work_is_worth_saying(self):
        said = rules.deadline_friction("Book it", "2026-06-11", TODAY, progress=0)
        self.assertIn("tomorrow", said[0][1])

    def test_an_imminent_date_on_work_already_moving_is_not(self):
        self.assertEqual(rules.deadline_friction("Book it", "2026-06-11", TODAY, progress=60), [])

    def test_a_distant_date_costs_nothing(self):
        self.assertEqual(rules.deadline_friction("Book it", "2026-09-01", TODAY, progress=0), [])

    def test_late_work_costs_more_than_imminent_work(self):
        late = rules.deadline_friction("X", "2026-06-01", TODAY, 0)
        soon = rules.deadline_friction("X", "2026-06-12", TODAY, 0)
        self.assertGreater(late[0][0], soon[0][0])

    def test_finished_work_is_never_late(self):
        boss, c, _crew = a_cell()
        t = task.create(boss["id"], c["id"], "Done thing")
        task.assign(boss["id"], t["id"], boss["id"])
        task.set_deadline(boss["id"], t["id"], "2020-01-01")
        task.report_progress(boss["id"], t["id"], 100)
        self.assertEqual(constraints.deadlines_in([c["id"]])["late"], [])


class FeedsHealth(unittest.TestCase):

    def test_a_missed_date_shows_up_as_something_needing_attention(self):
        boss, c, _crew = a_cell()
        t = task.create(boss["id"], c["id"], "Book the venue")
        task.assign(boss["id"], t["id"], boss["id"])
        task.set_deadline(boss["id"], t["id"], "2020-01-01")

        reading = health.of_cell(c["id"])
        self.assertTrue(any("was due" in a for a in reading["attention"]), reading["attention"])

    def test_commitments_drag_on_health_like_anything_else(self):
        boss, c, _crew = a_cell()
        before = health.of_cell(c["id"])["friction"]
        cell_service.set_budget(boss["id"], c["id"], 10, "EUR")
        t = task.create(boss["id"], c["id"], "Venue")
        task.assign(boss["id"], t["id"], boss["id"])
        task.record_cost(boss["id"], t["id"], 500)
        self.assertGreater(health.of_cell(c["id"])["friction"], before)

    def test_nothing_is_enforced_only_noticed(self):
        """CellOS never blocks the spend. It says so and the cell decides."""
        boss, c, _crew = a_cell()
        cell_service.set_budget(boss["id"], c["id"], 10, "EUR")
        t = task.create(boss["id"], c["id"], "Expensive")
        task.assign(boss["id"], t["id"], boss["id"])
        task.record_cost(boss["id"], t["id"], 99999)      # allowed
        self.assertTrue(constraints.budget_of(c["id"])["over"])
