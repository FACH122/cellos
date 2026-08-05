"""Errors a domain raises when its rules say no."""


class DomainError(Exception):
    """The request was understood and refused. Maps to 400."""

    status = 400


class NotAllowed(DomainError):
    """The actor lacks the responsibility this action requires. Maps to 403."""

    status = 403


class NotFound(DomainError):
    status = 404


class Conflict(DomainError):
    """
    The world moved while the caller was deciding. Two people resolved the
    same decision; one of them lost. Maps to 409.
    """

    status = 409
