"""Password hashing. argon2id, via argon2-cffi's sensible defaults."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_hasher = PasswordHasher()

# A real hash of a throwaway password, used to burn the same CPU time when no user matched.
# Returning early on an unknown identifier makes login measurably faster for identifiers
# that do not exist, which is an account-existence oracle no matter how careful the
# response body is.
_DUMMY_HASH = _hasher.hash("timing-equalisation-only")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """True when the hash was made with weaker parameters than we now use.

    Checked on every successful login, so raising the cost factor upgrades users as they
    return rather than never.
    """
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def waste_time_like_a_verify() -> None:
    """Spend a verify's worth of CPU so an unknown identifier costs what a known one does."""
    verify_password(_DUMMY_HASH, "not-the-password")
