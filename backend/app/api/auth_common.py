"""What every sign-in route shares: the session cookie, and the one 401 a failed login returns.

Split out so the monitoring app's sign-in (routes/admin.py, `/admin/auth/*`) can use exactly
the same cookie and exactly the same refusal as the customer sign-in (routes/auth.py) without
importing the customer routes — the two must stay byte-identical on failure, or a refused
admin login would tell a customer that admin logins exist.
"""

from fastapi import HTTPException, Response, status

from app.config import get_settings
from app.services.session import create_session_token

# One message for every way a login can fail. See services/errors.InvalidCredentials.
UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
)


def set_session_cookie(response: Response, user_id) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=create_session_token(user_id),
        max_age=settings.session_max_age_seconds,
        httponly=True,          # JS must never be able to read it
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    # Same flags as when set: a cookie deleted with different attributes is not deleted.
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
