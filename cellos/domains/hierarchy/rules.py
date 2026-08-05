"""
Hierarchy: business rules. Pure functions.

There is no depth rule here. Nesting is not limited, because a cell inside a
cell is not a different kind of thing that needs guarding against -- it is a
cell. The only structural constraint is the loop check, and that needs the
graph, so it lives in the service.
"""


def rollup(own, below):
    """
    Combine a cell's own work with the work beneath it, weighted by how much
    each holds -- so a child cell with two tasks cannot outweigh one with two
    hundred. `own` and each of `below` are (count, total, done) triples.

    Pure arithmetic, kept here so the progress domain can be tested without a
    database.
    """
    count, total, done = own
    for c, t, d in below:
        count += c
        total += t
        done += d
    return {
        "percent": int(round(total / count)) if count else 0,
        "task_count": count,
        "done": done,
        "remaining": count - done,
    }
