"""
Governance is the load-bearing idea: capabilities are a function of headcount
and nothing else. These tests are the specification of that function.
"""

import unittest

from cellos.domains.governance import rules as governance


class Emergence(unittest.TestCase):

    def test_a_person_alone_gets_tasks_and_nothing_else(self):
        caps = governance.capabilities(1)
        self.assertEqual(caps, set(governance.ALWAYS))
        self.assertNotIn(governance.VOTING, caps)
        self.assertNotIn(governance.CHILDREN, caps)
        self.assertNotIn(governance.DASHBOARD, caps)

    def test_voting_appears_at_five_and_not_at_four(self):
        self.assertFalse(governance.has(4, governance.VOTING))
        self.assertTrue(governance.has(5, governance.VOTING))

    def test_children_appear_at_twenty(self):
        self.assertFalse(governance.has(19, governance.CHILDREN))
        self.assertTrue(governance.has(20, governance.CHILDREN))

    def test_dashboard_at_fifty_analytics_at_two_hundred(self):
        self.assertFalse(governance.has(49, governance.DASHBOARD))
        self.assertTrue(governance.has(50, governance.DASHBOARD))
        self.assertFalse(governance.has(199, governance.ANALYTICS))
        self.assertTrue(governance.has(200, governance.ANALYTICS))

    def test_capabilities_only_ever_accumulate(self):
        previous = set()
        for scale in range(0, 260):
            caps = governance.capabilities(scale)
            self.assertTrue(previous <= caps, "capability lost at scale %d" % scale)
            previous = caps

    def test_a_cell_that_shrinks_gives_capabilities_back(self):
        self.assertIn(governance.DASHBOARD, governance.capabilities(60))
        self.assertNotIn(governance.DASHBOARD, governance.capabilities(12))


class Governing(unittest.TestCase):

    def test_small_cells_are_informal(self):
        self.assertEqual(governance.model(1), governance.INFORMAL)
        self.assertEqual(governance.model(4), governance.INFORMAL)
        self.assertFalse(governance.votes(4))

    def test_the_count_settles_it_in_the_middle(self):
        self.assertEqual(governance.model(5), governance.VOTE_DECIDES)
        self.assertEqual(governance.model(19), governance.VOTE_DECIDES)
        self.assertTrue(governance.votes(5))

    def test_large_cells_hand_the_count_to_a_leader(self):
        self.assertEqual(governance.model(20), governance.LEADER_CONFIRMS_VOTE)
        self.assertEqual(governance.model(5000), governance.LEADER_CONFIRMS_VOTE)
        self.assertTrue(governance.votes(20))

    def test_next_threshold_names_what_growing_would_add(self):
        self.assertEqual(governance.next_threshold(1), (governance.VOTING, 5))
        self.assertEqual(governance.next_threshold(300), (None, None))
