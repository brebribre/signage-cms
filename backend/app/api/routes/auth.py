from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import CurrentUser, DbSession
from app.config import get_settings
from app.models import Account
from app.schemas.auth import (
    AccountRead,
    LoginRequest,
    MeResponse,
    SignupRequest,
    UserRead,
)
from app.services import auth as auth_service
from app.services.errors import EmailTaken, InvalidCredentials, UsernameTaken
from app.services.session import create_session_token

router = APIRouter(tags=["auth"])

# One message for every way a login can fail. See services/errors.InvalidCredentials.
UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
)


def _set_session_cookie(response: Response, user_id) -> None:
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


def _clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    # Same flags as when set: a cookie deleted with different attributes is not deleted.
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )


def _me(session, user) -> MeResponse:
    account = session.get(Account, user.account_id)
    return MeResponse(
        user=UserRead.model_validate(user, from_attributes=True),
        account=AccountRead.model_validate(account, from_attributes=True),
        device_ids=auth_service.accessible_device_ids(session, user),
    )


@router.post("/auth/signup", response_model=MeResponse, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, response: Response, session: DbSession) -> MeResponse:
    """Create an account and sign in as its owner."""
    try:
        user = auth_service.signup(
            session,
            username=body.username,
            password=body.password,
            display_name=body.display_name,
            email=body.email,
            account_name=body.account_name,
        )
    except UsernameTaken:
        raise HTTPException(status.HTTP_409_CONFLICT, "That username is taken") from None
    except EmailTaken:
        raise HTTPException(status.HTTP_409_CONFLICT, "That email is already registered") from None

    _set_session_cookie(response, user.id)
    return _me(session, user)


@router.post("/auth/login", response_model=MeResponse)
def login(body: LoginRequest, response: Response, session: DbSession) -> MeResponse:
    """Sign in with a username **or** an email."""
    try:
        user = auth_service.authenticate(
            session, identifier=body.identifier, password=body.password
        )
    except InvalidCredentials:
        raise UNAUTHORIZED from None

    _set_session_cookie(response, user.id)
    return _me(session, user)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    _clear_session_cookie(response)


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUser, session: DbSession) -> MeResponse:
    return _me(session, user)
