"""
The workflow engine.

These run against a temporary database because the engine's central promise --
that reading the state, checking the transition and appending the event happen
as one indivisible step -- is only meaningful against real storage.
"""

import threading
import unittest

from cellos.domains.cell import service as cell_service
from cellos.domains.decision import model as decision_model, service as decision
from cellos.domains.decision.workflow import flow
from cellos.domains.member import service as member
from cellos.kernel.errors import Conflict, DomainError, NotAllowed

_n = [0]


def a_cell(goal="Decide something", people=1):
    """A fresh cell with a fresh leader, at whatever scale is wanted."""
    _n[0] += 1
    tag = _n[0]
    leader = member.register("Leader %d" % tag, "leader%d@test.invalid" % tag)
    cell = cell_service.create(leader["id"], goal)
    crew = [
        member.admit(leader["id"], cell["id"], "P%d-%d" % (tag, i),
                     "p%d-%d@test.invalid" % (tag, i))
        for i in range(people - 1)
    ]
    return leader, cell, crew


def a_decision(leader, cell, options=("A", "B")):
    return decision.propose(leader["id"], cell["id"], "Which one?", "", list(options),
                            {"0": ["do A"], "1": ["do B"]})


class Declaration(unittest.TestCase):

    def test_every_transition_names_real_states(self):
        for t in flow.transitions.values():
            for state in t.sources + (t.target,):
                self.assertIn(state, flow.states, "%s -> %s" % (t.name, state))

    def test_the_lifecycle_runs_in_the_declared_order(self):
        self.assertEqual(flow.position("draft"), 0)
        self.assertLess(flow.position("open"), flow.position("voting"))
        self.assertLess(flow.position("accepted"), flow.position("executing"))
        self.assertLess(flow.position("completed"), flow.position("knowledge"))


class WhatIsOffered(unittest.TestCase):

    def test_a_new_decision_offers_opening_and_nothing_else_structural(self):
        leader, cell, _ = a_cell()
        d = a_decision(leader, cell)
        offered = {a["name"] for a in decision.actions(leader["id"], d)}
        self.assertIn("open", offered)
        self.assertNotIn("accept_by_vote", offered)
        self.assertNotIn("record", offered)

    def test_a_cell_of_one_is_never_offered_a_vote(self):
        leader, cell, _ = a_cell(people=1)
        d = a_decision(leader, cell)
        decision.act(leader["id"], d["id"], "open")
        offered = {a["name"] for a in decision.actions(leader["id"], decision.get(d["id"]))}
        self.assertNotIn("put_to_cell", offered)
        self.assertIn("resolve", offered)

    def test_a_cell_of_five_is_offered_a_vote(self):
        leader, cell, _ = a_cell(people=5)
        d = a_decision(leader, cell)
        decision.act(leader["id"], d["id"], "open")
        offered = {a["name"] for a in decision.actions(leader["id"], decision.get(d["id"]))}
        self.assertIn("put_to_cell", offered)

    def test_a_member_is_not_offered_a_leaders_transitions(self):
        leader, cell, crew = a_cell(people=5)
        d = a_decision(leader, cell)
        decision.act(leader["id"], d["id"], "open")
        offered = {a["name"] for a in decision.actions(crew[0]["id"], decision.get(d["id"]))}
        self.assertNotIn("resolve", offered)
        self.assertNotIn("reject", offered)
        self.assertIn("put_to_cell", offered)


class Guards(unittest.TestCase):

    def test_a_member_asking_anyway_is_refused(self):
        leader, cell, crew = a_cell(people=5)
        d = a_decision(leader, cell)
        decision.act(leader["id"], d["id"], "open")
        options = decision_model.options_of(d["id"])
        with self.assertRaises(NotAllowed):
            decision.act(crew[0]["id"], d["id"], "resolve", option_id=options[0]["id"])

    def test_overruling_the_cell_without_a_reason_is_refused(self):
        leader, cell, crew = a_cell(people=5)
        d = a_decision(leader, cell)
        decision.act(leader["id"], d["id"], "open")
        decision.act(leader["id"], d["id"], "put_to_cell")
        options = decision_model.options_of(d["id"])
        for who in [leader] + crew[:3]:
            decision.vote(who["id"], d["id"], options[0]["id"])

        with self.assertRaises(DomainError):
            decision.act(leader["id"], d["id"], "resolve", option_id=options[1]["id"], note="")
        # ...and is allowed with one.
        decision.act(leader["id"], d["id"], "resolve", option_id=options[1]["id"],
                     note="I am taking the risk.")
        self.assertEqual(decision.get(d["id"])["decided_how"], "override")

    def test_an_option_from_another_decision_is_refused(self):
        leader, cell, _ = a_cell()
        first = a_decision(leader, cell)
        second = a_decision(leader, cell)
        decision.act(leader["id"], first["id"], "open")
        stranger = decision_model.options_of(second["id"])[0]
        with self.assertRaises(DomainError):
            decision.act(leader["id"], first["id"], "resolve", option_id=stranger["id"])


class Atomicity(unittest.TestCase):

    def test_a_transition_cannot_be_taken_twice(self):
        leader, cell, _ = a_cell()
        d = a_decision(leader, cell)
        decision.act(leader["id"], d["id"], "open")
        with self.assertRaises(Conflict):
            decision.act(leader["id"], d["id"], "open")

    def test_two_leaders_resolving_at_once_produce_one_outcome(self):
        leader, cell, _ = a_cell()
        d = a_decision(leader, cell)
        decision.act(leader["id"], d["id"], "open")
        options = decision_model.options_of(d["id"])

        results, gate = [], threading.Barrier(2)

        def resolve(option_id):
            gate.wait()
            try:
                decision.act(leader["id"], d["id"], "resolve",
                             option_id=option_id, note="mine")
                results.append("accepted")
            except Conflict:
                results.append("refused")
            except DomainError:
                results.append("refused")

        threads = [threading.Thread(target=resolve, args=(o["id"],)) for o in options]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(sorted(results), ["accepted", "refused"])
        self.assertEqual(decision.get(d["id"])["state"], "executing")
        # One decision, one option's worth of work.
        self.assertEqual(len(decision.tasks_of(d["id"])), 1)


class ExecutionIsDrivenByWork(unittest.TestCase):

    def test_accepting_generates_work_and_moves_the_decision(self):
        from cellos.domains.task import service as task

        leader, cell, _ = a_cell()
        d = a_decision(leader, cell)
        decision.act(leader["id"], d["id"], "open")
        options = decision_model.options_of(d["id"])
        decision.act(leader["id"], d["id"], "resolve", option_id=options[0]["id"])

        self.assertEqual(decision.get(d["id"])["state"], "executing")
        work = task.in_cells([cell["id"]])
        self.assertEqual([t["title"] for t in work], ["do A"])

        task.report_progress(leader["id"], work[0]["id"], 100)
        self.assertEqual(decision.get(d["id"])["state"], "completed")

        # Reopening the work reopens the decision. State follows the work.
        task.report_progress(leader["id"], work[0]["id"], 20)
        self.assertEqual(decision.get(d["id"])["state"], "executing")

    def test_an_unknown_step_is_refused(self):
        leader, cell, _ = a_cell()
        d = a_decision(leader, cell)
        with self.assertRaises(DomainError):
            decision.act(leader["id"], d["id"], "teleport")
