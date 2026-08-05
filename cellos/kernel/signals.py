"""
Diagnostic signals.

One neutral value type, so a domain can say "this is costing the cell
something, and here is why" without knowing that a health layer exists. The
kernel stays ignorant of what any of it means.

A signal is never stored. It is produced from facts on read, like progress.
"""

from collections import namedtuple

# points  how much this drags on the cell, on the same 0-100 scale as potential
# reason  what to tell a person, in their words, not the system's
# where   the cell it belongs to, so a parent can say which child is stuck
# about   the id of the thing, so the interface can offer to open it
Friction = namedtuple("Friction", "points reason where about")


def friction(points, reason, where=None, about=None):
    return Friction(points=points, reason=reason, where=where, about=about)
