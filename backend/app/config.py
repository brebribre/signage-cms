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

    # How much the bucket may hold before it is time to upgrade — shown on the monitoring
    # app's Infrastructure page. R2 itself has no ceiling; it bills past its 10 GB free
    # allowance. So this is our own line, not Cloudflare's: raise it on the plan you move to.
    r2_storage_limit_gb: float = 10.0

    # The biggest single file an upload may be, by kind. Pictures: a full-size phone photo is
    # 5–15 MB, so 25 MB covers anything real while refusing the 200 MB TIFF that would strain the
    # converter and every cheap TV box showing it. Videos: 500 MB is ~10 minutes of Full HD or 3–4
    # of 4K, far past a signage loop, and the server keeps two more copies of each. (Other CMSs:
    # OptiSigns 1 GB, NoviSign 100 MB; Yodeck and ScreenCloud 5 GB on far bigger transcoders.)
    # The CMS reads these from GET /limits, so changing one here changes both sides.
    media_max_image_bytes: int = 25 * 1024 * 1024
    media_max_video_bytes: int = 500 * 1024 * 1024
    presign_put_ttl_seconds: int = 3600
    presign_get_ttl_seconds: int = 3600
    # Longer than the CMS's: a screen may be pulling a large file over bad wifi.
    device_presign_ttl_seconds: int = 6 * 3600

    # --- Devices (Phase 8) ---
    pairing_code_ttl_seconds: int = 900
    device_poll_seconds: int = 30
    # Local development only: a code "Add screen" always accepts, creating a mock screen with no
    # device behind it. See services/devices.py::claim — ignored whenever cookie_secure is on.
    mock_pairing_code: str = ""

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
    # The deployed broker (mosquitto/, on Railway) terminates TLS with a self-signed cert —
    # see infra/mqtt.py's module docstring for why it's self-signed rather than CA-issued.
    # False for local dev against docker-compose's plaintext mosquitto.
    mqtt_tls: bool = False
    # The dynsec bootstrap admin — see infra/mqtt_admin.py. Distinct from mqtt_username
    # (the `cms` publisher identity, which can only publish, never administer the broker).
    # Empty locally: docker-compose's dev broker has no dynsec plugin loaded at all.
    mqtt_admin_username: str = ""
    mqtt_admin_password: str = ""

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
