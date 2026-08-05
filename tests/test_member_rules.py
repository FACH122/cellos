"""Who may join, who may lead, and when formality arrives."""

import unittest

from cellos.domains.cell import rules as cell_rules
from cellos.domains.evidence import rules as evidence_rules
from cellos.domains.member import rules as member
from cellos.kernel.errors import DomainError


class Identity(unittest.TestCase):

    def test_a_name_is_required(self):
        for bad in ("", "  ", None):
            with self.assertRaises(DomainError):
                member.clean_name(bad)

    def test_email_is_normalised(self):
        self.assertEqual(member.clean_email("  Sara@Example.ORG "), "sara@example.org")

    def test_a_plausible_email_is_required(self):
        for bad in ("", "sara", "@example.org", "sara@", None):
            with self.assertRaises(DomainError):
                member.clean_email(bad)


class Roles(unittest.TestCase):

    def test_there_are_exactly_two_roles(self):
        self.assertEqual(set(member.ROLES), {"member", "leader"})
        with self.assertRaises(DomainError):
            member.check_role("admin")

    def test_a_cell_cannot_lose_its_last_leader(self):
        with self.assertRaises(DomainError):
            member.check_last_leader(member.MEMBER, leader_count=1)
        member.check_last_leader(member.MEMBER, leader_count=2)
        member.check_last_leader(member.LEADER, leader_count=1)


class Formality(unittest.TestCase):

    def test_small_cells_let_anyone_bring_someone_in(self):
        self.assertFalse(member.admitting_needs_leader(1))
        self.assertFalse(member.admitting_needs_leader(4))

    def test_larger_cells_make_it_a_leaders_act(self):
        self.assertTrue(member.admitting_needs_leader(5))
        self.assertTrue(member.admitting_needs_leader(500))


class Cells(unittest.TestCase):

    def test_a_cell_needs_a_goal(self):
        for bad in ("", "   ", None):
            with self.assertRaises(DomainError):
                cell_rules.clean_goal(bad)

    def test_a_goal_is_one_sentence(self):
        with self.assertRaises(DomainError):
            cell_rules.clean_goal("x" * (cell_rules.MAX_GOAL + 1))

    def test_child_cells_are_refused_below_the_threshold(self):
        with self.assertRaises(DomainError):
            cell_rules.check_can_hold_children(parent_scale=19, threshold=20)
        cell_rules.check_can_hold_children(parent_scale=20, threshold=20)


class Evidence(unittest.TestCase):

    def test_evidence_needs_a_description(self):
        with self.assertRaises(DomainError):
            evidence_rules.clean_label("  ")

    def test_only_known_kinds_are_accepted(self):
        evidence_rules.check_kind("measurement")
        with self.assertRaises(DomainError):
            evidence_rules.check_kind("vibes")

    def test_evidence_attaches_only_to_real_subjects(self):
        for good in evidence_rules.SUBJECTS:
            evidence_rules.check_subject(good)
        with self.assertRaises(DomainError):
            evidence_rules.check_subject("invoice")
