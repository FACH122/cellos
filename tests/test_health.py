"""
Health: potential, friction, capacity, momentum.

These are diagnostics, not targets, and the numbers in them are a first cut.
So the tests pin the *relationships* -- more people means more potential,
unclaimed work costs more than unstarted work, a cell cannot lose more than it
has -- rather than the exact weights, which are meant to be argued with.
"""

import unittest

from cellos.domains.decision import rules as decision_rules
from cellos.domains.evidence import rules as evidence_rules
from cellos.domains.health import rules
from cellos.domains.task import rules as task_rules


class Potential(unittest.TestCase):

    def test_an_empty_cell_can_do_nothing(self):
        self.assertEqual(rules.potential(0, 0, 0), 0)

    def test_more_people_means_more_potential(self):
        scores = [rules.potential(n, 0, 0) for n in (1, 2, 5, 10, 40)]
        self.assertEqual(scores, sorted(scores))
        self.assertLess(scores[0], scores[-1])

    def test_people_have_diminishing_returns(self):
        second = rules.potential(2, 0, 0) - rules.potential(1, 0, 0)
        twentieth = rules.potential(20, 0, 0) - rules.potential(19, 0, 0)
        self.assertGreater(second, twentieth)

    def test_what_a_cell_has_learned_raises_it(self):
        self.assertGreater(rules.potential(5, 3, 0), rules.potential(5, 0, 0))

    def test_evidence_raises_it(self):
        self.assertGreater(rules.potential(5, 0, 4), rules.potential(5, 0, 0))

    def test_it_never_exceeds_the_scale(self):
        self.assertLessEqual(rules.potential(10000, 100, 100), rules.SCALE)

    def test_it_ignores_everything_that_is_in_the_way(self):
        """Potential is optimistic by definition: friction is a separate number."""
        import inspect
        source = inspect.getsource(rules.potential)
        for word in ("friction", "blocked", "stalled", "waiting"):
            self.assertNotIn(word, source.split('"""')[2])


class Friction(unittest.TestCase):

    def test_nothing_in_the_way_costs_nothing(self):
        self.assertEqual(rules.friction([]), 0)

    def test_signals_add_up(self):
        self.assertEqual(rules.friction([(5, "a"), (3, "b")]), 8)

    def test_a_cell_cannot_lose_more_than_it_has(self):
        heavy = [(50, "a"), (50, "b"), (50, "c")]
        self.assertEqual(rules.friction(heavy, ceiling=30), 30)

    def test_unclaimed_work_costs_more_than_unstarted_work(self):
        untaken = task_rules.friction("open", "X", 0)
        unstarted = task_rules.friction("active", "X", 0, "Sam")
        self.assertGreater(untaken[0][0], unstarted[0][0])

    def test_work_in_progress_costs_nothing(self):
        self.assertEqual(task_rules.friction("active", "X", 40, "Sam"), [])
        self.assertEqual(task_rules.friction("done", "X", 100, "Sam"), [])

    def test_waiting_on_one_person_costs_more_than_waiting_on_everyone(self):
        leader = decision_rules.friction("leader_resolution", "Q")
        cell = decision_rules.friction("voting", "Q")
        self.assertGreater(leader[0][0], cell[0][0])

    def test_a_silent_vote_costs_extra(self):
        quiet = decision_rules.friction("voting", "Q", turnout=1, eligible=10)
        busy = decision_rules.friction("voting", "Q", turnout=9, eligible=10)
        self.assertGreater(sum(p for p, _ in quiet), sum(p for p, _ in busy))

    def test_a_settled_question_costs_nothing(self):
        self.assertEqual(decision_rules.friction("accepted", "Q"), [])

    def test_small_groups_are_not_nagged_about_evidence(self):
        self.assertEqual(evidence_rules.friction("Q", turnout=2, evidence_count=0), [])
        self.assertTrue(evidence_rules.friction("Q", turnout=8, evidence_count=0))
        self.assertEqual(evidence_rules.friction("Q", turnout=8, evidence_count=1), [])

    def test_one_person_holding_everything_is_a_cell_problem(self):
        self.assertEqual(task_rules.overload_friction("Sam", task_rules.OVERLOAD_AT), [])
        self.assertTrue(task_rules.overload_friction("Sam", task_rules.OVERLOAD_AT + 1))

    def test_every_signal_says_something_a_person_could_act_on(self):
        signals = (task_rules.friction("open", "Book the room", 0)
                   + decision_rules.friction("leader_resolution", "Who presents?")
                   + task_rules.overload_friction("Sam", 9))
        for points, reason in signals:
            self.assertGreater(points, 0)
            self.assertGreater(len(reason), 10)
            self.assertNotIn("_", reason)   # no state names leaking into English


class Capacity(unittest.TestCase):

    def test_capacity_is_what_is_left(self):
        self.assertEqual(rules.capacity(70, 20), 50)

    def test_it_never_goes_negative(self):
        self.assertEqual(rules.capacity(20, 90), 0)


class Momentum(unittest.TestCase):

    def test_a_quiet_cell_says_nothing_rather_than_guessing(self):
        self.assertEqual(rules.momentum(1, 1), rules.UNKNOWN)

    def test_speeding_up_is_rising(self):
        self.assertEqual(rules.momentum(40, 10), rules.RISING)

    def test_slowing_down_is_falling(self):
        self.assertEqual(rules.momentum(5, 40), rules.FALLING)

    def test_much_the_same_is_steady(self):
        self.assertEqual(rules.momentum(20, 20), rules.STEADY)


class Health(unittest.TestCase):

    def test_high_capacity_reads_well(self):
        band, _ = rules.health(85, rules.STEADY)
        self.assertEqual(band, "excellent")

    def test_no_capacity_is_critical(self):
        band, _ = rules.health(0, rules.STEADY)
        self.assertEqual(band, "critical")

    def test_losing_ground_reads_worse_than_holding_it(self):
        _, falling = rules.health(60, rules.FALLING)
        _, steady = rules.health(60, rules.STEADY)
        _, rising = rules.health(60, rules.RISING)
        self.assertLess(falling, steady)
        self.assertLess(steady, rising)

    def test_a_cell_at_twenty_percent_but_rising_beats_one_stalled_at_eighty(self):
        """The point of momentum: the level is not the whole story."""
        _, climbing = rules.health(55, rules.RISING)
        _, stalled = rules.health(55, rules.FALLING)
        self.assertGreater(climbing, stalled)

    def test_the_band_is_always_one_of_the_named_ones(self):
        names = {name for _floor, name in rules.BANDS}
        for capacity in range(0, 101, 7):
            for m in (rules.RISING, rules.STEADY, rules.FALLING, rules.UNKNOWN):
                self.assertIn(rules.health(capacity, m)[0], names)


class Attention(unittest.TestCase):

    def test_the_worst_thing_comes_first(self):
        said = rules.attention([(2, "small"), (9, "big"), (5, "middling")])
        self.assertEqual(said[0], "big")

    def test_it_stays_short_enough_to_read(self):
        many = [(i, "thing %d" % i) for i in range(20)]
        self.assertLessEqual(len(rules.attention(many)), 4)

    def test_a_healthy_cell_has_nothing_to_say(self):
        self.assertEqual(rules.attention([]), [])
