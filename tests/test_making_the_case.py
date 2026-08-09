"""
Arguing about an answer, not about the question.

Everything said about a decision used to be filed against the decision, which
meant a quote for one venue and an objection about another sat in the same
list and a reader had to work out which answer each one bore on. An argument
belongs to the thing it is an argument for.
"""

import unittest

from cellos.domains.cell import service as cell_service
from cellos.domains.decision import model as dm, service as decision
from cellos.domains.evidence import rules as evidence_rules, service as evidence
from cellos.domains.member import service as member
from cellos.kernel.errors import DomainError

_n = [0]


def a_question(people=3):
    _n[0] += 1
    tag = _n[0]
    boss = member.register("Chair %d" % tag, "case%d@test.invalid" % tag)
    c = cell_service.create(boss["id"], "Decide something %d" % tag)
    for i in range(people - 1):
        member.admit(boss["id"], c["id"], "C%d-%d" % (tag, i), "c%d-%d@test.invalid" % (tag, i))
    d = decision.propose(boss["id"], c["id"], "Where do we hold it?", "",
                         ["The garden", "The hall"])
    return boss, c, d, dm.options_of(d["id"])


class SaidAboutAnAnswer(unittest.TestCase):

    def test_a_remark_can_name_the_answer_it_is_about(self):
        boss, c, d, opts = a_question()
        decision.remark(boss["id"], d["id"], "Ten minutes from campus.", opts[0]["id"])
        decision.remark(boss["id"], d["id"], "We tried this in 2024.", opts[1]["id"])

        self.assertEqual([r["body"] for r in dm.remarks_of(d["id"], opts[0]["id"])],
                         ["Ten minutes from campus."])
        self.assertEqual([r["body"] for r in dm.remarks_of(d["id"], opts[1]["id"])],
                         ["We tried this in 2024."])

    def test_a_remark_about_the_question_stays_about_the_question(self):
        """
        Not everything is about one answer. Asking for what was said about the
        decision itself must not sweep up the arguments for each option.
        """
        boss, c, d, opts = a_question()
        decision.remark(boss["id"], d["id"], "We need to settle this by Friday.")
        decision.remark(boss["id"], d["id"], "Ten minutes from campus.", opts[0]["id"])

        general = dm.remarks_of(d["id"])
        self.assertEqual([r["body"] for r in general], ["We need to settle this by Friday."])

    def test_an_answer_from_another_question_is_refused(self):
        boss, c, d, opts = a_question()
        _, _, other, other_opts = a_question()
        with self.assertRaises(DomainError):
            decision.remark(boss["id"], d["id"], "Nonsense.", other_opts[0]["id"])


class OfferedForAnAnswer(unittest.TestCase):

    def test_an_option_is_something_evidence_can_back(self):
        self.assertIn("option", evidence_rules.SUBJECTS)

    def test_evidence_attaches_to_one_answer(self):
        boss, c, d, opts = a_question()
        evidence.attach(boss["id"], "option", opts[0]["id"], "measurement",
                        "Commute survey", "https://example.invalid/survey")

        backing = evidence.supporting("option", opts[0]["id"])
        self.assertEqual([e["label"] for e in backing], ["Commute survey"])
        self.assertEqual(evidence.supporting("option", opts[1]["id"]), [])

    def test_it_finds_the_cell_the_answer_lives_in(self):
        """
        Evidence is filed against a cell. An option does not carry one, so the
        locator has to walk to its decision -- and if it could not, attaching
        would fail rather than file it somewhere wrong.
        """
        boss, c, d, opts = a_question()
        attached = evidence.attach(boss["id"], "option", opts[0]["id"], "note", "A point")
        self.assertEqual(attached["cell_id"], c["id"])
