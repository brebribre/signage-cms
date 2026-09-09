from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    database: str
    # "ok", "unreachable", or "disabled" — never affects the response's status code. Unlike
    # the database, a broken broker does not make the CMS unhealthy: push is a latency
    # optimization devices fall back from automatically, never something else depends on.
    mqtt: str
