"""Shared FastAPI dependencies.

Phase 3 adds CurrentUser, RequireOwner and DeviceForUser here — those three are the
whole authorization model.
"""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from app.infra.db import session_scope


def get_db() -> Generator[Session, None, None]:
    yield from session_scope()


DbSession = Annotated[Session, Depends(get_db)]
