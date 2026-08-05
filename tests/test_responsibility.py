"""
Responsibility.

Permission asks what a person may do. Responsibility asks what they are
expected to accomplish. Nothing here is assigned -- every answer is read off
facts other domains already recorded, so these tests are really asserting that
the system already knew.
"""

import unittest

from cellos.domains import permission
from cellos.domains.cell import service as cell_service
from cellos.domains.decision import model as dm, service as decision
from cellos.domains.member import service as member
from cellos.domains.responsibility import rules, service as responsibility
from cellos.domains.task import service as task

_n = [0]


def an_org(people=6):
    _n[0] += 1
    tag = _n[0]
    boss = member.register("Chief %d" % tag, "chief%d@test.invalid" % tag)
    top = cell_service.create(boss["id"], "Run it %d" % tag)
    crew = [
        member.admit(boss["id"], top["id"], "R%d-%d" % (tag, i), "r%d-%d@test.invalid" % (tag, i))
        for i in range(people - 1)
    ]
    return boss, top, crew


def holders(shape, role):
    return [h["id"] for h in shape["roles"][role]]


class Roles(unittest.TestCase):

    def test_a_cell_is_answered_for_by_whoever_leads_it(self):
        boss, top, crew = an_org()
        shape = responsibility.for_cell(top["id"])
        self.assertEqual(holders(shape, rules.LEADER), [boss["id"]])
        self.assertEqual(holders(shape, rules.RESPONSIBLE), [boss["id"]])
        self.assertEqual(len(holders(shape, rules.PARTICIPANT)), 6)

    def test_whoever_holds_the_work_is_responsible_for_it(self):
        boss, top, crew = an_org()
        t = task.create(boss["id"], top["id"], "Do the thing")
        task.assign(boss["id"], t["id"], crew[0]["id"])

        shape = responsibility.for_task(task.get(t["id"]))
        self.assertEqual(holders(shape, rules.RESPONSIBLE), [crew[0]["id"]])
        self.assertEqual(holders(shape, rules.LEADER), [boss["id"]])

    def test_unheld_work_has_no_responsible_person_and_that_is_the_signal(self):
        boss, top, _crew = an_org()
        t = task.create(boss["id"], top["id"], "Nobody's job yet")
        shape = responsibility.for_task(task.get(t["id"]))
        self.assertEqual(holders(shape, rules.RESPONSIBLE), [])

    def test_nobody_verifies_their_own_work(self):
        boss, top, crew = an_org()
        t = task.create(boss["id"], top["id"], "Do the thing")
        task.assign(boss["id"], t["id"], boss["id"])   # the leader does it himself
        shape = responsibility.for_task(task.get(t["id"]))
        self.assertNotIn(boss["id"], holders(shape, rules.VERIFIER))

    def test_verification_comes_from_the_cell_above(self):
        boss, top, crew = an_org(people=25)
        t = task.create(boss["id"], top["id"], "Big piece")
        task.assign(boss["id"], t["id"], crew[0]["id"])
        child = task.expand(boss["id"], t["id"])

        # crew[0] was holding it, so they lead the new cell -- and the person
        # who checks it is the leader above, not themselves.
        inner = task.create(crew[0]["id"], child["id"], "Inner work")
        task.assign(crew[0]["id"], inner["id"], crew[0]["id"])
        shape = responsibility.for_task(task.get(inner["id"]))
        self.assertEqual(holders(shape, rules.RESPONSIBLE), [crew[0]["id"]])
        self.assertEqual(holders(shape, rules.VERIFIER), [boss["id"]])

    def test_responsibility_for_a_question_moves_to_whoever_settled_it(self):
        boss, top, crew = an_org()
        d = decision.propose(crew[0]["id"], top["id"], "Which way?", "", ["A", "B"])
        before = responsibility.for_decision(decision.get(d["id"]))
        self.assertEqual(holders(before, rules.RESPONSIBLE), [crew[0]["id"]])

        decision.act(crew[0]["id"], d["id"], "open")
        decision.act(boss["id"], d["id"], "resolve",
                     option_id=dm.options_of(d["id"])[0]["id"])
        after = responsibility.for_decision(decision.get(d["id"]))
        self.assertEqual(holders(after, rules.RESPONSIBLE), [boss["id"]])

    def test_everyone_who_voted_or_spoke_took_part(self):
        boss, top, crew = an_org()
        d = decision.propose(boss["id"], top["id"], "Which way?", "", ["A", "B"])
        decision.act(boss["id"], d["id"], "open")
        decision.remark(crew[1]["id"], d["id"], "I think A.")
        decision.act(boss["id"], d["id"], "put_to_cell")
        decision.vote(crew[2]["id"], d["id"], dm.options_of(d["id"])[0]["id"])

        shape = responsibility.for_decision(decision.get(d["id"]))
        took_part = holders(shape, rules.PARTICIPANT)
        self.assertIn(crew[1]["id"], took_part)
        self.assertIn(crew[2]["id"], took_part)
        self.assertNotIn(crew[3]["id"], took_part)


