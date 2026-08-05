"""
Progress is derived and rolls upward weighted by how much work each cell
holds. A task's state is derived too -- these tests pin both derivations so
neither can quietly become a stored column again.
"""

import unittest

from cellos.domains.hierarchy import rules as hierarchy
from cellos.domains.task import rules as task
from cellos.kernel.errors import DomainError


class Rollup(unittest.TestCase):

    def test_a_cell_with_no_work_is_at_zero_not_complete(self):
        self.assertEqual(hierarchy.rollup((0, 0, 0), [])["percent"], 0)

    def test_one_cell_averages_its_own_tasks(self):
        result = hierarchy.rollup((4, 200, 1), [])
        self.assertEqual(result["percent"], 50)
        self.assertEqual(result["task_count"], 4)
        self.assertEqual(result["done"], 1)
        self.assertEqual(result["remaining"], 3)

    def test_children_are_weighted_by_how_much_work_they_hold(self):
        # A child with 2 tasks at 100% must not outweigh one with 200 at 0%.
        result = hierarchy.rollup((0, 0, 0), [(2, 200, 2), (200, 0, 0)])
        self.assertEqual(result["percent"], 1)
        self.assertEqual(result["task_count"], 202)

    def test_an_equal_split_averages_evenly(self):
        result = hierarchy.rollup((0, 0, 0), [(10, 1000, 10), (10, 0, 0)])
        self.assertEqual(result["percent"], 50)

    def test_a_cell_combines_its_own_work_with_the_work_beneath_it(self):
        result = hierarchy.rollup((1, 100, 1), [(1, 0, 0)])
        self.assertEqual(result["percent"], 50)
        self.assertEqual(result["done"], 1)


class TaskState(unittest.TestCase):

    def test_work_nobody_holds_is_open(self):
        self.assertEqual(task.state_of(None, 0), task.OPEN)
        self.assertEqual(task.state_of(None, 40), task.OPEN)

    def test_work_someone_holds_is_active(self):
        self.assertEqual(task.state_of("user_1", 0), task.ACTIVE)
        self.assertEqual(task.state_of("user_1", 99), task.ACTIVE)

    def test_finished_work_is_done_whoever_holds_it(self):
        self.assertEqual(task.state_of("user_1", 100), task.DONE)
        self.assertEqual(task.state_of(None, 100), task.DONE)


class ProgressReports(unittest.TestCase):

    def test_progress_must_be_a_percentage(self):
        self.assertEqual(task.clean_progress("40"), 40)
        for bad in (-1, 101, "half", None):
            with self.assertRaises(DomainError):
                task.clean_progress(bad)

    def test_finishing_and_unfinishing_are_named_in_the_record(self):
        self.assertEqual(task.event_for(100, False), "TaskCompleted")
        self.assertEqual(task.event_for(30, True), "TaskReopened")
        self.assertEqual(task.event_for(30, False), "ProgressUpdated")
