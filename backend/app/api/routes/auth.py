from fastapi import APIRouter, HTTPException, Response, status

from app.api.auth_common import UNAUTHORIZED, clear_session_cookie, set_session_cookie
from app.api.deps import CurrentUser, DbSession
from app.models import Account
from app.schemas.auth import AccountRead, LoginRequest, MeResponse, PasswordChange, UserRead
from app.services import auth as auth_service
from app.services.errors import InvalidCredentials, SamePassword

router = APIRouter(tags=["auth"])


def _me(session, user) -> MeResponse:
    account = session.get(Account, user.account_id)
    return MeResponse(
        user=UserRead.model_validate(user, from_attributes=True),
        account=AccountRead.model_validate(
            {**account.model_dump(), "is_expired": account.is_expired()}
        ),
        device_ids=auth_service.accessible_device_ids(session, user),
    )


# There is no public signup. Accounts are issued by a platform admin (api/routes/admin.py),
# who hands the owner their username and password. `services/auth.py::signup` still exists —
# it is what the admin route calls — so removing the route here removed nothing else.


@router.post("/auth/login", response_model=MeResponse)
def login(body: LoginRequest, response: Response, session: DbSession) -> MeResponse:
    """Sign in with a username **or** an email."""
    try:
        user = auth_service.authenticate(
            session, identifier=body.identifier, password=body.password
        )
    except InvalidCredentials:
        raise UNAUTHORIZED from None

    set_session_cookie(response, user)
    return _me(session, user)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    clear_session_cookie(response)


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUser, session: DbSession) -> MeResponse:
    return _me(session, user)


@router.post("/auth/password", response_model=MeResponse)
def change_password(
    body: PasswordChange, user: CurrentUser, response: Response, session: DbSession
) -> MeResponse:
    """Replace your own password — required first when someone else chose it. Ends every other
    session, and hands this one a fresh cookie so it carries on. A wrong current password is
    400, not 401: it must not look like being signed out."""
    try:
        user = auth_service.change_own_password(
            session, user=user, current=body.current_password, new=body.new_password
        )
    except InvalidCredentials:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your current password isn't right") from None
    except SamePassword:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Choose a password different from the current one"
        ) from None
    set_session_cookie(response, user)
    return _me(session, user)
