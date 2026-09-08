"""Signed session cookies.

The token carries the **user id and nothing else**. Role, account and active status are
read from the database on every request, so revoking a subuser or narrowing their access
takes effect immediately rather than whenever their 30-day cookie happens to expire.
"""

import uuid

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import get_settings

# A salt distinct from any other signer we might add later: the same SECRET_KEY signing two
# kinds of token must not let one be presented as the other.
_SALT = "signage-cms.session"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().secret_key, salt=_SALT)


def create_session_token(user_id: uuid.UUID) -> str:
    return _serializer().dumps(str(user_id))


def read_session_token(token: str) -> uuid.UUID | None:
    """The user id, or None for anything we would not act on: tampered, stale, malformed."""
    try:
        raw = _serializer().loads(token, max_age=get_settings().session_max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None
    try:
        return uuid.UUID(raw)
    except (ValueError, TypeError):
        return None
