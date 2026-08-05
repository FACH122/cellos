#!/usr/bin/env python3
"""
End-to-end checks against a running server.

Drives one cell from nothing through the entire lifecycle, then grows it past
each threshold and asserts the capabilities appear on their own. Start the
server first, then: python3 smoke.py

These are the same assertions Phase 1 made. The one change is how a decision
is moved: there is no longer an endpoint per lifecycle step. The server offers
the transitions that are available and the client fires one by name, which is
what the workflow engine made possible -- so the test drives the decision the
way the interface does, and asserts on what is offered as well as what works.
"""

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8420"
failures = []


def call(method, path, body=None, token=None):
    data = json.dumps(body or {}).encode() if body is not None or method != "GET" else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def check(label, condition, detail=""):
    print("  %s %s%s" % ("ok  " if condition else "FAIL", label,
                         "" if condition else "  <- " + str(detail)))
    if not condition:
        failures.append(label)


def sign_in(name, email):
    status, r = call("POST", "/api/session", {"name": name, "email": email})
    assert status == 200, r
    return r["token"], r["user"]


def find(view, decision_id):
    for key in ("open_decisions", "settled_decisions"):
        for d in view.get(key, []):
            if d["id"] == decision_id:
                return d
    return None


def steps(view, decision_id):
    d = find(view, decision_id)
    return [a["name"] for a in (d["actions"] if d else [])]


def fire(decision_id, step, body=None, token=None):
    return call("POST", "/api/decisions/%s/steps/%s" % (decision_id, step), body or {}, token)


print("identity")
tok_a, alice = sign_in("Alice Test", "alice@test.org")
tok_b, bob = sign_in("Bob Test", "bob@test.org")
tok_c, carol = sign_in("Carol Outsider", "carol@test.org")
status, _ = call("GET", "/api/home")
check("unauthenticated request refused", status == 403)

print("\na cell of one")
status, v = call("POST", "/api/cells", {"goal": "Finish the thesis"}, tok_a)
check("cell created", status == 200, v)
cell_id = v["cell"]["id"]
check("creator leads it", v["you"]["is_leader"] is True)
check("no voting at scale 1", "voting" not in v["capabilities"], v["capabilities"])
check("no children at scale 1", "children" not in v["capabilities"])
check("no dashboard at scale 1", "dashboard" not in v["capabilities"])
check("governance is informal", v["governance"] == "informal", v["governance"])
check("nothing in the payload but the basics",
      "analytics" not in v and "children" not in v and "yours" not in v)

print("\na decision, alone")
status, v = call("POST", "/api/cells/%s/decisions" % cell_id,
                 {"question": "Which corpus?", "options": ["Hansard", "Europarl"],
                  "work": {"0": ["Download it", "Clean it"]}}, tok_a)
check("decision proposed", status == 200, v)
d = v["open_decisions"][0]
did = d["id"]
check("state is draft", d["state"] == "draft", d["state"])
check("the workflow offers opening it", "open" in steps(v, did), steps(v, did))
check("it does not offer a vote in a cell of one", "put_to_cell" not in steps(v, did))

status, v = fire(did, "open", {}, tok_a)
check("opened", find(v, did)["state"] == "open")
check("alone, you decide rather than hand it on",
      "resolve" in steps(v, did) and "ask_leader" not in steps(v, did), steps(v, did))

opts = find(v, did)["options"]
status, v = fire(did, "resolve", {"option_id": opts[0]["id"], "note": "More coverage."}, tok_a)
check("resolved", status == 200, v)
done = find(v, did)
check("recorded as a leader's call, not a vote", done["decided_how"] == "leader",
      done["decided_how"])
check("work generated automatically", len(v["tasks"]) == 2, v["tasks"])
check("solo cell auto-owns its work", all(t["owner_id"] == alice["id"] for t in v["tasks"]))
check("the decision moved itself to executing", done["state"] == "executing", done["state"])
check("the work links back to the decision",
      all(t["title"] in ("Download it", "Clean it") for t in v["tasks"]))

print("\nprogress flows up from the work, not down from a manager")
t0 = v["tasks"][0]["id"]
status, v = call("PATCH", "/api/tasks/%s" % t0, {"progress": 50}, tok_a)
check("cell progress derived", v["progress"]["percent"] == 25, v["progress"])
status, v = call("PATCH", "/api/tasks/%s" % t0, {"progress": 100}, tok_a)
check("completing a task moves the cell", v["progress"]["percent"] == 50, v["progress"])
check("no way to set cell progress directly",
      call("PATCH", "/api/cells/%s" % cell_id, {"progress": 99}, tok_a)[0] == 400)