class Graph(unittest.TestCase):

    def test_it_reports_what_you_hold(self):
        boss, top, crew = an_org()
        mine = task.create(boss["id"], top["id"], "Mine")
        task.assign(crew[0]["id"], mine["id"], crew[0]["id"])
        task.create(boss["id"], top["id"], "Not mine")

        g = responsibility.graph(crew[0]["id"], top["id"])
        self.assertEqual([t["title"] for t in g["yours"]], ["Mine"])

    def test_it_reports_what_is_waiting_on_you(self):
        boss, top, crew = an_org()
        d = decision.propose(boss["id"], top["id"], "Which way?", "", ["A", "B"])
        decision.act(boss["id"], d["id"], "open")
        decision.act(boss["id"], d["id"], "put_to_cell")

        g = responsibility.graph(crew[0]["id"], top["id"])
        self.assertEqual([q["question"] for q in g["waiting_on_you"]["votes"]], ["Which way?"])

        decision.vote(crew[0]["id"], d["id"], dm.options_of(d["id"])[0]["id"])
        g = responsibility.graph(crew[0]["id"], top["id"])
        self.assertEqual(g["waiting_on_you"]["votes"], [])

    def test_it_reports_what_nobody_has_taken(self):
        boss, top, _crew = an_org()
        task.create(boss["id"], top["id"], "Orphan")
        g = responsibility.graph(boss["id"], top["id"])
        self.assertEqual([t["title"] for t in g["blocked"]], ["Orphan"])

    def test_a_leader_sees_what_they_are_waiting_on_others_for(self):
        boss, top, crew = an_org()
        t = task.create(boss["id"], top["id"], "Someone else's")
        task.assign(boss["id"], t["id"], crew[0]["id"])

        g = responsibility.graph(boss["id"], top["id"])
        self.assertEqual([t["title"] for t in g["you_are_waiting_on"]["work"]],
                         ["Someone else's"])

    def test_it_never_reaches_above_the_person(self):
        boss, top, crew = an_org(people=25)
        t = task.create(boss["id"], top["id"], "Big piece")
        task.assign(boss["id"], t["id"], crew[0]["id"])
        child = task.expand(boss["id"], t["id"])

        # crew[0] leads the child and belongs to the parent too, so ask from
        # somebody who only belongs below.
        inner = member.admit(crew[0]["id"], child["id"], "Deep", "deep%d@test.invalid" % _n[0])
        self.assertIsNone(responsibility.graph(inner["id"], top["id"]))
        self.assertIsNotNone(responsibility.graph(inner["id"], child["id"]))

    def test_descendants_are_visible_and_ancestors_are_not(self):
        boss, top, crew = an_org(people=25)
        t = task.create(boss["id"], top["id"], "Big piece")
        task.assign(boss["id"], t["id"], crew[0]["id"])
        child = task.expand(boss["id"], t["id"])

        rows = responsibility.descendants(boss["id"], top["id"])
        self.assertEqual([r["id"] for r in rows], [child["id"]])
        self.assertEqual(responsibility.descendants(crew[0]["id"], child["id"]), [])
        self.assertNotIn(top["id"], permission.visible_cell_ids(
            member.admit(crew[0]["id"], child["id"], "Only here",
                         "onlyhere%d@test.invalid" % _n[0])["id"]))
