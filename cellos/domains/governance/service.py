"""
Governance: the same rules, asked about a real cell.

A thin layer over `rules`, because everything interesting about governance is
a pure function of scale and belongs somewhere testable.
"""

from ..hierarchy import service as hierarchy
from . import rules


def scale_of(cell_id):
    return hierarchy.scale(cell_id)


def capabilities(cell_id, scale=None):
    return rules.capabilities(scale_of(cell_id) if scale is None else scale)


def has(cell_id, capability, scale=None):
    return rules.has(scale_of(cell_id) if scale is None else scale, capability)


def model(cell_id, scale=None):
    return rules.model(scale_of(cell_id) if scale is None else scale)


def votes(cell_id, scale=None):
    return rules.votes(scale_of(cell_id) if scale is None else scale)