remaining = [t for t in v["tasks"] if t["progress"] < 100]
check("finished work sorts out of the way", len(remaining) == 1, v["tasks"])
status, v = call("PATCH", "/api/tasks/%s" % remaining[0]["id"], {"progress": 100}, tok_a)
check("finishing all the work completes the decision",
      find(v, did)["state"] == "completed", find(v, did)["state"])

print("\nresponsibility")
status, _ = call("GET", "/api/cells/%s" % cell_id, None, tok_c)
check("an outsider cannot see the cell", status == 403)
status, r = call("POST", "/api/cells/%s/members" % cell_id,
                 {"name": "Bob Test", "email": "bob@test.org"}, tok_c)
check("an outsider cannot admit people", status == 403, r)
status, v = call("POST", "/api/cells/%s/members" % cell_id,
                 {"name": "Bob Test", "email": "bob@test.org"}, tok_a)
check("a member can be admitted", status == 200, v)
check("bob is a member, not a leader",
      [m for m in v["members"] if m["id"] == bob["id"]][0]["role"] == "member")

status, r = call("POST", "/api/cells/%s/decisions" % cell_id,
                 {"question": "Do we submit in spring or autumn?",
                  "options": ["Spring", "Autumn"],
                  "work": {"1": ["Book the reviewers", "Draft the timeline"]}}, tok_b)
check("a member may propose", status == 200)
d2 = r["open_decisions"][0]["id"]
call("POST", "/api/decisions/%s/steps/open" % d2, {}, tok_b)
status, v = call("GET", "/api/cells/%s" % cell_id, None, tok_b)
check("a member is not offered resolving", "resolve" not in steps(v, d2), steps(v, d2))
status, r = fire(d2, "resolve", {"option_id": find(v, d2)["options"][0]["id"]}, tok_b)
check("and is refused if they ask anyway", status == 403, r)

print("\ngrowth")
for i in range(3):
    call("POST", "/api/cells/%s/members" % cell_id,
         {"name": "Extra %d" % i, "email": "extra%d@test.org" % i}, tok_a)
status, v = call("GET", "/api/cells/%s" % cell_id, None, tok_a)
check("at five people, voting appears by itself",
      v["scale"] == 5 and "voting" in v["capabilities"], (v["scale"], v["capabilities"]))
check("governance became a vote", v["governance"] == "vote_decides", v["governance"])
check("children still absent at five", "children" not in v["capabilities"])
check("the same decision is now offered to the cell", "put_to_cell" in steps(v, d2), steps(v, d2))

status, r = call("POST", "/api/cells", {"goal": "A sub-team", "parent_id": cell_id}, tok_a)
check("child cells refused below the threshold", status == 400, r)

for i in range(15):
    call("POST", "/api/cells/%s/members" % cell_id,
         {"name": "Person %d" % i, "email": "grow%d@test.org" % i}, tok_a)
status, v = call("GET", "/api/cells/%s" % cell_id, None, tok_a)
check("at twenty, children and leader confirmation appear",
      {"children", "leader_confirms"} <= set(v["capabilities"]), v["capabilities"])
check("governance became leader-confirmed",
      v["governance"] == "leader_confirms_vote", v["governance"])
status, v2 = call("POST", "/api/cells", {"goal": "A sub-team", "parent_id": cell_id}, tok_a)
check("child cell now allowed", status == 200, v2)
child_id = v2["cell"]["id"]
check("the child is its own small cell again", "voting" not in v2["capabilities"])

print("\nthe vote, and overruling it")
status, v = call("GET", "/api/cells/%s" % cell_id, None, tok_a)
status, v = fire(d2, "put_to_cell", {}, tok_a)
opts = find(v, d2)["options"]
call("POST", "/api/decisions/%s/votes" % d2, {"option_id": opts[0]["id"]}, tok_a)
status, v = call("POST", "/api/decisions/%s/votes" % d2, {"option_id": opts[0]["id"]}, tok_b)
d = find(v, d2)
check("votes counted", d["turnout"] == 2, d["turnout"])
check("your own vote comes back to you", d["your_vote"] == opts[0]["id"])
status, r = call("POST", "/api/decisions/%s/votes" % d2, {"option_id": opts[0]["id"]}, tok_c)
check("an outsider cannot vote", status == 403)

check("past twenty the count is not offered as final",
      "accept_by_vote" not in steps(v, d2) and "send_to_leader" in steps(v, d2), steps(v, d2))
status, v = fire(d2, "send_to_leader", {}, tok_a)
check("it goes to whoever is accountable",
      find(v, d2)["state"] == "leader_resolution", find(v, d2)["state"])

