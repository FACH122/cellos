"""
Work that outgrows one person: expansion.

A cell splits when it reaches twenty people, and separately when a piece of
work turns out to be a group's job rather than a person's. These tests pin the
second path: who may take it, what happens to the task, and -- most
importantly -- that the work is not counted twice afterwards.
"""

import unittest

from cellos.domains import permission
from cellos.domains.cell import service as cell_service
from cellos.domains.decision import model as dm, service as decision
from cellos.domains.hierarchy import service as hierarchy
from cellos.domains.member import service as member
from cellos.domains.progress import service as progress
from cellos.domains.task import model as task_model, rules, service as task
from cellos.kernel.errors import DomainError, NotAllowed

_n = [0]


def a_cell(people=3):
    _n[0] += 1
    tag = _n[0]
    boss = member.register("Boss %d" % tag, "sboss%d@test.invalid" % tag)
    c = cell_service.create(boss["id"], "Rebuild the warehouse system %d" % tag)
    crew = [
        member.admit(boss["id"], c["id"], "S%d-%d" % (tag, i), "s%d-%d@test.invalid" % (tag, i))
        for i in range(people - 1)
    ]
    return boss, c, crew


def a_task(boss, c, title="Migrate the stock database", owner=None):
    t = task.create(boss["id"], c["id"], title)
    if owner:
        task.assign(boss["id"], t["id"], owner["id"])
    return task.get(t["id"])


class WhoMaySplit(unittest.TestCase):

    def test_a_leader_may(self):
        boss, c, _crew = a_cell()
        t = a_task(boss, c)
        self.assertTrue(task.may_expand(boss["id"], t["id"]))

    def test_a_member_may_not(self):
        boss, c, crew = a_cell()
        t = a_task(boss, c)
        self.assertFalse(task.may_expand(crew[0]["id"], t["id"]))
        with self.assertRaises(NotAllowed):
            task.expand(crew[0]["id"], t["id"])

    def test_finished_work_cannot_be_split(self):
        boss, c, _crew = a_cell()
        t = a_task(boss, c, owner=boss)
        task.report_progress(boss["id"], t["id"], 100)
        self.assertFalse(task.may_expand(boss["id"], t["id"]))
        with self.assertRaises(DomainError):
            task.expand(boss["id"], t["id"])

    def test_it_cannot_be_split_twice(self):
        boss, c, _crew = a_cell()
        t = a_task(boss, c)
        task.expand(boss["id"], t["id"])
        self.assertFalse(task.may_expand(boss["id"], t["id"]))
        with self.assertRaises(DomainError):
            task.expand(boss["id"], t["id"])


class WhatItProduces(unittest.TestCase):

    def test_the_work_becomes_a_child_cell_with_that_goal(self):
        boss, c, _crew = a_cell()
        t = a_task(boss, c, "Migrate the stock database")
        child = task.expand(boss["id"], t["id"])

        self.assertEqual(child["goal"], "Migrate the stock database")
        self.assertEqual(hierarchy.parent_id(child["id"]), c["id"])
        self.assertIn(child["id"], hierarchy.subtree_ids(c["id"]))

    def test_the_goal_can_be_reworded(self):
        boss, c, _crew = a_cell()
        t = a_task(boss, c, "Migrate the stock database")
        child = task.expand(boss["id"], t["id"], goal="Get every warehouse onto one system")
        self.assertEqual(child["goal"], "Get every warehouse onto one system")

    def test_whoever_held_the_work_leads_the_group(self):
        boss, c, crew = a_cell()
        t = a_task(boss, c, owner=crew[0])
        child = task.expand(boss["id"], t["id"])

        self.assertTrue(permission.is_leader(crew[0]["id"], child["id"]))
        self.assertEqual(
            [m["id"] for m in member.members(child["id"])], [crew[0]["id"]]
        )

    def test_unheld_work_leaves_the_splitter_leading_it(self):
        boss, c, _crew = a_cell()
        t = a_task(boss, c)
        child = task.expand(boss["id"], t["id"])
        self.assertTrue(permission.is_leader(boss["id"], child["id"]))

    def test_the_task_keeps_its_place_in_the_record(self):
        boss, c, _crew = a_cell()
        t = a_task(boss, c)
        child = task.expand(boss["id"], t["id"])

        after = task.get(t["id"])
        self.assertEqual(after["state"], rules.EXPANDED)
        self.assertEqual(after["expanded_into"], child["id"])
        self.assertEqual(task.expanded_into(t["id"]), child["id"])


