from fastapi import APIRouter, Response, status

from app.api.auth_common import UNAUTHORIZED, clear_session_cookie, set_session_cookie
from app.api.deps import CurrentUser, DbSession
from app.models import Account
from app.schemas.auth import AccountRead, LoginRequest, MeResponse, UserRead
from app.services import auth as auth_service
from app.services.errors import InvalidCredentials

router = APIRouter(tags=["auth"])


def _me(session, user) -> MeResponse:
    account = session.get(Account, user.account_id)
    return MeResponse(
        user=UserRead.model_validate(user, from_attributes=True),
        account=AccountRead.model_validate(account, from_attributes=True),
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

    set_session_cookie(response, user.id)
    return _me(session, user)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    clear_session_cookie(response)


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUser, session: DbSession) -> MeResponse:
    return _me(session, user)
