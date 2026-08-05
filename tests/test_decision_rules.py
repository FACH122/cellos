"""
How a vote is read, and when a leader is confirming the cell rather than
overruling it. These are the rules the ninth principle rests on.
"""

import unittest

from cellos.domains.decision import rules
from cellos.kernel.errors import DomainError


class Tally(unittest.TestCase):

    def test_no_votes_has_no_winner(self):
        result = rules.tally({})
        self.assertEqual(result["total"], 0)
        self.assertIsNone(result["winner"])
        self.assertFalse(result["tied"])

    def test_a_clear_majority_wins(self):
        result = rules.tally({"a": 7, "b": 3})
        self.assertEqual(result["winner"], "a")
        self.assertEqual(result["total"], 10)
        self.assertFalse(result["tied"])

    def test_a_tie_has_no_winner(self):
        result = rules.tally({"a": 5, "b": 5})
        self.assertIsNone(result["winner"])
        self.assertTrue(result["tied"])

    def test_a_plurality_wins_without_a_majority(self):
        result = rules.tally({"a": 4, "b": 3, "c": 3})
        self.assertEqual(result["winner"], "a")

    def test_options_with_no_votes_are_not_counted_as_tying(self):
        result = rules.tally({"a": 2, "b": 0})
        self.assertEqual(result["winner"], "a")
        self.assertFalse(result["tied"])


class HowDecided(unittest.TestCase):

    def test_with_no_votes_a_person_decided(self):
        result = rules.tally({})
        self.assertEqual(rules.how_decided(result, "a", ""), rules.BY_LEADER)

    def test_a_tie_broken_by_a_leader_is_not_recorded_as_a_vote(self):
        result = rules.tally({"a": 3, "b": 3})
        self.assertEqual(rules.how_decided(result, "a", ""), rules.BY_LEADER)

    def test_choosing_the_winner_confirms_the_vote(self):
        result = rules.tally({"a": 9, "b": 1})
        self.assertEqual(rules.how_decided(result, "a", ""), rules.BY_VOTE)

    def test_choosing_against_the_winner_is_an_override(self):
        result = rules.tally({"a": 9, "b": 1})
        self.assertEqual(
            rules.how_decided(result, "b", "I am taking the schedule hit."),
            rules.BY_OVERRIDE,
        )

    def test_an_override_without_a_reason_is_refused(self):
        result = rules.tally({"a": 9, "b": 1})
        with self.assertRaises(DomainError):
            rules.how_decided(result, "b", "")
        with self.assertRaises(DomainError):
            rules.how_decided(result, "b", "   ")


class Options(unittest.TestCase):

    def test_a_decision_with_no_options_becomes_its_own_question(self):
        options = rules.build_options("Do we move?", [], {})
        self.assertEqual([o["text"] for o in options], ["Do we move?"])

    def test_blank_options_are_dropped(self):
        options = rules.build_options("Q", ["A", "  ", "", "B"], {})
        self.assertEqual([o["text"] for o in options], ["A", "B"])

    def test_work_attaches_to_the_option_it_belongs_to(self):
        options = rules.build_options("Q", ["A", "B"], {"1": ["do this", " ", "and this"]})
        self.assertEqual(options[0]["work"], [])
        self.assertEqual(options[1]["work"], ["do this", "and this"])


class Validation(unittest.TestCase):

    def test_a_decision_needs_a_question(self):
        for bad in ("", "   ", None):
            with self.assertRaises(DomainError):
                rules.clean_question(bad)

    def test_a_question_is_trimmed(self):
        self.assertEqual(rules.clean_question("  Where?  "), "Where?")

    def test_an_outcome_is_required_to_record_knowledge(self):
        with self.assertRaises(DomainError):
            rules.clean_outcome("")
