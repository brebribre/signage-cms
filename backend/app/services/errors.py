"""Domain errors.

Raised by services, translated to HTTP by routes. Nothing here knows about FastAPI.
"""


class DomainError(Exception):
    """Base class for everything a service raises deliberately."""


class UsernameTaken(DomainError):
    pass


class EmailTaken(DomainError):
    pass


class InvalidCredentials(DomainError):
    """Deliberately covers three cases at once.

    Unknown identifier, wrong password, and deactivated user all raise this and produce a
    byte-identical 401. Three distinct messages would turn the login endpoint into an
    account-existence oracle, and `is_active` in particular would leak that a subuser had
    been suspended.
    """
