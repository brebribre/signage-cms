import logging
from collections.abc import Generator
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlmodel import Session, create_engine

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# pool_pre_ping: Railway's Postgres drops idle connections, and without this the
# first request after an idle period fails instead of transparently reconnecting.
engine = create_engine(settings.database_url, echo=False, pool_pre_ping=True)

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


def _alembic_config() -> Config:
    """Alembic config with absolute paths, so it works whatever the working directory is.

    The database URL is deliberately *not* set here — migrations/env.py reads it from
    app.config instead. alembic.ini goes through configparser, where a password
    containing '%' would blow up on interpolation.
    """
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    return config


def run_migrations() -> None:
    """Bring the database up to the latest revision.

    Called from the FastAPI lifespan, so a deploy applies its own migrations and there
    is no separate release step to forget.
    """
    command.upgrade(_alembic_config(), "head")
    logger.info("database migrations are up to date")


def session_scope() -> Generator[Session, None, None]:
    """Yield a session. Wrapped as a FastAPI dependency in app/api/deps.py."""
    with Session(engine) as session:
        yield session
