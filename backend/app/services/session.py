"""Signed session cookies.

The token carries the **user id and the user's session version**, nothing else. Role, account
and active status are read from the database on every request, so revoking a subuser or
narrowing their access takes effect immediately rather than whenever their 30-day cookie
happens to expire. The version does the same for passwords: changing one bumps
`User.session_version`, and every cookie carrying the old number stops working.

A cookie from before versions existed carries only the id; it reads as version 1, which is
what every user started at, so nobody was signed out by the change.
"""

import uuid

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import get_settings

# A salt distinct from any other signer we might add later: the same SECRET_KEY signing two
# kinds of token must not let one be presented as the other.
_SALT = "signage-cms.session"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().secret_key, salt=_SALT)


def create_session_token(user_id: uuid.UUID, version: int = 1) -> str:
    return _serializer().dumps(f"{user_id}:{version}")


def read_session_token(token: str) -> tuple[uuid.UUID, int] | None:
    """(user id, session version), or None for anything we would not act on: tampered, stale,
    malformed."""
    try:
        raw = _serializer().loads(token, max_age=get_settings().session_max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(raw, str):
        return None
    user_part, _, version_part = raw.partition(":")
    try:
        return uuid.UUID(user_part), int(version_part) if version_part else 1
    except (ValueError, TypeError):
        return None