class ItIsNotCountedTwice(unittest.TestCase):

    def test_splitting_removes_the_task_from_its_cells_progress(self):
        boss, c, _crew = a_cell()
        done = a_task(boss, c, "Something finished", owner=boss)
        task.report_progress(boss["id"], done["id"], 100)
        big = a_task(boss, c, "Something enormous")

        self.assertEqual(progress.of_cell(c["id"]),
                         {"percent": 50, "task_count": 2, "done": 1, "remaining": 1})

        task.expand(boss["id"], big["id"])
        after = progress.of_cell(c["id"])
        # The empty child cell contributes no work, and the promoted task is
        # no longer counted here -- one finished thing remains.
        self.assertEqual(after["task_count"], 1)
        self.assertEqual(after["percent"], 100)

    def test_progress_comes_back_up_from_the_new_cell(self):
        boss, c, _crew = a_cell()
        big = a_task(boss, c, "Something enormous")
        child = task.expand(boss["id"], big["id"])

        inner = task.create(boss["id"], child["id"], "First piece")
        task.assign(boss["id"], inner["id"], boss["id"])
        task.report_progress(boss["id"], inner["id"], 40)

        self.assertEqual(progress.of_cell(child["id"])["percent"], 40)
        self.assertEqual(progress.of_cell(c["id"])["percent"], 40)
        self.assertEqual(progress.of_cell(c["id"])["task_count"], 1)

    def test_nobody_reports_progress_on_work_that_became_a_cell(self):
        boss, c, _crew = a_cell()
        t = a_task(boss, c, owner=boss)
        task.expand(boss["id"], t["id"])
        with self.assertRaises(DomainError):
            task.report_progress(boss["id"], t["id"], 50)

    def test_it_no_longer_counts_as_unowned_or_stalled(self):
        boss, c, _crew = a_cell()
        t = a_task(boss, c)
        self.assertEqual(task_model.unowned_count([c["id"]]), 1)
        task.expand(boss["id"], t["id"])
        self.assertEqual(task_model.unowned_count([c["id"]]), 0)


class TheDecisionThatCausedIt(unittest.TestCase):

    def test_a_decision_is_not_left_waiting_on_work_that_became_a_cell(self):
        boss, c, _crew = a_cell()
        d = decision.propose(boss["id"], c["id"], "How do we do this?", "",
                             ["Properly"], {"0": ["Small piece", "Enormous piece"]})
        decision.act(boss["id"], d["id"], "open")
        decision.act(boss["id"], d["id"], "resolve",
                     option_id=dm.options_of(d["id"])[0]["id"])
        self.assertEqual(decision.get(d["id"])["state"], "executing")

        work = task.in_cells([c["id"]])
        small = [t for t in work if t["title"] == "Small piece"][0]
        huge = [t for t in work if t["title"] == "Enormous piece"][0]

        task.expand(boss["id"], huge["id"])
        task.assign(boss["id"], small["id"], boss["id"])
        task.report_progress(boss["id"], small["id"], 100)

        # The decision is done here: what is left is another cell's goal.
        self.assertEqual(decision.get(d["id"])["state"], "completed")

    def test_the_split_is_in_the_permanent_record(self):
        from cellos.kernel import events

        boss, c, _crew = a_cell()
        t = a_task(boss, c)
        task.expand(boss["id"], t["id"])
        log = events.history(cell_ids=[c["id"]], types=["TaskExpanded"], limit=10)
        self.assertTrue(any(e["subject_id"] == t["id"] for e in log))


