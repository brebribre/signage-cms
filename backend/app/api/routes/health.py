import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.api.deps import DbSession
from app.config import get_settings
from app.infra import mqtt
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health(session: DbSession) -> HealthResponse:
    """200 only if Postgres actually answers.

    A health check that reports the process is alive tells you nothing you didn't
    already know from the request reaching it — the interesting failure is the app
    running fine and a dependency being unreachable. The database is that dependency
    for the 503; MQTT deliberately is not — see HealthResponse.mqtt's docstring for why
    a broken broker is reported, not failed on.
    """
    try:
        session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — any driver failure is unhealthy
        logger.warning("health check failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from exc

    if not get_settings().mqtt_enabled:
        mqtt_status = "disabled"
    elif mqtt.check_connection():
        mqtt_status = "ok"
    else:
        mqtt_status = "unreachable"

    return HealthResponse(status="ok", database="ok", mqtt=mqtt_status)
