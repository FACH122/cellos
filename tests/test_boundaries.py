"""
Architecture, asserted.

Phase 2's central rule -- no domain manipulates another domain's internal
state -- is the kind of thing that holds for a week and then quietly stops
being true. These tests read the source and fail if it does.
"""

import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMAINS = os.path.join(ROOT, "cellos", "domains")
KERNEL = os.path.join(ROOT, "cellos", "kernel")

WRITE = re.compile(r"\b(?:INSERT\s+(?:OR\s+\w+\s+)?INTO|UPDATE|DELETE\s+FROM)\s+(\w+)",
                   re.IGNORECASE)
DECLARES = re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)", re.IGNORECASE)


def python_files(root):
    for base, _dirs, names in os.walk(root):
        if "__pycache__" in base:
            continue
        for name in names:
            if name.endswith(".py"):
                yield os.path.join(base, name)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def domain_of(path):
    rel = os.path.relpath(path, DOMAINS)
    return rel.split(os.sep)[0]


def ownership():
    """table -> the domain whose schema declares it."""
    owners = {}
    for path in python_files(DOMAINS):
        for table in DECLARES.findall(read(path)):
            owners[table.lower()] = domain_of(path)
    # The kernel owns the two tables that belong to no domain.
    for path in python_files(KERNEL):
        for table in DECLARES.findall(read(path)):
            owners[table.lower()] = "kernel"
    return owners


class Tables(unittest.TestCase):

    def setUp(self):
        self.owners = ownership()

    def test_every_domain_table_has_exactly_one_owner(self):
        self.assertIn("decisions", self.owners)
        self.assertEqual(self.owners["decisions"], "decision")
        self.assertEqual(self.owners["tasks"], "task")
        self.assertEqual(self.owners["memberships"], "member")
        self.assertEqual(self.owners["cells"], "cell")
        self.assertEqual(self.owners["evidence"], "evidence")
        self.assertEqual(self.owners["relationships"], "kernel")
        self.assertEqual(self.owners["events"], "kernel")

    def test_no_domain_writes_another_domains_table(self):
        trespass = []
        for path in python_files(DOMAINS):
            here = domain_of(path)
            body = read(path)
            for table in set(WRITE.findall(body)):
                owner = self.owners.get(table.lower())
                if owner is None:
                    trespass.append("%s writes unknown table %s" % (path, table))
                elif owner not in (here, "kernel"):
                    trespass.append(
                        "%s (%s domain) writes %s, owned by %s"
                        % (os.path.relpath(path, ROOT), here, table, owner)
                    )
        self.assertEqual(trespass, [], "\n".join(trespass))

    def test_the_kernel_writes_only_its_own_tables(self):
        for path in python_files(KERNEL):
            for table in set(WRITE.findall(read(path))):
                self.assertIn(
                    self.owners.get(table.lower()), ("kernel", None),
                    "%s writes %s" % (os.path.relpath(path, ROOT), table),
                )

    def test_only_the_workflow_engine_writes_a_state_column(self):
        """No service may set `state` directly; transitions own that column."""
        offenders = []
        for path in python_files(DOMAINS):
            for line in read(path).splitlines():
                if re.search(r"SET\s+state\s*=", line, re.IGNORECASE):
                    if not path.endswith(os.path.join("decision", "events.py")):
                        offenders.append("%s: %s" % (os.path.relpath(path, ROOT), line.strip()))
        self.assertEqual(offenders, [], "\n".join(offenders))


class Layering(unittest.TestCase):

    def test_no_domain_imports_the_app_at_module_level(self):
        """
        Endpoints compose their answer with the app's view layer, but only
        inside a handler. A module-level import would invert the dependency.
        """
        offenders = []
        for path in python_files(DOMAINS):
            for line in read(path).splitlines():
                stripped = line.strip()
                if not stripped.startswith(("from ", "import ")):
                    continue
                if "app" in stripped and line[:1] not in (" ", "\t"):
                    offenders.append("%s: %s" % (os.path.relpath(path, ROOT), stripped))
        self.assertEqual(offenders, [], "\n".join(offenders))

    def test_nothing_depends_on_health(self):
        """
        Health is the final interpretation layer. Everything feeds it and it
        feeds nothing, which is what keeps it a diagnostic: the moment a
        domain acted on a health number, that number would stop describing
        the organisation and start steering it.
        """
        offenders = []
        for path in python_files(DOMAINS):
            # The package index imports every domain by definition -- that is
            # registration, not dependency.
            if domain_of(path) == "health" or path.endswith(
                    os.path.join("domains", "__init__.py")):
                continue
            for line in read(path).splitlines():
                if line.strip().startswith(("from ", "import ")) and "health" in line:
                    offenders.append("%s: %s" % (os.path.relpath(path, ROOT), line.strip()))
        self.assertEqual(offenders, [], "\n".join(offenders))

    def test_health_never_writes_anything(self):
        """It owns no table and appends no event. It only ever reads."""
        for path in python_files(os.path.join(DOMAINS, "health")):
            body = read(path)
            self.assertNotIn("db.owns(", body)
            self.assertNotIn("events.append(", body)
            for word in ("INSERT", "UPDATE", "DELETE"):
                self.assertNotIn(word, body, os.path.relpath(path, ROOT))

    def test_the_kernel_knows_nothing_about_domains(self):
        for path in python_files(KERNEL):
            body = read(path)
            for word in ("domains", "decision", "cell_service", "membership"):
                self.assertNotIn(
                    "from ..%s" % word, body,
                    "%s reaches into %s" % (os.path.relpath(path, ROOT), word),
                )

    def test_rules_modules_stay_pure(self):
        """
        Business rules must be callable without a database. If a rules module
        imports storage, it cannot be tested as arithmetic any more.
        """
        for path in python_files(DOMAINS):
            if not path.endswith("rules.py"):
                continue
            body = read(path)
            for forbidden in ("import db", "import events", "from . import model",
                              "import relationships"):
                self.assertNotIn(
                    forbidden, body,
                    "%s should be pure but imports %s"
                    % (os.path.relpath(path, ROOT), forbidden),
                )


class Documentation(unittest.TestCase):

    def test_every_module_says_what_it_is_for(self):
        undocumented = []
        for root in (DOMAINS, KERNEL, os.path.join(ROOT, "cellos", "app")):
            for path in python_files(root):
                body = read(path).lstrip()
                if not body:
                    continue
                if not body.startswith(('"""', "'''")):
                    undocumented.append(os.path.relpath(path, ROOT))
        self.assertEqual(undocumented, [], "\n".join(undocumented))
