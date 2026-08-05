"""
Responsibility, not access control lists.

The sixth principle -- nobody sees a cell above their own level -- is the one
rule a refactor is most likely to break quietly, so it is asserted against
real cells rather than mocked.
"""

import unittest

from cellos.domains import permission
from cellos.domains.cell import service as cell_service
from cellos.domains.member import service as member
from cellos.kernel.errors import NotAllowed

_n = [0]


def an_org():
    """A cell big enough to hold a child, with a leader, a member and an outsider."""
    _n[0] += 1
    tag = _n[0]
    boss = member.register("Boss %d" % tag, "boss%d@test.invalid" % tag)
    parent = cell_service.create(boss["id"], "Run the thing %d" % tag)
    for i in range(21):
        member.admit(boss["id"], parent["id"], "Staff %d-%d" % (tag, i),
                     "staff%d-%d@test.invalid" % (tag, i))
    child = cell_service.create(boss["id"], "A team %d" % tag, parent["id"])
    worker = member.admit(boss["id"], child["id"], "Worker %d" % tag,
                          "worker%d@test.invalid" % tag)
    outsider = member.register("Outsider %d" % tag, "outsider%d@test.invalid" % tag)
    return boss, parent, child, worker, outsider


class Sight(unittest.TestCase):

    def test_a_leader_sees_their_cell_and_everything_beneath_it(self):
        boss, parent, child, _worker, _outsider = an_org()
        visible = permission.visible_cell_ids(boss["id"])
        self.assertIn(parent["id"], visible)
        self.assertIn(child["id"], visible)

    def test_a_member_of_a_child_never_sees_the_parent(self):
        _boss, parent, child, worker, _outsider = an_org()
        visible = permission.visible_cell_ids(worker["id"])
        self.assertIn(child["id"], visible)
        self.assertNotIn(parent["id"], visible)
        with self.assertRaises(NotAllowed):
            permission.require_sight(worker["id"], parent["id"])

    def test_an_outsider_sees_nothing(self):
        _boss, parent, child, _worker, outsider = an_org()
        self.assertEqual(permission.visible_cell_ids(outsider["id"]), set())
        for cell_id in (parent["id"], child["id"]):
            with self.assertRaises(NotAllowed):
                permission.require_sight(outsider["id"], cell_id)

    def test_home_starts_at_the_highest_cell_you_belong_to(self):
        boss, parent, child, worker, _outsider = an_org()
        # The boss belongs to both, so the child is not a separate home.
        self.assertEqual(permission.home_cell_ids(boss["id"]), [parent["id"]])
        self.assertEqual(permission.home_cell_ids(worker["id"]), [child["id"]])


class Acting(unittest.TestCase):

    def test_responsibility_flows_downward(self):
        boss, _parent, child, _worker, _outsider = an_org()
        self.assertTrue(permission.is_member(boss["id"], child["id"]))
        self.assertTrue(permission.is_leader(boss["id"], child["id"]))

    def test_it_does_not_flow_upward(self):
        _boss, parent, _child, worker, _outsider = an_org()
        self.assertFalse(permission.is_member(worker["id"], parent["id"]))
        self.assertFalse(permission.is_leader(worker["id"], parent["id"]))

    def test_a_member_is_not_a_leader(self):
        _boss, _parent, child, worker, _outsider = an_org()
        self.assertTrue(permission.is_member(worker["id"], child["id"]))
        self.assertFalse(permission.is_leader(worker["id"], child["id"]))
        with self.assertRaises(NotAllowed):
            permission.require_leader(worker["id"], child["id"], "do that")

    def test_a_requirement_can_be_asked_as_a_question(self):
        _boss, _parent, child, worker, outsider = an_org()
        self.assertTrue(permission.allows(permission.require_member, worker["id"], child["id"]))
        self.assertFalse(
            permission.allows(permission.require_leader, worker["id"], child["id"])
        )
        self.assertFalse(permission.allows(permission.require_sight, outsider["id"], child["id"]))

    def test_standing_reports_everything_the_interface_needs(self):
        _boss, _parent, child, worker, _outsider = an_org()
        standing = permission.standing(worker["id"], child["id"])
        self.assertEqual(standing["role"], "member")
        self.assertTrue(standing["is_member"])
        self.assertTrue(standing["acts_here"])
        self.assertFalse(standing["is_leader"])


class LargeCellsBecomeFormal(unittest.TestCase):

    def test_admitting_becomes_a_leaders_act_once_the_cell_grows(self):
        _boss, parent, _child, worker, _outsider = an_org()
        # The parent is well past five people, and the worker is not its leader.
        self.assertFalse(member.may_admit(worker["id"], parent["id"]))

    def test_a_small_cell_lets_any_member_bring_someone_in(self):
        _n[0] += 1
        founder = member.register("Founder %d" % _n[0], "founder%d@test.invalid" % _n[0])
        cell = cell_service.create(founder["id"], "Just us")
        friend = member.admit(founder["id"], cell["id"], "Friend %d" % _n[0],
                              "friend%d@test.invalid" % _n[0])
        self.assertTrue(member.may_admit(friend["id"], cell["id"]))
