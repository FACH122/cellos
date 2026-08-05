"""
The system states its own rules, or it does not.

CellOS promises the reader never has to work out what they may do: the server
says so, and anything not offered is not available. Ten people using it at
once found two places where that promise was not kept.

The first: casting a vote is not a state change -- the question stays in
voting -- so it was never a transition, so it never appeared in what the
server offered. Three separate people reported having to learn the commonest
action in the system from somewhere other than the system.

The second: ratifying the cell's own vote recorded no reason at all, so the
cheapest way to close a question was also the only way to close one silently.
A leader deciding alone has to say why. The cell deciding together should
leave the same trace.
"""

import unittest

from cellos.domains.cell import service as cell_service
from cellos.domains.decision import model as decision_model, rules, service as decision
from cellos.domains.member import service as member

_n = [0]


def a_cell(people=5):
    _n[0] += 1
    tag = _n[0]
    leader = member.register("Chair %d" % tag, "chair%d@test.invalid" % tag)
    cell = cell_service.create(leader["id"], "Pick a chemistry %d" % tag)
    crew = [
        member.admit(leader["id"], cell["id"], "V%d-%d" % (tag, i),
                     "v%d-%d@test.invalid" % (tag, i))
        for i in range(people - 1)
    ]
    return leader, cell, crew


def a_vote_in_progress(people=5):
    leader, cell, crew = a_cell(people)
    d = decision.propose(leader["id"], cell["id"], "Which chemistry?", "",
                         ["LFP", "Sodium-ion"], {"0": ["qualify LFP cells"]})
    decision.act(leader["id"], d["id"], "open")
    decision.act(leader["id"], d["id"], "put_to_cell")
    return leader, cell, crew, decision.get(d["id"])


class OfferingTheVote(unittest.TestCase):

    def test_the_rule_itself(self):
        self.assertTrue(rules.may_vote("voting", True))
        self.assertFalse(rules.may_vote("voting", False))
        self.assertFalse(rules.may_vote("open", True))
        self.assertFalse(rules.may_vote("accepted", True))

    def test_a_member_is_told_they_can_vote(self):
        leader, cell, crew, d = a_vote_in_progress()
        self.assertTrue(decision.record(crew[0]["id"], d["id"])["can_vote"])

    def test_having_voted_does_not_withdraw_the_offer(self):
        """A vote can be changed while the question is open, so it stays on offer."""
        leader, cell, crew, d = a_vote_in_progress()
        options = decision_model.options_of(d["id"])
        decision.vote(crew[0]["id"], d["id"], options[0]["id"])
        record = decision.record(crew[0]["id"], d["id"])
        self.assertTrue(record["can_vote"])
        self.assertIsNotNone(record["your_vote"])

    def test_a_question_not_in_voting_does_not_offer_it(self):
        leader, cell, crew = a_cell()
        d = decision.propose(leader["id"], cell["id"], "Which?", "", ["A", "B"], {})
        self.assertFalse(decision.record(leader["id"], d["id"])["can_vote"])


class RatifyingLeavesATrace(unittest.TestCase):

    def test_the_reason_reads_as_the_count(self):
        said = rules.vote_reason({"counts": {"opt": 8}, "total": 9, "winner": "opt"})
        self.assertEqual(said, "The cell chose this, 8 of 9 votes.")

    def test_closing_a_vote_records_why(self):
        leader, cell, crew, d = a_vote_in_progress(people=5)
        options = decision_model.options_of(d["id"])
        for person in crew:
            decision.vote(person["id"], d["id"], options[0]["id"])

        decision.act(leader["id"], d["id"], "accept_by_vote")

        settled = decision.get(d["id"])
        self.assertEqual(settled["chosen_option"], options[0]["id"])
        self.assertEqual(settled["decided_how"], rules.BY_VOTE)
        self.assertTrue(settled["resolution_note"],
                        "ratifying a vote must not settle a question silently")
        self.assertIn("4 of 4", settled["resolution_note"])