status, r = fire(d2, "resolve", {"option_id": opts[1]["id"]}, tok_a)
check("overruling the vote without a reason is refused", status == 400, r)
status, v = fire(d2, "resolve",
                 {"option_id": opts[1]["id"], "note": "The vote is optimistic about timing."},
                 tok_a)
check("overruling with a reason is allowed", status == 200, v)
settled = find(v, d2)
check("recorded permanently as an override", settled["decided_how"] == "override")
check("the reason is kept", "optimistic" in settled["resolution_note"])

print("\nthe workflow is the only door")
status, r = fire(d2, "open", {}, tok_a)
check("a settled decision cannot be reopened", status == 409, r)
status, r = fire(d2, "not_a_step", {}, tok_a)
check("an invented step is refused", status == 400, r)
status, r = call("PATCH", "/api/cells/%s" % cell_id, {"state": "accepted"}, tok_a)
check("no endpoint accepts a state", status == 400, r)

print("\nevidence and knowledge")
status, v = call("POST", "/api/evidence",
                 {"subject_kind": "decision", "subject_id": d2, "kind": "link",
                  "label": "Timing analysis", "ref": "https://example.org/t"}, tok_a)
check("evidence attached", status == 200, v)
check("the cell now reports evidence in use", v.get("evidence_in_use") is True)
status, v = fire(d2, "record",
                 {"outcome": "Took eleven weeks.", "lesson": "Timing estimates were weak."},
                 tok_a)
check("knowledge recorded", status == 200, v)
check("it appears in the cell's memory",
      any(k["id"] == d2 for k in v.get("knowledge", [])), v.get("knowledge"))
rec = [k for k in v["knowledge"] if k["id"] == d2][0]
check("the reasoning survived with it", rec["lesson"].startswith("Timing"))

print("\nsending a decision back keeps the reason")
status, r = call("POST", "/api/cells/%s/decisions" % cell_id,
                 {"question": "Rewrite or patch?", "options": ["Rewrite", "Patch"]}, tok_a)
d3 = r["open_decisions"][0]["id"]
fire(d3, "open", {}, tok_a)
fire(d3, "put_to_cell", {}, tok_a)
status, v = fire(d3, "return", {"note": "Needs the cost figures."}, tok_a)
check("returned to discussion", find(v, d3)["state"] == "open", find(v, d3)["state"])
check("and the reason is shown, not only logged",
      find(v, d3)["revision_note"] == "Needs the cost figures.", find(v, d3)["revision_note"])

print("\nhierarchy and sight")
status, v = call("GET", "/api/cells/%s" % child_id, None, tok_a)
check("a parent leader can see into a child", status == 200)
status, v = call("GET", "/api/cells/%s" % cell_id, None, tok_b)
check("a member sees their own cell", status == 200)
status, v = call("GET", "/api/home", None, tok_b)
check("the child does not appear as a home cell for a parent member",
      all(c["id"] != child_id for c in v["cells"]), v["cells"])
status, v = call("GET", "/api/cells/%s/history" % cell_id, None, tok_a)
check("the full history is readable", len(v["events"]) > 20, len(v["events"]))
check("history names what happened",
      any(e["type"] == "DecisionAccepted" for e in v["events"]))
check("and names an override as an override",
      any(e["type"] == "LeaderOverride" for e in v["events"]))

print("\nresponsibility, not permissions")
status, v = call("GET", "/api/cells/%s/dashboard" % cell_id, None, tok_a)
check("a leader gets the cells beneath them", v["shape"] == "leader", v)
status, v = call("GET", "/api/cells/%s/dashboard" % cell_id, None, tok_b)
check("a member gets their own responsibility", v["shape"] == "member", v)
check("what they hold", "yours" in v["yours"], v["yours"].keys())
check("who is waiting on them", "waiting_on_you" in v["yours"])
check("what they are waiting on", "you_are_waiting_on" in v["yours"])
check("what nobody has taken", "blocked" in v["yours"])
check("what is moving", "moving" in v["yours"])

status, v = call("GET", "/api/cells/%s" % cell_id, None, tok_a)
roles = v["responsibility"]["roles"]
check("a cell says who is accountable for it",
      any(h["id"] == alice["id"] for h in roles["leader"]), roles)
check("and who took part", len(roles["participant"]) == v["scale"], roles)
t = [x for x in v["tasks"] if x["state"] != "expanded"]
if t:
    check("every piece of work says who is expected to do it",
          "responsibility" in t[0], t[0].keys())

print()
if failures:
    print("%d failed: %s" % (len(failures), ", ".join(failures)))
    sys.exit(1)
print("all checks passed")