class TheHeadcountRuleStillHolds(unittest.TestCase):

    def test_a_small_cell_still_cannot_split_off_a_group_speculatively(self):
        boss, c, _crew = a_cell(people=3)
        with self.assertRaises(DomainError):
            cell_service.create(boss["id"], "A team I might need", c["id"])

    def test_but_it_can_split_off_work_that_is_too_large(self):
        boss, c, _crew = a_cell(people=3)
        t = a_task(boss, c)
        child = task.expand(boss["id"], t["id"])
        self.assertEqual(hierarchy.parent_id(child["id"]), c["id"])


class RecursionHasNoLimit(unittest.TestCase):
    """
    A cell inside a cell inside a cell is not a special case of anything. The
    only structural rule is that nothing may contain itself.
    """

    def test_nesting_forty_deep_behaves_like_nesting_once(self):
        boss, top, _crew = a_cell()
        current = top
        for i in range(40):
            t = a_task(boss, current, "Level %d" % i)
            current = task.expand(boss["id"], t["id"])

        self.assertEqual(hierarchy.depth(current["id"]), 40)
        self.assertEqual(len(hierarchy.subtree_ids(top["id"])), 41)
        self.assertEqual(len(hierarchy.path(current["id"])), 41)

        # The deepest cell answers exactly like the root: same shape, no
        # special case, and progress still rolls the whole way up.
        deep = task.create(boss["id"], current["id"], "The actual work")
        task.assign(boss["id"], deep["id"], boss["id"])
        task.report_progress(boss["id"], deep["id"], 50)
        self.assertEqual(progress.of_cell(current["id"])["percent"], 50)
        self.assertEqual(progress.of_cell(top["id"])["percent"], 50)

    def test_a_cell_cannot_contain_itself(self):
        from cellos.domains.hierarchy import service as h
        boss, top, _crew = a_cell()
        t = a_task(boss, top)
        child = task.expand(boss["id"], t["id"])
        with self.assertRaises(DomainError):
            h.place_under(boss["id"], child["id"], top["id"])


class NothingIsCopied(unittest.TestCase):
    """
    Section 2 of the brief: the task becomes the mission of the new cell, and
    everything already attached to it stays attached.
    """

    def test_the_cell_knows_the_work_it_grew_out_of(self):
        from cellos.domains.responsibility import service as responsibility

        boss, c, crew = a_cell()
        t = a_task(boss, c, "Build authentication", owner=crew[0])
        child = task.expand(boss["id"], t["id"])

        mission = responsibility.mission(child["id"])
        self.assertEqual(mission["task_id"], t["id"])
        self.assertEqual(mission["title"], "Build authentication")
        self.assertEqual(mission["from_cell"]["id"], c["id"])

    def test_evidence_offered_on_the_work_is_the_cells_evidence(self):
        from cellos.domains.evidence import service as evidence
        from cellos.domains.responsibility import service as responsibility

        boss, c, _crew = a_cell()
        t = a_task(boss, c)
        evidence.attach(boss["id"], "task", t["id"], "report", "Why this is a month of work")
        child = task.expand(boss["id"], t["id"])

        mission = responsibility.mission(child["id"])
        self.assertEqual([e["label"] for e in mission["evidence"]],
                         ["Why this is a month of work"])

    def test_a_cell_started_from_nothing_has_no_mission(self):
        from cellos.domains.responsibility import service as responsibility
        _boss, c, _crew = a_cell()
        self.assertIsNone(responsibility.mission(c["id"]))

    def test_the_task_row_itself_is_never_rewritten(self):
        boss, c, crew = a_cell()
        t = a_task(boss, c, "Build authentication", owner=crew[0])
        before = task.get(t["id"])
        task.expand(boss["id"], t["id"])
        after = task.get(t["id"])

        for field in ("id", "title", "cell_id", "owner_id", "created_at"):
            self.assertEqual(before[field], after[field], field)
