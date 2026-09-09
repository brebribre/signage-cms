from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # An absolute env_file path, so `.env` is found whatever directory the process
    # was started from — uvicorn from backend/, a check script from the repo root,
    # or Alembic from anywhere.
    model_config = SettingsConfigDict(env_file=BACKEND_ROOT / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg://signage:signage@localhost:5434/signage"

    # --- Sessions (Phase 3) ---
    secret_key: str = "dev-secret-change-me"
    session_cookie_name: str = "scms_session"
    session_max_age_seconds: int = 60 * 60 * 24 * 30  # 30 days
    # Must be True in production (HTTPS), and whenever cookie_samesite is "none".
    cookie_secure: bool = False
    # "lax" while frontend and API share a site. On different domains it must be
    # "none", which browsers honour only together with Secure=true — get one of the
    # two wrong and the cookie is dropped silently, with no console error.
    cookie_samesite: str = "lax"

    # --- Cloudflare R2 (Phase 5) ---
    r2_endpoint_url: str = ""
    r2_bucket: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""

    media_max_bytes: int = 500 * 1024 * 1024
    presign_put_ttl_seconds: int = 3600
    presign_get_ttl_seconds: int = 3600
    # Longer than the CMS's: a screen may be pulling a large file over bad wifi.
    device_presign_ttl_seconds: int = 6 * 3600

    # --- Player self-update (Phase 12c) ---
    # The version currently published for screens, e.g. "1.1.0". Empty disables updates
    # entirely, which is the safe default: a misconfigured value pushes an APK to every
    # screen you own at once.
    player_latest_version: str = ""
    # R2 object key for that APK, e.g. "apks/fortu-player-1.1.0.apk". Upload it with
    # scripts/publish_player_apk.py, which sets both of these for you.
    player_apk_key: str = ""

    # --- Devices (Phase 8) ---
    pairing_code_ttl_seconds: int = 900
    device_poll_seconds: int = 30

    # --- MQTT push prototype (see app/infra/mqtt.py) ---
    # Off by default — a device still gets everything from its next poll regardless, since
    # this is a latency optimization, never the source of truth. Local dev turns it on
    # against docker-compose's mosquitto service (anonymous, no credentials needed); the
    # deployed broker (mosquitto/, its own Railway service) requires mqtt_username/password.
    mqtt_enabled: bool = False
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: str = ""
    mqtt_password: str = ""

    log_level: str = "INFO"

    frontend_origin: str = "http://localhost:5173"
    # Comma-separated extra origins allowed by CORS, e.g. the deployed frontend.
    extra_cors_origins: str = ""

    @field_validator("database_url")
    @classmethod
    def _use_psycopg3_driver(cls, value: str) -> str:
        """Railway injects DATABASE_URL as `postgresql://…`.

        SQLAlchemy reads that as psycopg2, which isn't installed. Rewriting the scheme
        here means the platform-provided variable works unmodified.
        """
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        return value

    @property
    def cors_origins(self) -> list[str]:
        origins = [self.frontend_origin]
        origins += [o.strip() for o in self.extra_cors_origins.split(",") if o.strip()]
        # dict.fromkeys de-duplicates while preserving order.
        return list(dict.fromkeys(origins))


@lru_cache
def get_settings() -> Settings:
    return Settings()
