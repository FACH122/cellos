"""
The typed relationship layer.

A generic edge table is only safe if every write is checked against a declared
kind. These tests are that guarantee.
"""

import unittest

from cellos.kernel import relationships
from cellos.kernel.errors import DomainError

# A kind that exists only for these tests.
TEST_KIND = relationships.register(
    "test_owns", "cell", ("decision", "task"), single_head=True,
    description="Test fixture.",
)

_n = [0]


def an_id(prefix):
    _n[0] += 1
    return "%s_test%d" % (prefix, _n[0])


class Declaration(unittest.TestCase):

    def test_the_real_kinds_are_registered(self):
        kinds = relationships.kinds()
        self.assertIn("contains", kinds)
        self.assertIn("produces", kinds)
        self.assertIn("supports", kinds)

    def test_containment_allows_one_parent_only(self):
        self.assertTrue(relationships.kinds()["contains"].single_head)

    def test_every_kind_documents_itself(self):
        for name, spec in relationships.kinds().items():
            if name == TEST_KIND:
                continue
            self.assertTrue(spec.description, "%s has no description" % name)


class Validation(unittest.TestCase):

    def test_an_unknown_kind_is_refused(self):
        with self.assertRaises(DomainError):
            relationships.form("invented", "cell", an_id("cell"), "task", an_id("task"))

    def test_the_wrong_type_at_the_tail_is_refused(self):
        with self.assertRaises(DomainError):
            relationships.form(TEST_KIND, "task", an_id("task"), "decision", an_id("dec"))

    def test_the_wrong_type_at_the_head_is_refused(self):
        with self.assertRaises(DomainError):
            relationships.form(TEST_KIND, "cell", an_id("cell"), "cell", an_id("cell"))

    def test_nothing_may_relate_to_itself(self):
        same = an_id("cell")
        with self.assertRaises(DomainError):
            relationships.form(TEST_KIND, "cell", same, "decision", same)

    def test_a_single_head_cannot_be_claimed_twice(self):
        child = an_id("dec")
        relationships.form(TEST_KIND, "cell", an_id("cell"), "decision", child)
        with self.assertRaises(DomainError):
            relationships.form(TEST_KIND, "cell", an_id("cell"), "decision", child)


class Walking(unittest.TestCase):

    def test_edges_can_be_followed_in_both_directions(self):
        parent = an_id("cell")
        first, second = an_id("dec"), an_id("dec")
        relationships.form(TEST_KIND, "cell", parent, "decision", first)
        relationships.form(TEST_KIND, "cell", parent, "decision", second)

        self.assertEqual(set(relationships.heads(TEST_KIND, parent)), {first, second})
        self.assertEqual(relationships.tails(TEST_KIND, first), [parent])
        self.assertEqual(relationships.head_of(TEST_KIND, first), parent)
        self.assertEqual(relationships.count(TEST_KIND, parent), 2)

    def test_an_absent_edge_reads_as_absent(self):
        self.assertEqual(relationships.heads(TEST_KIND, an_id("cell")), [])
        self.assertIsNone(relationships.head_of(TEST_KIND, an_id("dec")))
        self.assertFalse(relationships.exists(TEST_KIND, an_id("cell"), an_id("dec")))


class RebuiltFromTheLog(unittest.TestCase):

    def test_forming_an_edge_records_an_event(self):
        from cellos.kernel import events

        tail, head = an_id("cell"), an_id("task")
        relationships.form(TEST_KIND, "cell", tail, "task", head)
        recorded = events.history(types=["RelationshipFormed"], limit=50)
        self.assertTrue(
            any(e["payload"]["from_id"] == tail and e["payload"]["to_id"] == head
                for e in recorded),
            "the relationship graph must be reconstructible from the log",
        )
